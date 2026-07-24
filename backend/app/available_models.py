"""Central catalog of chat LLM models available to users."""

from dataclasses import dataclass

DEFAULT_LLM_MODEL = "openai/gpt-oss-120b"


@dataclass(frozen=True, slots=True)
class AvailableModel:
    id: str
    name: str
    description: str
    icon: str
    recommended: bool = False


AVAILABLE_MODELS: tuple[AvailableModel, ...] = (
    AvailableModel(
        id="openai/gpt-oss-120b",
        name="GPT-OSS 120B",
        description="Best for reasoning, document analysis, RAG, planning, coding and complex tasks.",
        icon="⭐",
        recommended=True,
    ),
    AvailableModel(
        id="llama-3.3-70b-versatile",
        name="Llama 3.3 70B",
        description="Balanced model for conversations, creativity and everyday assistance.",
        icon="🦙",
    ),
    AvailableModel(
        id="qwen/qwen3.6-27b",
        name="Qwen 3.6 27B",
        description="Optimized for coding, debugging and technical problem solving.",
        icon="💻",
    ),
)

MODEL_IDS: frozenset[str] = frozenset(m.id for m in AVAILABLE_MODELS)


def is_valid_model_id(model_id: str | None) -> bool:
    return bool(model_id and model_id in MODEL_IDS)


def get_model_or_default(model_id: str | None) -> str:
    if is_valid_model_id(model_id):
        return model_id  # type: ignore[return-value]
    return DEFAULT_LLM_MODEL
