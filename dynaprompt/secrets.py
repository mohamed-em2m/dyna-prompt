"""Secret injection at render time — never stored in files."""

from __future__ import annotations

import os


class MissingSecretError(Exception):
    """Raised when a prompt template requires a secret not found in the environment."""

    pass


class SecretStore:
    """
    Resolves secrets on demand during Jinja2 rendering.
    Maps attribute access → os.environ lookups.
    Extend this class to add Vault, AWS Secrets Manager, etc.
    """

    def __getattr__(self, name: str) -> str:
        value = os.environ.get(name)
        if value is None:
            raise MissingSecretError(
                f"Secret '{name}' was requested by a prompt template but is not "
                f"set in the environment. Set it with: export {name}=<value>"
            )
        return value

    def __getitem__(self, name: str) -> str:
        return self.__getattr__(name)

    def get(self, name: str, default: str = None) -> str:
        return os.environ.get(name, default)
