#!/usr/bin/env python3
"""Manual performance smoke checks (not run in CI by default).

Targets from BUILD_PLAN Phase 2:
  - 100 MB CSV scanned in ≤ 60 s
  - 1 GB parquet streamed with < 500 MB peak memory

Usage:
  uv run python scripts/perf_smoke.py           # CSV 100MB only (default)
  uv run python scripts/perf_smoke.py --full    # also build/scan 1GB parquet
"""

from __future__ import annotations

import argparse
import csv
import os
import tempfile
import time
import tracemalloc
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from piilint.engine import scan_path


def _rss_mb() -> float:
    try:
        import psutil  # type: ignore[import-untyped]

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:
        _current, peak = tracemalloc.get_traced_memory()
        return peak / (1024 * 1024)


def build_csv(path: Path, target_mb: int = 100) -> None:
    """Write a synthetic CSV roughly target_mb in size."""
    rows = max(int((target_mb * 1024 * 1024) / 120), 1000)
    print(f"Writing ~{target_mb} MB CSV ({rows:,} rows) -> {path}")
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["id", "email", "note"])
        batch: list[list[object]] = []
        for i in range(rows):
            batch.append([i, f"user{i}@corpmail.test", f"row-{i}-padding-{'x' * 40}"])
            if len(batch) >= 20_000:
                writer.writerows(batch)
                batch.clear()
        if batch:
            writer.writerows(batch)
    print(f"CSV size: {path.stat().st_size / (1024 * 1024):.1f} MB")


def build_parquet(path: Path, target_mb: int = 1024) -> None:
    print(f"Writing ~{target_mb} MB parquet -> {path}")
    rows = max(int((target_mb * 1024 * 1024) / 80), 1000)
    chunk = 200_000
    writer: pq.ParquetWriter | None = None
    written = 0
    while written < rows:
        n = min(chunk, rows - written)
        table = pa.table(
            {
                "id": pa.array(range(written, written + n)),
                "email": pa.array([f"user{i}@corpmail.test" for i in range(written, written + n)]),
                "note": pa.array([f"pad-{i}-{'y' * 32}" for i in range(written, written + n)]),
            }
        )
        if writer is None:
            writer = pq.ParquetWriter(path, table.schema)
        writer.write_table(table)
        written += n
        print(f"  … {written:,}/{rows:,}")
    assert writer is not None
    writer.close()
    print(f"Parquet size: {path.stat().st_size / (1024 * 1024):.1f} MB")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Include 1GB parquet memory check")
    parser.add_argument("--csv-mb", type=int, default=100)
    parser.add_argument("--parquet-mb", type=int, default=1024)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="piilint-perf-") as tmp:
        tmp_path = Path(tmp)
        csv_path = tmp_path / "big.csv"
        build_csv(csv_path, target_mb=args.csv_mb)

        tracemalloc.start()
        t0 = time.perf_counter()
        result = scan_path(csv_path)
        elapsed = time.perf_counter() - t0
        mem = _rss_mb()
        print(
            f"CSV scan: {elapsed:.2f}s, findings={len(result.findings)}, "
            f"files={result.files_scanned}, mem≈{mem:.0f} MB"
        )
        if elapsed > 60:
            raise SystemExit(f"FAIL: CSV scan {elapsed:.1f}s > 60s")
        print("PASS: CSV ≤ 60s")

        if args.full:
            pq_path = tmp_path / "big.parquet"
            build_parquet(pq_path, target_mb=args.parquet_mb)
            tracemalloc.reset_peak()
            t0 = time.perf_counter()
            before = _rss_mb()
            result = scan_path(pq_path)
            elapsed = time.perf_counter() - t0
            peak = _rss_mb()
            print(
                f"Parquet scan: {elapsed:.2f}s, findings={len(result.findings)}, "
                f"mem before≈{before:.0f} MB peak≈{peak:.0f} MB"
            )
            if peak >= 500:
                raise SystemExit(f"FAIL: parquet peak memory {peak:.0f} MB ≥ 500 MB")
            print("PASS: parquet peak < 500 MB")


if __name__ == "__main__":
    main()
