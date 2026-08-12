"""Recognizer protocol and registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from piilint.findings import EntityType, Severity


@dataclass(frozen=True, slots=True)
class Match:
    entity: EntityType
    value: str
    start: int
    end: int
    confidence: float
    severity: Severity | None = None


class Recognizer(Protocol):
    entity: EntityType
    enabled_by_default: bool

    def scan(self, text: str, *, context_key: str | None = None) -> list[Match]:
        """Return matches found in text. Never log raw values."""
        ...


class RecognizerRegistry:
    def __init__(self) -> None:
        self._recognizers: dict[EntityType, Recognizer] = {}
        self._enabled: dict[EntityType, bool] = {}

    def register(self, recognizer: Recognizer, *, enabled: bool | None = None) -> None:
        self._recognizers[recognizer.entity] = recognizer
        self._enabled[recognizer.entity] = (
            recognizer.enabled_by_default if enabled is None else enabled
        )

    def enable(self, entity: EntityType, enabled: bool = True) -> None:
        if entity in self._recognizers:
            self._enabled[entity] = enabled

    def enabled_recognizers(self) -> list[Recognizer]:
        return [r for e, r in self._recognizers.items() if self._enabled.get(e, False)]

    def get(self, entity: EntityType) -> Recognizer | None:
        return self._recognizers.get(entity)


def build_default_registry(
    *,
    default_phone_region: str = "US",
    phone_regions: list[str] | None = None,
    enable_ip: bool = False,
    enable_ner: bool = False,
    enable_nino_uk: bool = False,
    enable_bsn_nl: bool = False,
) -> RecognizerRegistry:
    from piilint.recognizers.bsn_nl import BsnNlRecognizer
    from piilint.recognizers.credit_card import CreditCardRecognizer
    from piilint.recognizers.dob import DobRecognizer
    from piilint.recognizers.email import EmailRecognizer
    from piilint.recognizers.iban import IbanRecognizer
    from piilint.recognizers.ip import IpAddressRecognizer
    from piilint.recognizers.ner import AddressRecognizer, PersonRecognizer
    from piilint.recognizers.nino_uk import NinoUkRecognizer
    from piilint.recognizers.phone import PhoneRecognizer
    from piilint.recognizers.sin_ca import SinCaRecognizer
    from piilint.recognizers.ssn import SsnUsRecognizer

    registry = RecognizerRegistry()
    registry.register(EmailRecognizer())
    registry.register(
        PhoneRecognizer(
            default_region=default_phone_region,
            extra_regions=phone_regions,
        )
    )
    registry.register(SsnUsRecognizer())
    registry.register(SinCaRecognizer())
    registry.register(NinoUkRecognizer(), enabled=enable_nino_uk)
    registry.register(BsnNlRecognizer(), enabled=enable_bsn_nl)
    registry.register(CreditCardRecognizer())
    registry.register(IbanRecognizer())
    registry.register(DobRecognizer())
    registry.register(IpAddressRecognizer(), enabled=enable_ip)
    # Always register (lazy imports inside scan); enabled only when NER is requested.
    registry.register(PersonRecognizer(), enabled=enable_ner)
    registry.register(AddressRecognizer(), enabled=enable_ner)
    return registry
