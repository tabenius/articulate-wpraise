"""Secret generation and encryption for tenant provisioning."""

import secrets
import string
from cryptography.fernet import Fernet


class TenantCrypto:
    """Generates and encrypts tenant secrets."""

    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)

    def _generate_password(self, length: int = 32) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def generate_secrets(self) -> dict[str, str]:
        return {
            "db_password": self._generate_password(),
            "db_root_password": self._generate_password(),
            "wp_admin_password": self._generate_password(),
        }

    def encrypt(self, value: str) -> bytes:
        return self.cipher.encrypt(value.encode())

    def decrypt(self, value: bytes) -> str:
        return self.cipher.decrypt(value).decode()

    def encrypt_secrets(self, secrets_dict: dict[str, str]) -> dict[str, bytes]:
        return {k: self.encrypt(v) for k, v in secrets_dict.items()}

    def decrypt_secrets(self, encrypted: dict[str, bytes]) -> dict[str, str]:
        return {k: self.decrypt(v) for k, v in encrypted.items()}
