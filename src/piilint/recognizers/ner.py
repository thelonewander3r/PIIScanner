"""Optional Presidio/spaCy NER recognizers for PERSON and ADDRESS.

Heavy dependencies (presidio-analyzer, spaCy) are imported lazily so the base
install never loads them. The spaCy English model is fetched only via
``piilint setup-ner`` — never at scan time.
"""

from __future__ import annotations

from typing import Any

from piilint.findings import EntityType
from piilint.recognizers import Match

SPACY_MODEL = "en_core_web_sm"

# Presidio spaCy labels → piilint entities. LOCATION (GPE/LOC) maps to ADDRESS.
_PRESIDIO_TO_ENTITY: dict[str, EntityType] = {
    "PERSON": EntityType.PERSON,
    "LOCATION": EntityType.ADDRESS,  # spaCy GPE/LOC via Presidio
}

_INSTALL_HINT = 'pip install "piilint[ner]" && piilint setup-ner'
_SETUP_HINT = "run piilint setup-ner"


class NerDependencyError(RuntimeError):
    """Raised when ``piilint[ner]`` packages are not installed."""


class NerModelError(RuntimeError):
    """Raised when the spaCy model is missing (run setup-ner)."""


def ner_deps_available() -> bool:
    """Return True if presidio-analyzer and spaCy import successfully."""
    try:
        import presidio_analyzer  # noqa: F401
        import spacy  # noqa: F401
    except ImportError:
        return False
    return True


def spacy_model_available(model: str = SPACY_MODEL) -> bool:
    """Return True if the named spaCy model can be loaded locally (no download)."""
    try:
        import spacy
    except ImportError:
        return False
    try:
        spacy.load(model)
    except OSError:
        return False
    return True


def require_ner_ready(model: str = SPACY_MODEL) -> None:
    """Raise NerDependencyError / NerModelError with clear user-facing messages."""
    if not ner_deps_available():
        raise NerDependencyError(f"NER requires the optional extra. Install with: {_INSTALL_HINT}")
    if not spacy_model_available(model):
        raise NerModelError(f"spaCy model {model!r} is not installed; {_SETUP_HINT}")


def _model_wheel_url(model: str) -> str:
    """GitHub release wheel URL matching the installed spaCy minor version."""
    import spacy

    version = getattr(spacy, "__version__", "3.8.0")
    parts = str(version).split(".")
    major, minor = parts[0], parts[1]
    # spaCy models publish as major.minor.0 for each spaCy minor line.
    model_ver = f"{major}.{minor}.0"
    return (
        "https://github.com/explosion/spacy-models/releases/download/"
        f"{model}-{model_ver}/{model}-{model_ver}-py3-none-any.whl"
    )


def download_spacy_model(model: str = SPACY_MODEL) -> None:
    """Download a spaCy model (network). Intended only for ``setup-ner``.

    Prefers ``uv pip install`` (uv venvs often ship without ``pip``), then
    ``python -m pip``, then ``spacy.cli.download``.
    """
    try:
        import spacy  # noqa: F401
    except ImportError as exc:
        raise NerDependencyError(
            f"NER requires the optional extra. Install with: {_INSTALL_HINT}"
        ) from exc

    import os
    import shutil
    import subprocess
    import sys

    wheel_url = _model_wheel_url(model)
    errors: list[str] = []

    uv = shutil.which("uv")
    if uv:
        cmd = [uv, "pip", "install", wheel_url, "--python", sys.executable]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            return
        errors.append(f"uv pip: {(proc.stderr or proc.stdout or '').strip()}")

    pip_cmd = [sys.executable, "-m", "pip", "install", wheel_url]
    proc = subprocess.run(pip_cmd, capture_output=True, text=True, check=False)
    if proc.returncode == 0:
        return
    errors.append(f"pip: {(proc.stderr or proc.stdout or '').strip()}")

    # Last resort: spaCy's own downloader (needs pip in the env).
    try:
        from spacy.cli import (
            download as spacy_download,  # type: ignore[attr-defined, unused-ignore]
        )

        # Avoid interactive prompts; download() may still shell out to pip.
        os.environ.setdefault("SPACY_WARNING_IGNORE", "W008")
        spacy_download(model)
        return
    except Exception as exc:  # noqa: BLE001
        errors.append(f"spacy.cli.download: {exc}")

    raise RuntimeError(f"Could not install spaCy model {model!r}. Tried: " + " | ".join(errors))


class _SharedNerEngine:
    """Lazy Presidio AnalyzerEngine shared by PERSON/ADDRESS recognizers.

    Caches the last ``analyze`` result so scanning the same text for both
    entities does not run spaCy twice.
    """

    def __init__(self, model: str = SPACY_MODEL) -> None:
        self._model = model
        self._analyzer: Any | None = None
        self._cache_text: str | None = None
        self._cache_results: list[Any] = []

    def _ensure_analyzer(self) -> Any:
        if self._analyzer is not None:
            return self._analyzer
        require_ner_ready(self._model)
        from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        from presidio_analyzer.predefined_recognizers import SpacyRecognizer

        provider = NlpEngineProvider(
            nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": self._model}],
            }
        )
        nlp_engine = provider.create_engine()
        # Only spaCy NER — avoid Presidio regex recognizers (and tldextract).
        registry = RecognizerRegistry()
        registry.add_recognizer(SpacyRecognizer())
        self._analyzer = AnalyzerEngine(
            registry=registry,
            nlp_engine=nlp_engine,
            supported_languages=["en"],
        )
        return self._analyzer

    def analyze(self, text: str) -> list[Any]:
        if not text or not text.strip():
            return []
        if text == self._cache_text:
            return self._cache_results
        analyzer = self._ensure_analyzer()
        results = analyzer.analyze(
            text=text,
            language="en",
            entities=list(_PRESIDIO_TO_ENTITY.keys()),
        )
        self._cache_text = text
        self._cache_results = list(results)
        return self._cache_results


_ENGINE = _SharedNerEngine()


def _matches_for(text: str, entity: EntityType) -> list[Match]:
    out: list[Match] = []
    for result in _ENGINE.analyze(text):
        mapped = _PRESIDIO_TO_ENTITY.get(result.entity_type)
        if mapped != entity:
            continue
        start = int(result.start)
        end = int(result.end)
        value = text[start:end]
        if not value.strip():
            continue
        score = float(result.score) if result.score is not None else 0.7
        conf = max(0.0, min(1.0, score))
        out.append(
            Match(
                entity=entity,
                value=value,
                start=start,
                end=end,
                confidence=conf,
            )
        )
    return out


class PersonRecognizer:
    """Presidio/spaCy PERSON recognizer. Off by default; requires ``[ner]`` + model."""

    entity = EntityType.PERSON
    enabled_by_default = False

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        del context_key
        return _matches_for(text, EntityType.PERSON)


class AddressRecognizer:
    """Presidio LOCATION/ADDRESS → piilint ADDRESS. Off by default."""

    entity = EntityType.ADDRESS
    enabled_by_default = False

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        del context_key
        return _matches_for(text, EntityType.ADDRESS)
