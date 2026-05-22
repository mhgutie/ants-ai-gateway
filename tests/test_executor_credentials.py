from app.executor_credentials import (
    credential_pool_status_from_payload,
    decrypt_credential_pool,
    encrypt_credential_pool,
    generate_executor_credentials_key,
    load_executor_credential_pool_status,
    safe_credential_pool_preview,
)


def _hermes_like_payload():
    return {
        "version": 1,
        "providers": {
            "openai-codex": {
                "tokens": {
                    "id_token": "id-secret",
                    "access_token": "access-secret",
                    "refresh_token": "refresh-secret",
                    "account_id": "account-1",
                },
                "last_refresh": "2026-05-18T17:06:43.313396Z",
                "auth_mode": "chatgpt",
            }
        },
        "active_provider": "openai-codex",
        "updated_at": "2026-05-21T02:34:24.664545+00:00",
        "credential_pool": {
            "openai-codex": [
                {
                    "id": "cred-1",
                    "label": "device_code",
                    "auth_type": "oauth",
                    "priority": 0,
                    "source": "device_code",
                    "access_token": "access-secret",
                    "refresh_token": "refresh-secret",
                    "last_status": "ok",
                    "base_url": "https://chatgpt.com/backend-api/codex",
                    "request_count": 0,
                }
            ]
        },
    }


def test_executor_credential_pool_encrypts_and_decrypts_hermes_like_payload():
    key = generate_executor_credentials_key()
    payload = _hermes_like_payload()

    encrypted = encrypt_credential_pool(payload, key)
    decrypted = decrypt_credential_pool(encrypted, key)

    assert encrypted != str(payload)
    assert decrypted == payload


def test_executor_credential_status_exposes_metadata_only():
    status = credential_pool_status_from_payload(_hermes_like_payload())

    assert status.configured is True
    assert status.decryptable is True
    assert status.active_provider == "openai-codex"
    assert status.credential_counts == {"openai-codex": 1}
    assert "secret" not in status.model_dump_json()


def test_safe_preview_redacts_token_fields():
    preview = safe_credential_pool_preview(_hermes_like_payload())
    serialized = str(preview)

    assert "access-secret" not in serialized
    assert "refresh-secret" not in serialized
    assert "[ENCRYPTED]" in serialized


def test_load_executor_credential_pool_status_from_env(monkeypatch):
    key = generate_executor_credentials_key()
    encrypted = encrypt_credential_pool(_hermes_like_payload(), key)
    monkeypatch.setenv("ANTS_EXECUTOR_CREDENTIALS_KEY", key)
    monkeypatch.setenv("ANTS_EXECUTOR_CREDENTIAL_POOL_ENC", encrypted)

    status = load_executor_credential_pool_status()

    assert status.configured is True
    assert status.decryptable is True
    assert status.providers == ["openai-codex"]
