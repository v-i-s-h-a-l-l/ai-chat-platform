from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class UploadPolicyDecision(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    RESTRICT = "restrict"


@dataclass(frozen=True)
class DocumentSample:
    title: str
    first_page_text: str
    page_count: int | None
    filename: str


@dataclass(frozen=True)
class PiiInventory:
    names: int = 0
    emails: int = 0
    phone_numbers: int = 0
    passport_numbers: int = 0
    aadhaar_numbers: int = 0
    pan_numbers: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "names": self.names,
            "emails": self.emails,
            "phone_numbers": self.phone_numbers,
            "passport_numbers": self.passport_numbers,
            "aadhaar_numbers": self.aadhaar_numbers,
            "pan_numbers": self.pan_numbers,
        }


@dataclass
class UploadValidationResult:
    decision: UploadPolicyDecision
    document_type: str | None = None
    confidence: float | None = None
    policy_applied: str = "fast_policy"
    existing_pii_violation: str | None = None
    fast_policy_reason: str | None = None
    gpt_invoked: bool = False
    inventory: PiiInventory = field(default_factory=PiiInventory)
