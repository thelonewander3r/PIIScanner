"""Finding model, masking, and fingerprint helpers.

This module must not import recognizer logic — it is part of the generic
scan chassis shared with future sibling products.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EntityType(str, Enum):
    CREDIT_CARD = "CREDIT_CARD"
    SSN_US = "SSN_US"
    SIN_CA = "SIN_CA"
    NINO_UK = "NINO_UK"
    BSN_NL = "BSN_NL"
    IBAN = "IBAN"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    DOB = "DOB"
    IP_ADDRESS = "IP_ADDRESS"
    PERSON = "PERSON"
    ADDRESS = "ADDRESS"


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


DEFAULT_SEVERITY: dict[EntityType, Severity] = {
    EntityType.CREDIT_CARD: Severity.HIGH,
    EntityType.SSN_US: Severity.HIGH,
    EntityType.SIN_CA: Severity.HIGH,
    EntityType.NINO_UK: Severity.HIGH,
    EntityType.BSN_NL: Severity.HIGH,
    EntityType.IBAN: Severity.HIGH,
    EntityType.EMAIL: Severity.MEDIUM,
    EntityType.PHONE: Severity.MEDIUM,
    EntityType.DOB: Severity.MEDIUM,
    EntityType.IP_ADDRESS: Severity.LOW,
    EntityType.PERSON: Severity.MEDIUM,
    EntityType.ADDRESS: Severity.MEDIUM,
}


def normalize_value(value: str, entity: EntityType) -> str:
    """Normalize a raw match for hashing / dedup (never for display)."""
    cleaned = value.strip()
    if entity in {
        EntityType.CREDIT_CARD,
        EntityType.SSN_US,
        EntityType.SIN_CA,
        EntityType.NINO_UK,
        EntityType.BSN_NL,
        EntityType.PHONE,
        EntityType.IBAN,
    }:
        cleaned = re.sub(r"[\s\-().]", "", cleaned)
    if entity == EntityType.EMAIL:
        cleaned = cleaned.lower()
    if entity in {EntityType.IBAN, EntityType.NINO_UK}:
        cleaned = cleaned.upper()
    if entity == EntityType.IP_ADDRESS:
        cleaned = cleaned.lower()
    return cleaned


def value_hash(value: str, entity: EntityType) -> str:
    normalized = normalize_value(value, entity)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def mask_value(value: str, entity: EntityType) -> str:
    """Return a redacted sample suitable for logs and reporters."""
    raw = value.strip()
    if entity == EntityType.EMAIL:
        return _mask_email(raw)
    if entity == EntityType.PHONE:
        digits = re.sub(r"\D", "", raw)
        if len(digits) >= 2:
            return f"{'*' * max(len(digits) - 2, 0)}{digits[-2:]}"
        return "***"
    if entity == EntityType.CREDIT_CARD:
        digits = re.sub(r"\D", "", raw)
        last4 = digits[-4:] if len(digits) >= 4 else "****"
        return f"**** **** **** {last4}"
    if entity == EntityType.SSN_US:
        return "***-**-****"
    if entity == EntityType.SIN_CA:
        return "***-***-***"
    if entity == EntityType.NINO_UK:
        return "** ****** *"
    if entity == EntityType.BSN_NL:
        return "*********"
    if entity == EntityType.IBAN:
        compact = re.sub(r"\s+", "", raw).upper()
        if len(compact) <= 4:
            return "****"
        return f"{compact[:2]}{'*' * (len(compact) - 4)}{compact[-2:]}"
    if entity == EntityType.PERSON:
        parts = raw.split()
        if not parts:
            return "*"
        return " ".join(f"{p[0]}***" if p else "*" for p in parts)
    if entity == EntityType.IP_ADDRESS:
        return _mask_ip(raw)
    if entity == EntityType.DOB:
        return "**/**/****"
    if entity == EntityType.ADDRESS:
        return "[address redacted]"
    return "***"


def _mask_email(value: str) -> str:
    if "@" not in value:
        return "***@***.***"
    local, _, domain = value.partition("@")
    local_mask = (local[:1] + "***") if local else "***"
    parts = domain.split(".")
    if len(parts) >= 2:
        name = parts[0]
        name_mask = (name[:1] + "***") if name else "***"
        return f"{local_mask}@{name_mask}.{'.'.join(parts[1:])}"
    return f"{local_mask}@{domain[:1]}***" if domain else f"{local_mask}@***"


def _mask_ip(value: str) -> str:
    if ":" in value:
        parts = value.split(":")
        if len(parts) >= 2:
            return f"{parts[0]}:****:****:{parts[-1]}"
        return "****"
    parts = value.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.***.***.{parts[3]}"
    return "***.***.***.***"


@dataclass(frozen=True, slots=True)
class Location:
    path: str
    line: int | None = None
    column: str | None = None
    cell: int | None = None
    cell_part: str | None = None  # source | output
    row: int | None = None
    offset: int | None = None

    def label(self) -> str:
        bits: list[str] = [self.path]
        if self.cell is not None:
            part = self.cell_part or "source"
            bits.append(f"cell {self.cell} ({part})")
        if self.column is not None:
            bits.append(f'column "{self.column}"')
        if self.line is not None:
            bits.append(f"line {self.line}")
        if self.row is not None:
            bits.append(f"row {self.row}")
        return " · ".join(bits)


@dataclass(slots=True)
class Finding:
    entity: EntityType
    severity: Severity
    confidence: float
    location: Location
    masked_sample: str
    value_sha256: str
    fingerprint: str
    matched_count: int = 1
    total_non_null: int | None = None
    sampled: bool = False
    extras: dict[str, Any] = field(default_factory=dict)
    # Internal: used by policy (allowlist / test-data). Never printed by reporters.
    normalized_value: str = field(default="", repr=False)

    @staticmethod
    def create(
        *,
        entity: EntityType,
        raw_value: str,
        location: Location,
        confidence: float,
        severity: Severity | None = None,
        occurrence_index: int = 0,
        matched_count: int = 1,
        total_non_null: int | None = None,
        sampled: bool = False,
        extras: dict[str, Any] | None = None,
    ) -> Finding:
        vhash = value_hash(raw_value, entity)
        fp = fingerprint_for(
            path=location.path,
            entity=entity,
            value_sha256=vhash,
            occurrence_index=occurrence_index,
        )
        return Finding(
            entity=entity,
            severity=severity or DEFAULT_SEVERITY[entity],
            confidence=confidence,
            location=location,
            masked_sample=mask_value(raw_value, entity),
            value_sha256=vhash,
            fingerprint=fp,
            matched_count=matched_count,
            total_non_null=total_non_null,
            sampled=sampled,
            extras=extras or {},
            normalized_value=normalize_value(raw_value, entity),
        )


def fingerprint_for(
    *,
    path: str,
    entity: EntityType,
    value_sha256: str,
    occurrence_index: int,
) -> str:
    """Stable fingerprint excluding line numbers so edits don't resurrect findings."""
    material = f"{path}|{entity.value}|{value_sha256}|{occurrence_index}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
