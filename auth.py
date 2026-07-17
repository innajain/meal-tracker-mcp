import secrets
import time
from dataclasses import dataclass, field
from mcp.server.auth.provider import (
    OAuthAuthorizationServerProvider,
    OAuthClientInformationFull,
    OAuthToken,
    AuthorizationParams,
    AuthorizationCode,
    AccessToken,
    RefreshToken,
)


@dataclass
class _Client:
    info: OAuthClientInformationFull


@dataclass
class _AuthCode:
    code: str
    client_id: str
    redirect_uri: str
    code_challenge: str | None = None


@dataclass
class _Token:
    token: str
    client_id: str
    scopes: list[str] = field(default_factory=list)
    expires_at: float = field(default_factory=lambda: time.time() + 86400)


class SimpleOAuthProvider(OAuthAuthorizationServerProvider):
    """Minimal OAuth provider that auto-approves everything.
    For personal use only — no real auth, just satisfies ChatGPT's MCP connector."""

    def __init__(self):
        self._clients: dict[str, _Client] = {}
        self._codes: dict[str, _AuthCode] = {}
        self._tokens: dict[str, _Token] = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        c = self._clients.get(client_id)
        if c:
            return c.info
        # Auto-register cached client IDs (e.g. after server restart)
        info = OAuthClientInformationFull(
            client_id=client_id,
            redirect_uris=[],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="none",
        )
        await self.register_client(info)
        return info

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = _Client(info=client_info)

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        code = secrets.token_urlsafe(32)
        self._codes[code] = _AuthCode(
            code=code,
            client_id=client.client_id,
            redirect_uri=params.redirect_uri,
            code_challenge=params.code_challenge,
        )
        redirect_uri = str(params.redirect_uri)
        sep = "&" if "?" in redirect_uri else "?"
        return f"{redirect_uri}{sep}code={code}&state={params.state}"

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        c = self._codes.get(authorization_code)
        if not c or c.client_id != client.client_id:
            return None
        return AuthorizationCode(
            code=c.code,
            client_id=c.client_id,
            redirect_uri=c.redirect_uri,
            code_challenge=c.code_challenge,
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        self._codes.pop(authorization_code.code, None)
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        self._tokens[access] = _Token(
            token=access, client_id=client.client_id, scopes=["mcp"]
        )
        self._tokens[refresh] = _Token(
            token=refresh, client_id=client.client_id, scopes=["mcp"]
        )
        return OAuthToken(
            access_token=access,
            token_type="Bearer",
            expires_in=86400,
            refresh_token=refresh,
            scope="mcp",
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        t = self._tokens.get(refresh_token)
        if not t or t.client_id != client.client_id:
            return None
        return RefreshToken(token=t.token, client_id=t.client_id, scopes=t.scopes)

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        self._tokens.pop(refresh_token.token, None)
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        self._tokens[access] = _Token(
            token=access, client_id=client.client_id, scopes=scopes
        )
        self._tokens[refresh] = _Token(
            token=refresh, client_id=client.client_id, scopes=scopes
        )
        return OAuthToken(
            access_token=access,
            token_type="Bearer",
            expires_in=86400,
            refresh_token=refresh,
            scope=" ".join(scopes),
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        t = self._tokens.get(token)
        if not t:
            return None
        if t.expires_at < time.time():
            return None
        return AccessToken(token=t.token, client_id=t.client_id, scopes=t.scopes)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        self._tokens.pop(token.token, None)
