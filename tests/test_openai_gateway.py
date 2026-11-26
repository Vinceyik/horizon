import json

from src.ai.client import (OpenAIClient, _is_response_format_unsupported,
                           _unwrap_gateway_envelope)
from src.models import AIConfig


def make_config(**overrides):
    data = {
        "provider": "openai",
        "model": "deepseek-v4.1-flash",
        "api_key_env": "TEST_GATEWAY_KEY",
    }
    data.update(overrides)
    return AIConfig(**data)


def test_opencode_gateway_gets_a_session_header(monkeypatch):
    monkeypatch.setenv("TEST_GATEWAY_KEY", "sk-test")
    client = OpenAIClient(
        make_config(base_url="https://opencode.ai/inference/go/openai/v1")
    )
    headers = dict(client.client.default_headers)
    assert headers["x-opencode-session"].startswith("ses_")
    assert headers["User-Agent"] == "horizon-briefing/1.0"


def test_other_gateways_get_no_session_header(monkeypatch):
    monkeypatch.setenv("TEST_GATEWAY_KEY", "sk-test")
    client = OpenAIClient(make_config(base_url="https://api.example.com/v1"))
    assert "x-opencode-session" not in dict(client.client.default_headers)


def test_response_format_rejection_is_detected():
    assert _is_response_format_unsupported("response_format is not supported")
    assert _is_response_format_unsupported("Invalid parameter: json_object")
    assert not _is_response_format_unsupported("temperature is not supported")


def test_messages_envelope_is_unwrapped():
    raw = json.dumps({
        "messages": [
            {"role": "user", "content": "ignored"},
            {"role": "assistant", "content": "庫存降至 3,850 BCF。"},
        ]
    })
    assert _unwrap_gateway_envelope(raw) == "庫存降至 3,850 BCF。"


def test_plain_text_and_other_json_are_left_alone():
    assert _unwrap_gateway_envelope("庫存降至 3,850 BCF。") == "庫存降至 3,850 BCF。"
    payload = '{"score": 8, "reason": "ok"}'
    assert _unwrap_gateway_envelope(payload) == payload
    assert _unwrap_gateway_envelope("") == ""
