from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from pydantic import BaseModel

from pis_platform.errors import UnauthorizedError


class TokenPayload(BaseModel):
    sub: str
    role: str = "user"
    exp: datetime


def create_access_token(subject: str, secret: str, algorithm: str, minutes: int = 120, role: str = "user") -> str:
    payload = {
        "sub": subject,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str, secret: str, algorithm: str) -> TokenPayload:
    try:
        data = jwt.decode(token, secret, algorithms=[algorithm])
        return TokenPayload.model_validate(data)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

