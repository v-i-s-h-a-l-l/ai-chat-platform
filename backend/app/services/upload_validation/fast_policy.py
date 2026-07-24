"""Fast upload policy rules — no external API calls."""

from __future__ import annotations

import re

from app.guardrails.pii import detect_sensitive_financial_data
from app.services.upload_validation.pii_inventory import build_pii_inventory
from app.services.upload_validation.types import (
    DocumentSample,
    PiiInventory,
    UploadPolicyDecision,
    UploadValidationResult,
)

_ACADEMIC_HINTS = re.compile(
    r"\b(abstract|arxiv|ieee|acm|doi|references|bibliography|proceedings|journal|"
    r"university|research|paper|authors?|correspondence)\b",
    re.IGNORECASE,
)
_BUSINESS_DOC_HINTS = re.compile(
    r"\b(invoice|receipt|business\s+card|resume|curriculum\s+vitae|\bcv\b|"
    r"bill\s+to|ship\s+to|tax\s+invoice|contact\s+card)\b",
    re.IGNORECASE,
)
_SENSITIVE_DOC_HINTS = re.compile(
    r"\b(passport|aadhaar|aadhar|\bpan\s+card\b|permanent\s+account\s+number|"
    r"medical\s+record|health\s+record|bank\s+statement|credit\s+card\s+statement|"
    r"driving\s+licen[cs]e|salary\s+slip)\b",
    re.IGNORECASE,
)


def evaluate_fast_policy(sample: DocumentSample) -> UploadValidationResult:
    """Apply fast rules. Returns decision and whether GPT classification is needed."""
    combined = f"{sample.filename}\n{sample.first_page_text}"
    inventory = build_pii_inventory(combined)

    filename_violation = detect_sensitive_financial_data(sample.filename)
    content_violation = detect_sensitive_financial_data(sample.first_page_text)
    existing_violation = filename_violation or content_violation

    if existing_violation:
        return UploadValidationResult(
            decision=UploadPolicyDecision.RESTRICT,
            policy_applied="fast_policy_pending_gpt",
            existing_pii_violation=existing_violation,
            fast_policy_reason="Financial PII detected — requires context classification",
            inventory=inventory,
            gpt_invoked=False,
        )

    if _has_high_sensitivity_signals(combined, inventory):
        return UploadValidationResult(
            decision=UploadPolicyDecision.WARN,
            document_type=_guess_sensitive_document_type(combined),
            confidence=0.9,
            policy_applied="fast_policy_sensitive_document",
            existing_pii_violation=existing_violation,
            fast_policy_reason="High-sensitivity document indicators detected",
            inventory=inventory,
        )

    if _is_common_metadata_only(inventory):
        return UploadValidationResult(
            decision=UploadPolicyDecision.ALLOW,
            document_type="General Document",
            confidence=0.95,
            policy_applied="fast_policy_no_pii",
            fast_policy_reason="No sensitive PII detected",
            inventory=inventory,
        )

    if _ACADEMIC_HINTS.search(combined) or _BUSINESS_DOC_HINTS.search(combined):
        return UploadValidationResult(
            decision=UploadPolicyDecision.ALLOW,
            document_type=_guess_benign_document_type(combined),
            confidence=0.85,
            policy_applied="fast_policy_benign_document",
            fast_policy_reason="Expected PII for document category",
            inventory=inventory,
        )

    if inventory.emails or inventory.names or inventory.phone_numbers:
        return UploadValidationResult(
            decision=UploadPolicyDecision.RESTRICT,
            policy_applied="fast_policy_pending_gpt",
            existing_pii_violation=None,
            fast_policy_reason="Ambiguous personal information — requires context classification",
            inventory=inventory,
        )

    return UploadValidationResult(
        decision=UploadPolicyDecision.ALLOW,
        document_type="General Document",
        confidence=0.9,
        policy_applied="fast_policy_default_allow",
        fast_policy_reason="No blocking signals",
        inventory=inventory,
    )


def needs_gpt_classification(result: UploadValidationResult) -> bool:
    return result.policy_applied == "fast_policy_pending_gpt"


def _has_high_sensitivity_signals(text: str, inventory: PiiInventory) -> bool:
    if _SENSITIVE_DOC_HINTS.search(text):
        return True
    if inventory.aadhaar_numbers or inventory.pan_numbers:
        return True
    if inventory.passport_numbers and re.search(r"\bpassport\b", text, re.IGNORECASE):
        return True
    return False


def _is_common_metadata_only(inventory: PiiInventory) -> bool:
    return (
        inventory.emails == 0
        and inventory.names == 0
        and inventory.phone_numbers == 0
        and inventory.passport_numbers == 0
        and inventory.aadhaar_numbers == 0
        and inventory.pan_numbers == 0
    )


def _guess_benign_document_type(text: str) -> str:
    if _ACADEMIC_HINTS.search(text):
        return "Research Paper"
    if re.search(r"\bresume\b|\bcv\b|curriculum\s+vitae", text, re.IGNORECASE):
        return "Resume / CV"
    if re.search(r"business\s+card|contact\s+card", text, re.IGNORECASE):
        return "Business Card"
    if re.search(r"\binvoice\b|receipt|tax\s+invoice", text, re.IGNORECASE):
        return "Invoice"
    return "Business Document"


def _guess_sensitive_document_type(text: str) -> str:
    lowered = text.lower()
    if "passport" in lowered:
        return "Passport"
    if "aadhaar" in lowered or "aadhar" in lowered:
        return "Aadhaar"
    if "pan card" in lowered or "permanent account number" in lowered:
        return "PAN Card"
    if "medical record" in lowered or "health record" in lowered:
        return "Medical Record"
    if "bank statement" in lowered:
        return "Bank Statement"
    if "credit card statement" in lowered:
        return "Credit Card Statement"
    if "driving licen" in lowered:
        return "Driving Licence"
    return "Sensitive Personal Document"
