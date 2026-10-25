import hmac
import os

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.errors import ApiError

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="bearerAuth",
    description="Token de serviço `SYNC_API_TOKEN`, enviado como Bearer. Não é um JWT do api-auth.",
)


def require_sync_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    expected_token = os.environ.get("SYNC_API_TOKEN", "")
    if not expected_token:
        raise ApiError(503, "DEPENDENCY_UNAVAILABLE", "SYNC_API_TOKEN não está configurado.")
    if credentials is None or not hmac.compare_digest(credentials.credentials, expected_token):
        raise ApiError(
            401,
            "UNAUTHENTICATED",
            "Token Bearer ausente ou inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
