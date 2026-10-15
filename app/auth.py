import hmac
import os

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)


def require_sync_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    expected_token = os.environ.get("SYNC_API_TOKEN", "")
    if not expected_token:
        raise HTTPException(status_code=503, detail="SYNC_API_TOKEN is not configured")
    if credentials is None or not hmac.compare_digest(credentials.credentials, expected_token):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
