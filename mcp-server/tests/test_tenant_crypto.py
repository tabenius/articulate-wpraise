import os
import pytest
from cryptography.fernet import Fernet


@pytest.fixture
def crypto():
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    from articulate_mcp.tenants.crypto import TenantCrypto
    return TenantCrypto(os.environ["ENCRYPTION_KEY"])


def test_generate_secrets_returns_all_fields(crypto):
    secrets = crypto.generate_secrets()
    assert "db_password" in secrets
    assert "db_root_password" in secrets
    assert "wp_admin_password" in secrets
    assert len(secrets["db_password"]) >= 24
    assert len(secrets["db_root_password"]) >= 24
    assert len(secrets["wp_admin_password"]) >= 24


def test_generate_secrets_are_unique(crypto):
    s1 = crypto.generate_secrets()
    s2 = crypto.generate_secrets()
    assert s1["db_password"] != s2["db_password"]


def test_encrypt_decrypt_roundtrip(crypto):
    original = "my-secret-password"
    encrypted = crypto.encrypt(original)
    assert encrypted != original.encode()
    decrypted = crypto.decrypt(encrypted)
    assert decrypted == original


def test_encrypt_secrets_returns_bytes(crypto):
    secrets = crypto.generate_secrets()
    encrypted = crypto.encrypt_secrets(secrets)
    assert isinstance(encrypted["db_password"], bytes)
    assert isinstance(encrypted["db_root_password"], bytes)
    assert isinstance(encrypted["wp_admin_password"], bytes)


def test_decrypt_secrets_roundtrip(crypto):
    secrets = crypto.generate_secrets()
    encrypted = crypto.encrypt_secrets(secrets)
    decrypted = crypto.decrypt_secrets(encrypted)
    assert decrypted == secrets
