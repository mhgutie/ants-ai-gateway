from app.providers import get_provider_client
from app.providers.qwen import QwenClient
from app.model_router import provider_model_id


def test_provider_factory_returns_qwen_client():
    assert isinstance(get_provider_client("qwen"), QwenClient)


def test_qwen_client_uses_openai_compatible_base_url():
    client = QwenClient()

    assert client.name == "qwen"
    assert client.default_base_url.endswith("/compatible-mode/v1")


def test_qwen3_coder_alias_points_to_real_dashscope_model_id():
    assert provider_model_id("qwen3-coder") == "qwen3-coder-30b-a3b-instruct"
