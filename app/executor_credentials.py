from __future__ import annotations

import json
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.schemas import ExecutorCredentialPoolStatus


TOKEN_KEYS = {"id_token", "access_token", "refresh_token"}


def generate_executor_credentials_key() -> str:
    return Fernet.generate_key().decode("ascii")


def encrypt_credential_pool(payload: dict[str, Any], key: str) -> str:
    serialized = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return Fernet(key.encode("ascii")).encrypt(serialized).decode("ascii")


def decrypt_credential_pool(encrypted_payload: str, key: str) -> dict[str, Any]:
    decrypted = Fernet(key.encode("ascii")).decrypt(encrypted_payload.encode("ascii"))
    return json.loads(decrypted.decode("utf-8"))


def _redact_tokens(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("[ENCRYPTED]" if key in TOKEN_KEYS else _redact_tokens(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_tokens(item) for item in value]
    return value


def credential_pool_status_from_payload(payload: dict[str, Any]) -> ExecutorCredentialPoolStatus:
    credential_pool = payload.get("credential_pool") or {}
    providers = sorted(str(provider) for provider in credential_pool)
    return ExecutorCredentialPoolStatus(
        configured=True,
        decryptable=True,
        version=payload.get("version"),
        active_provider=payload.get("active_provider"),
        providers=providers,
        credential_counts={
            str(provider): len(credentials) if isinstance(credentials, list) else 0
            for provider, credentials in credential_pool.items()
        },
        updated_at=payload.get("updated_at"),
    )


def safe_credential_pool_preview(payload: dict[str, Any]) -> dict[str, Any]:
    return _redact_tokens(payload)


def load_executor_credential_pool_status() -> ExecutorCredentialPoolStatus:
    key = os.getenv("ANTS_EXECUTOR_CREDENTIALS_KEY")
    encrypted_payload = os.getenv("ANTS_EXECUTOR_CREDENTIAL_POOL_ENC")
    if not key or not encrypted_payload:
        return ExecutorCredentialPoolStatus(configured=False, decryptable=False)
    try:
        payload = decrypt_credential_pool(encrypted_payload, key)
    except (InvalidToken, ValueError, TypeError) as exc:
        return ExecutorCredentialPoolStatus(
            configured=True,
            decryptable=False,
            error=exc.__class__.__name__,
        )
    return credential_pool_status_from_payload(payload)
