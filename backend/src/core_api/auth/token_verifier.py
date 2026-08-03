"""JWT verification against Supabase Auth.

Per docs/ARCHITECTURE.md §8: internal services never talk to Supabase Auth
directly, they only verify the JWT it already issued. The gateway/service
fetches Supabase's JWKS, caches it, and validates signature + standard
claims (exp, aud) on every request.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from jose import jwt
from jose.exceptions import JOSEError


class TokenVerificationError(Exception):
    """Raised for any invalid, expired, or malformed bearer token."""


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    id: UUID
    email: str


class TokenVerifier(ABC):
    @abstractmethod
    async def verify(self, token: str) -> VerifiedIdentity: ...


class SupabaseJWTVerifier(TokenVerifier):
    """Production verifier: fetches and caches Supabase's JWKS.

    The JWKS is refreshed at most once per `jwks_cache_ttl_seconds` to avoid
    a network round-trip on every request while still picking up key
    rotation within a bounded window.
    """

    def __init__(
        self,
        jwks_url: str,
        *,
        audience: str = "authenticated",
        jwks_cache_ttl_seconds: int = 300,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._jwks_url = jwks_url
        self._audience = audience
        self._cache_ttl = jwks_cache_ttl_seconds
        self._http_client = http_client or httpx.AsyncClient(timeout=5.0)
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_fetched_at: float = 0.0

    async def _get_jwks(self) -> dict[str, Any]:
        now = time.monotonic()
        if self._jwks_cache is None or (now - self._jwks_fetched_at) > self._cache_ttl:
            response = await self._http_client.get(self._jwks_url)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_fetched_at = now
        return self._jwks_cache

    async def verify(self, token: str) -> VerifiedIdentity:
        jwks = await self._get_jwks()
        try:
            unverified_header = jwt.get_unverified_header(token)
            key = next(
                (k for k in jwks.get("keys", []) if k.get("kid") == unverified_header.get("kid")),
                None,
            )
            if key is None:
                raise TokenVerificationError("No matching JWKS key for token")

            claims = jwt.decode(token, key, audience=self._audience, algorithms=[key["alg"]])
        except JOSEError as exc:
            raise TokenVerificationError(str(exc)) from exc

        subject = claims.get("sub")
        email = claims.get("email")
        if not subject or not email:
            raise TokenVerificationError("Token missing required 'sub'/'email' claims")

        return VerifiedIdentity(id=UUID(subject), email=email)


class StaticTokenVerifier(TokenVerifier):
    """Test/dev double: maps fixed bearer tokens to identities without any
    network call or cryptographic verification. Never used in production.
    """

    def __init__(self, tokens: dict[str, VerifiedIdentity]) -> None:
        self._tokens = tokens

    async def verify(self, token: str) -> VerifiedIdentity:
        identity = self._tokens.get(token)
        if identity is None:
            raise TokenVerificationError("Unknown test token")
        return identity
