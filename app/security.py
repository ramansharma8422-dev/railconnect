from datetime import datetime, timedelta
from uuid import uuid4
import hashlib
import bcrypt
from jose import jwt, JWTError
from app.config import settings

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False

def create_access_token(user_id: int) -> tuple[str, str, datetime]:
    expires = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    jti = str(uuid4())
    payload = {"sub": str(user_id), "jti": jti, "exp": expires, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), jti, expires

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_reset_token() -> str:
    return uuid4().hex + uuid4().hex
