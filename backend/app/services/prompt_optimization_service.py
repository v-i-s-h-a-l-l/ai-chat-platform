import logging

from app.schemas.prompt_optimization import PromptOptimizationResponse
from app.services.prompt_optimization_provider import PromptOptimizationProvider

logger = logging.getLogger(__name__)

# If the model returns a rewrite that is too long, fall back to the original.
_MAX_LENGTH_RATIO = 1.25


class PromptOptimizationService:
    """Orchestrates prompt safety review and proofreading during project creation."""

    def __init__(self, provider: PromptOptimizationProvider) -> None:
        self._provider = provider

    async def optimize_prompt(
        self,
        project_name: str,
        description: str,
        system_prompt: str,
    ) -> PromptOptimizationResponse:
        original = system_prompt.strip()
        if not original:
            raise ValueError("System prompt is required for optimization")

        logger.info(
            "Prompt optimization started (project=%r, prompt_len=%d)",
            project_name,
            len(original),
        )

        result = await self._provider.analyze_and_optimize(
            project_name=project_name.strip(),
            description=(description or "").strip(),
            system_prompt=original,
        )

        if not result.safe:
            logger.warning(
                "Prompt optimization blocked unsafe prompt (project=%r): %s",
                project_name,
                result.reason,
            )
            return PromptOptimizationResponse(
                safe=False,
                reason=result.reason,
                original_prompt=original,
                improved_prompt=None,
                changes=[],
            )

        improved = result.improved_prompt or original
        changes = list(result.changes)

        # Guard against over-expansion on longer prompts (short prompts may grow
        # more in relative terms when adding paragraph breaks).
        if len(original) >= 100 and len(improved) > len(original) * _MAX_LENGTH_RATIO:
            logger.info(
                "Improved prompt exceeded length ratio (orig=%d, improved=%d); using original",
                len(original),
                len(improved),
            )
            improved = original
            changes.append("Kept original wording (AI revision exceeded length guidelines)")

        if improved == original and not changes:
            changes = ["No changes needed"]

        logger.info(
            "Prompt optimization completed (project=%r, safe=True, changes=%d)",
            project_name,
            len(changes),
        )

        return PromptOptimizationResponse(
            safe=True,
            reason=None,
            original_prompt=original,
            improved_prompt=improved,
            changes=changes,
        )
