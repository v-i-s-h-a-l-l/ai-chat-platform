"""Orchestrates upload validation: PII inventory → fast policy → optional GPT decision."""

from __future__ import annotations

import logging

from app.config import settings
from app.guardrails.exceptions import GuardrailViolationError
from app.services.upload_validation.document_classifier import DocumentUploadClassifier
from app.services.upload_validation.exceptions import UploadConfirmationRequiredError
from app.services.upload_validation.fast_policy import evaluate_fast_policy, needs_gpt_classification
from app.services.upload_validation.text_sampler import sample_document
from app.services.upload_validation.types import UploadPolicyDecision, UploadValidationResult

logger = logging.getLogger(__name__)

_WARN_MESSAGE = (
    "This document appears to contain sensitive personal information. "
    "Do you still want to continue indexing this document?"
)

_RESTRICT_MESSAGE = (
    "Upload rejected: file appears to contain sensitive payment or authentication data "
    "(card numbers, CVV, MPIN, or OTP). Please remove it and try again."
)


class UploadDecisionService:
    def __init__(self, classifier: DocumentUploadClassifier | None = None) -> None:
        self._classifier = classifier or DocumentUploadClassifier()

    async def evaluate_and_enforce(
        self,
        filename: str,
        mime_type: str,
        data: bytes,
        *,
        confirmed: bool = False,
    ) -> UploadValidationResult:
        """Run validation pipeline and raise if upload must stop or confirm."""
        if not settings.guardrails_enabled:
            return UploadValidationResult(decision=UploadPolicyDecision.ALLOW)

        sample = sample_document(filename, mime_type, data)
        result = evaluate_fast_policy(sample)

        logger.info(
            "Upload validation [pii_inventory] filename=%s inventory=%s existing_pii=%s",
            filename,
            result.inventory.as_dict(),
            result.existing_pii_violation,
        )
        logger.info(
            "Upload validation [fast_policy] filename=%s decision=%s policy=%s reason=%s",
            filename,
            result.decision.value,
            result.policy_applied,
            result.fast_policy_reason,
        )

        if needs_gpt_classification(result) and settings.upload_validation_gpt_enabled:
            result = await self._apply_gpt_decision(sample, result)
            logger.info(
                "Upload validation [gpt_decision] filename=%s decision=%s type=%s confidence=%s policy=%s",
                filename,
                result.decision.value,
                result.document_type,
                result.confidence,
                result.policy_applied,
            )
        elif needs_gpt_classification(result):
            result.decision = UploadPolicyDecision.WARN
            result.policy_applied = "fast_policy_gpt_disabled_fallback_warn"

        self._enforce(result, confirmed=confirmed)
        return result

    async def _apply_gpt_decision(
        self,
        sample,
        result: UploadValidationResult,
    ) -> UploadValidationResult:
        try:
            decision, document_type, confidence, reason = await self._classifier.classify(
                sample,
                result.inventory,
                existing_pii_violation=result.existing_pii_violation,
            )
        except Exception as exc:
            logger.warning("Upload GPT classification failed, falling back to warn: %s", exc)
            result.decision = UploadPolicyDecision.WARN
            result.policy_applied = "gpt_fallback_warn"
            result.fast_policy_reason = str(exc)
            result.gpt_invoked = True
            return result

        result.decision = decision
        result.document_type = document_type
        result.confidence = confidence
        result.policy_applied = "gpt_context_classification"
        result.fast_policy_reason = reason
        result.gpt_invoked = True
        return result

    @staticmethod
    def _enforce(result: UploadValidationResult, *, confirmed: bool) -> None:
        if result.decision == UploadPolicyDecision.ALLOW:
            logger.info(
                "Upload validation [final] decision=allow type=%s policy=%s",
                result.document_type,
                result.policy_applied,
            )
            return

        if result.decision == UploadPolicyDecision.WARN:
            if confirmed:
                logger.info(
                    "Upload validation [final] decision=warn_confirmed type=%s policy=%s",
                    result.document_type,
                    result.policy_applied,
                )
                return
            logger.info(
                "Upload validation [final] decision=warn_pending_confirmation type=%s policy=%s",
                result.document_type,
                result.policy_applied,
            )
            raise UploadConfirmationRequiredError(
                _WARN_MESSAGE,
                document_type=result.document_type,
                confidence=result.confidence,
            )

        logger.warning(
            "Upload validation [final] decision=restrict type=%s policy=%s",
            result.document_type,
            result.policy_applied,
        )
        raise GuardrailViolationError(_RESTRICT_MESSAGE, code="pii_violation")
