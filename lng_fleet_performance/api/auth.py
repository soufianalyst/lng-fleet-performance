"""Authentication module — JWT tokens, password hashing, user management."""
import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

router = APIRouter()

JWT_SECRET = os.environ.get("JWT_SECRET", "lng-fleet-performance-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, h = password_hash.split(":", 1)
        return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest() == h
    except (ValueError, AttributeError):
        return False


def create_token(user_id: int, username: str, role: str) -> str:
    import hmac
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_EXPIRY_HOURS)).timestamp()),
    }
    import json, base64
    header = base64.urlsafe_b64encode(json.dumps({"alg": JWT_ALGORITHM, "typ": "JWT"}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    sig_input = f"{header}.{body}".encode()
    sig = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{header}.{body}.{sig_b64}"


def decode_token(token: str) -> Optional[dict]:
    import hmac, json, base64
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, body_b64, sig_b64 = parts
        sig_input = f"{header_b64}.{body_b64}".encode()
        expected_sig = hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest()
        padding = 4 - len(sig_b64) % 4
        if padding != 4:
            sig_b64 += "=" * padding
        actual_sig = base64.urlsafe_b64decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        padding = 4 - len(body_b64) % 4
        if padding != 4:
            body_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(body_b64))
        if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
            return None
        return payload
    except Exception:
        return None


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "viewer"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/login")
async def login(req: LoginRequest):
    from ..api.deps import get_db
    db = get_db()
    row = db.fetchone("SELECT * FROM users WHERE username=? AND is_active=1", (req.username,))
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    row_dict = dict(row) if hasattr(row, 'keys') else row
    if not verify_password(req.password, row_dict["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(row_dict["user_id"], row_dict["username"], row_dict["role"])
    return {
        "token": token,
        "user": {
            "user_id": row_dict["user_id"],
            "username": row_dict["username"],
            "email": row_dict["email"],
            "role": row_dict["role"],
        },
    }


@router.get("/me")
async def me(user=Depends(get_current_user)):
    from ..api.deps import get_db
    db = get_db()
    row = db.fetchone("SELECT user_id, username, email, role, is_active, created_at FROM users WHERE user_id=?", (int(user["sub"]),))
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    row_dict = dict(row) if hasattr(row, 'keys') else row
    return {"user": row_dict}


@router.get("/users")
async def list_users(user=Depends(require_admin)):
    from ..api.deps import get_db
    db = get_db()
    rows = db.fetchall("SELECT user_id, username, email, role, is_active, created_at FROM users ORDER BY user_id")
    return {"users": [dict(r) if hasattr(r, 'keys') else r for r in rows]}


@router.post("/users")
async def create_user(req: CreateUserRequest, user=Depends(require_admin)):
    from ..api.deps import get_db
    if req.role not in ("admin", "viewer"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'viewer'")
    db = get_db()
    existing = db.fetchone("SELECT user_id FROM users WHERE username=? OR email=?", (req.username, req.email))
    if existing:
        raise HTTPException(status_code=409, detail="Username or email already exists")
    pw_hash = hash_password(req.password)
    db.execute(
        "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (req.username, req.email, pw_hash, req.role),
    )
    return {"message": "User created", "username": req.username, "role": req.role}


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, user=Depends(require_admin)):
    from ..api.deps import get_db
    if int(user["sub"]) == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db = get_db()
    existing = db.fetchone("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    db.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    return {"message": "User deleted"}


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, user=Depends(get_current_user)):
    from ..api.deps import get_db
    db = get_db()
    row = db.fetchone("SELECT * FROM users WHERE user_id=?", (int(user["sub"]),))
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    row_dict = dict(row) if hasattr(row, 'keys') else row
    if not verify_password(req.old_password, row_dict["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    new_hash = hash_password(req.new_password)
    db.execute("UPDATE users SET password_hash=? WHERE user_id=?", (new_hash, int(user["sub"])))
    return {"message": "Password changed"}


def seed_admin_user(db):
    existing = db.fetchone("SELECT user_id FROM users WHERE username='admin'")
    if existing:
        return
    pw_hash = hash_password("admin123")
    try:
        db.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("admin", "admin@lngfleet.com", pw_hash, "admin"),
        )
        print("[auth] Default admin user created (admin / admin123)")
    except Exception as e:
        print(f"[auth] Admin seed skipped: {e}")
