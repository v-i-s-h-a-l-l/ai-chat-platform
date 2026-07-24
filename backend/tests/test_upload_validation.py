import pytest

from app.guardrails.exceptions import GuardrailViolationError
from app.services.upload_validation.exceptions import UploadConfirmationRequiredError
from app.services.upload_validation.fast_policy import evaluate_fast_policy, needs_gpt_classification
from app.services.upload_validation.pii_inventory import build_pii_inventory
from app.services.upload_validation.text_sampler import sample_document
from app.services.upload_validation.types import DocumentSample, UploadPolicyDecision
from app.services.upload_validation.upload_decision_service import UploadDecisionService


RESEARCH_PAPER = b"""# Attention Is All You Need

Abstract
The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.

Authors: Ashish Vaswani, Noam Shazeer, Niki Parmar
Correspondence: author@google.com, niki@google.com
References
[1] Previous work on neural machine translation.
"""

RESUME = b"""# Jane Doe

Email: jane.doe@example.com
Phone: +1 415 555 0100

Experience
Software Engineer at Example Corp
"""

PASSPORT_DOC = b"""Passport
Surname: DOE
Given Names: JANE
Passport No: A12345678
Nationality: Example Country
"""

INVOICE_WITH_CARD_LABEL = b"""Tax Invoice
Bill To: Example Corp
Card Number: 4111 1111 1111 1111
CVV: 123
"""


def test_fast_policy_allows_research_paper():
    sample = sample_document("attention_is_all_you_need.pdf", "text/markdown", RESEARCH_PAPER)
    result = evaluate_fast_policy(sample)
    assert result.decision == UploadPolicyDecision.ALLOW
    assert not needs_gpt_classification(result)
    assert result.inventory.emails >= 1


def test_fast_policy_allows_resume():
    sample = sample_document("resume.txt", "text/plain", RESUME)
    result = evaluate_fast_policy(sample)
    assert result.decision == UploadPolicyDecision.ALLOW
    assert result.document_type in {"Resume / CV", "Business Document"}


def test_fast_policy_warns_for_passport():
    sample = sample_document("passport_scan.txt", "text/plain", PASSPORT_DOC)
    result = evaluate_fast_policy(sample)
    assert result.decision == UploadPolicyDecision.WARN
    assert result.document_type == "Passport"
    assert not needs_gpt_classification(result)


def test_financial_pii_triggers_gpt_path():
    sample = sample_document("invoice.txt", "text/plain", INVOICE_WITH_CARD_LABEL)
    result = evaluate_fast_policy(sample)
    assert needs_gpt_classification(result)
    assert result.existing_pii_violation is not None


def test_pii_inventory_counts_emails():
    inventory = build_pii_inventory("Contact author@google.com and niki@google.com")
    assert inventory.emails == 2


@pytest.mark.asyncio
async def test_enforce_warn_requires_confirmation():
    service = UploadDecisionService()
    with pytest.raises(UploadConfirmationRequiredError):
        service._enforce(
            type("R", (), {
                "decision": UploadPolicyDecision.WARN,
                "document_type": "Passport",
                "confidence": 0.9,
                "policy_applied": "fast_policy_sensitive_document",
            })(),
            confirmed=False,
        )


@pytest.mark.asyncio
async def test_enforce_restrict_raises_guardrail():
    from app.services.upload_validation.types import UploadValidationResult

    service = UploadDecisionService()
    with pytest.raises(GuardrailViolationError):
        service._enforce(
            UploadValidationResult(decision=UploadPolicyDecision.RESTRICT),
            confirmed=False,
        )


@pytest.mark.asyncio
async def test_evaluate_plain_text_fast_path():
    service = UploadDecisionService(classifier=None)
    result = await service.evaluate_and_enforce(
        "notes.txt",
        "text/plain",
        b"Meeting notes for sprint planning.",
    )
    assert result.decision == UploadPolicyDecision.ALLOW


def test_sample_document_title_from_heading():
    sample = sample_document("paper.pdf", "text/markdown", RESEARCH_PAPER)
    assert "Attention Is All You Need" in sample.title
