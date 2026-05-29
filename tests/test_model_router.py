import pytest

from app.config import get_models_config
from app.model_router import get_routing_rules, implemented_providers, is_model_available, provider_for, route_for, select_model
from app.schemas import TaskType


def test_gpt_5_4_exists_in_model_catalog():
    assert "gpt-5.4" in get_models_config()["models"]


def test_gemini_3_5_flash_exists_in_model_catalog():
    assert "gemini-3.5-flash" in get_models_config()["models"]


def test_coding_debug_routes_to_qwen3_coder_and_validates_with_gpt_5_4():
    route = route_for(TaskType.coding_debug)
    assert route["primary"] == "qwen3-coder"
    assert route["fallback"] == "kimi-k2.6"
    assert route["validator"] == "gpt-5.4"
    assert provider_for(route["primary"]) == "qwen"


def test_long_document_routes_to_deepseek_v4_pro():
    route = route_for(TaskType.long_document)
    assert route["primary"] == "deepseek-v4-pro"
    assert route["fallback"] == "kimi-k2.6"
    assert provider_for(route["primary"]) == "deepseek"


def test_final_validation_routes_to_gpt_5_5_with_gpt_5_4_fallback():
    route = route_for(TaskType.final_validation)
    assert route["primary"] == "gpt-5.5"
    assert route["fallback"] == "gpt-5.4"
    assert route["validator"] is None
    assert provider_for(route["primary"]) == "openai"


def test_disabled_models_cannot_be_selected_unless_explicitly_allowed():
    assert is_model_available("gemini-3.1-pro") is False

    model, fallback = select_model("complex_reasoning", "auto")
    assert model == "deepseek-v4-pro"
    assert fallback == "deepseek-v4-pro"

    model, fallback = select_model("complex_reasoning", "auto", allow_disabled=True)
    assert model == "gemini-3.1-pro"
    assert fallback == "deepseek-v4-pro"


def test_disabled_model_without_enabled_fallback_raises():
    with pytest.raises(ValueError):
        select_model("text_to_speech", "auto")


def test_task_type_enum_covers_all_routing_rules():
    task_type_values = {task_type.value for task_type in TaskType}
    assert set(get_routing_rules()) <= task_type_values


def test_google_workspace_processing_routes_to_deepseek_v4_pro():
    route = route_for(TaskType.google_workspace_processing)
    assert route["primary"] == "deepseek-v4-pro"
    assert route["fallback"] == "kimi-k2.6"


def test_complex_reasoning_uses_enabled_fallback_when_primary_disabled():
    model, fallback = select_model(TaskType.complex_reasoning, "auto")
    assert model == "deepseek-v4-pro"
    assert fallback == "deepseek-v4-pro"


def test_direct_provider_models_are_executable_only_when_adapter_exists():
    assert is_model_available("qwen3-coder") is True
    assert is_model_available("gemini-3.5-flash") is False
    assert is_model_available("gpt-5.5") is False
    assert is_model_available("deepseek-v4-flash") is True


def test_implemented_providers_are_derived_from_models_yaml():
    assert implemented_providers() == {"deepseek", "kimi", "openrouter", "qwen"}
