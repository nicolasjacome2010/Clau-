"""Field-level encryption for sensitive columns.

docs/DATABASE.md §5 requires the raw text of a user's decision to be
encrypted at the application layer, not just covered by disk-level
encryption (docs/ARCHITECTURE.md §11). This module defines the port
(`FieldEncryptor`); `infrastructure` layers depend on it, never on a
concrete crypto library directly.

Production is meant to derive each user's key from an AWS KMS master key
(per docs/ARCHITECTURE.md §11: "la clave de cifrado por usuario se deriva
de una master key en AWS KMS, nunca almacenada en la propia base de
datos"). `FernetFieldEncryptor` below is the interim implementation: a
single application-wide key from Settings. Swapping in real per-user
KMS-derived keys later only requires a new `FieldEncryptor` implementation
— callers never change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from cryptography.fernet import Fernet, InvalidToken


class FieldDecryptionError(Exception):
    """Raised when ciphertext cannot be decrypted (wrong/rotated key, corruption)."""


class FieldEncryptor(ABC):
    @abstractmethod
    def encrypt(self, plaintext: str) -> bytes: ...

    @abstractmethod
    def decrypt(self, ciphertext: bytes) -> str: ...


class FernetFieldEncryptor(FieldEncryptor):
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._fernet.decrypt(ciphertext).decode()
        except InvalidToken as exc:
            raise FieldDecryptionError(
                "Could not decrypt field: invalid key or corrupt data"
            ) from exc
