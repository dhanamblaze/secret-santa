import os
import sqlite3
import random
import string
import secrets
import hmac
import hashlib
import time
from typing import Optional, List
from contextlib import contextmanager

import bcrypt
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Database file location
DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "christmas-santa-super-secret-key-2026")

app = FastAPI(title="Christmas Chris Secret Santa", version="1.0.0")

# Enable CORS for flexible deployments (Render, Vercel, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        # Users table - Dynamic signup/login with hashed passwords
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Groups table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                creator_id INTEGER NOT NULL,
                is_shuffled INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES users (id)
            )
        """)

        # Group members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                wishlist TEXT DEFAULT '',
                assigned_recipient_id INTEGER DEFAULT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(group_id, user_id),
                FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (assigned_recipient_id) REFERENCES users (id)
            )
        """)


init_db()


# --- Security & Token Utilities ---

def hash_password(password: str) -> str:
    """Hash password using bcrypt without character restrictions."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: int, username: str) -> str:
    """Create a tamper-proof signed session token."""
    expiry = int(time.time()) + (30 * 24 * 3600)  # 30 days valid
    payload = f"{user_id}:{username}:{expiry}"
    signature = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def verify_token(token: str) -> Optional[dict]:
    """Verify signed session token."""
    try:
        parts = token.split(":")
        if len(parts) != 4:
            return None
        user_id_str, username, expiry_str, received_sig = parts
        payload = f"{user_id_str}:{username}:{expiry_str}"
        expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(received_sig, expected_sig):
            return None
        if int(expiry_str) < time.time():
            return None
        return {"id": int(user_id_str), "username": username}
    except Exception:
        return None


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session token")
    return user


def generate_group_code(length: int = 6) -> str:
    """Generate uppercase holiday group code."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # omit ambiguous characters
    return "".join(random.choice(chars) for _ in range(length))


# --- Request & Response Models ---

class AuthRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)


class JoinGroupRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=20)


class UpdateWishlistRequest(BaseModel):
    wishlist: str = Field(..., max_length=1000)


# --- Authentication Endpoints ---

@app.post("/api/auth/signup")
def signup(req: AuthRequest):
    clean_username = req.username.strip()
    if not clean_username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

    # Password with ANY special characters is fully allowed
    hashed = hash_password(req.password)

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (clean_username, hashed)
            )
            user_id = cursor.lastrowid
            token = create_token(user_id, clean_username)
            return {
                "message": "Account created successfully! Welcome to Secret Santa 🎅",
                "token": token,
                "user": {"id": user_id, "username": clean_username}
            }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username is already taken. Please choose another one.")


@app.post("/api/auth/login")
def login(req: AuthRequest):
    clean_username = req.username.strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (clean_username,))
        row = cursor.fetchone()
        if not row or not verify_password(req.password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="Invalid username or password")

        token = create_token(row["id"], row["username"])
        return {
            "message": "Login successful! 🎄",
            "token": token,
            "user": {"id": row["id"], "username": row["username"]}
        }


@app.get("/api/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    return {"user": user}


# --- Group Management Endpoints ---

@app.post("/api/groups/create")
def create_group(req: CreateGroupRequest, user: dict = Depends(get_current_user)):
    group_name = req.name.strip()
    if not group_name:
        raise HTTPException(status_code=400, detail="Group name is required")

    with get_db() as conn:
        cursor = conn.cursor()
        # Find unique code
        code = ""
        for _ in range(10):
            candidate = generate_group_code()
            cursor.execute("SELECT id FROM groups WHERE code = ?", (candidate,))
            if not cursor.fetchone():
                code = candidate
                break
        if not code:
            code = secrets.token_hex(3).upper()

        cursor.execute(
            "INSERT INTO groups (name, code, creator_id) VALUES (?, ?, ?)",
            (group_name, code, user["id"])
        )
        group_id = cursor.lastrowid

        # Add creator as the first member
        cursor.execute(
            "INSERT INTO group_members (group_id, user_id) VALUES (?, ?)",
            (group_id, user["id"])
        )

        return {
            "message": f"Group '{group_name}' created successfully! 🎁",
            "group": {
                "id": group_id,
                "name": group_name,
                "code": code,
                "creator_id": user["id"],
                "is_shuffled": 0
            }
        }


@app.post("/api/groups/join")
def join_group(req: JoinGroupRequest, user: dict = Depends(get_current_user)):
    clean_code = req.code.strip().upper()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, code, creator_id, is_shuffled FROM groups WHERE UPPER(code) = ?", (clean_code,))
        group = cursor.fetchone()
        if not group:
            raise HTTPException(status_code=404, detail="Invalid group code. Group not found.")

        # Check if already joined
        cursor.execute(
            "SELECT id FROM group_members WHERE group_id = ? AND user_id = ?",
            (group["id"], user["id"])
        )
        if cursor.fetchone():
            return {
                "message": f"You are already a member of '{group['name']}'.",
                "group_id": group["id"]
            }

        cursor.execute(
            "INSERT INTO group_members (group_id, user_id) VALUES (?, ?)",
            (group["id"], user["id"])
        )

        return {
            "message": f"Joined group '{group['name']}' successfully! 🎄",
            "group_id": group["id"]
        }


@app.get("/api/groups/my-groups")
def list_my_groups(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                g.id, g.name, g.code, g.creator_id, g.is_shuffled, g.created_at,
                (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) AS member_count,
                (g.creator_id = ?) AS is_creator
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.user_id = ?
            ORDER BY g.created_at DESC
        """, (user["id"], user["id"]))

        groups = []
        for row in cursor.fetchall():
            groups.append({
                "id": row["id"],
                "name": row["name"],
                "code": row["code"],
                "creator_id": row["creator_id"],
                "is_creator": bool(row["is_creator"]),
                "is_shuffled": bool(row["is_shuffled"]),
                "member_count": row["member_count"],
                "created_at": row["created_at"]
            })
        return {"groups": groups}


@app.get("/api/groups/{group_id}")
def get_group_details(group_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        # Verify user is member of this group
        cursor.execute("""
            SELECT gm.id, gm.wishlist, gm.assigned_recipient_id,
                   g.name, g.code, g.creator_id, g.is_shuffled, g.created_at,
                   u_creator.username as creator_name
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id AND gm.user_id = ?
            JOIN users u_creator ON g.creator_id = u_creator.id
            WHERE g.id = ?
        """, (user["id"], group_id))
        member_data = cursor.fetchone()

        if not member_data:
            raise HTTPException(status_code=403, detail="You are not a member of this group.")

        # Fetch all members of this group
        cursor.execute("""
            SELECT u.id, u.username, gm.wishlist, (u.id = ?) as is_creator
            FROM group_members gm
            JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id = ?
            ORDER BY u.username ASC
        """, (member_data["creator_id"], group_id))

        members = []
        for m in cursor.fetchall():
            members.append({
                "id": m["id"],
                "username": m["username"],
                "wishlist": m["wishlist"] or "",
                "is_creator": bool(m["is_creator"])
            })

        # Secret Santa assignment info for this user
        assignment = None
        recipient_id = member_data["assigned_recipient_id"]
        if member_data["is_shuffled"] and recipient_id:
            cursor.execute("""
                SELECT u.username, gm.wishlist 
                FROM users u
                JOIN group_members gm ON gm.user_id = u.id AND gm.group_id = ?
                WHERE u.id = ?
            """, (group_id, recipient_id))
            rec_row = cursor.fetchone()
            if rec_row:
                assignment = {
                    "recipient_username": rec_row["username"],
                    "recipient_wishlist": rec_row["wishlist"] or "No wishlist added yet. Surprise them! 🎁"
                }

        return {
            "group": {
                "id": group_id,
                "name": member_data["name"],
                "code": member_data["code"],
                "creator_name": member_data["creator_name"],
                "is_creator": member_data["creator_id"] == user["id"],
                "is_shuffled": bool(member_data["is_shuffled"]),
                "created_at": member_data["created_at"]
            },
            "my_wishlist": member_data["wishlist"] or "",
            "members": members,
            "assignment": assignment
        }


@app.put("/api/groups/{group_id}/wishlist")
def update_wishlist(group_id: int, req: UpdateWishlistRequest, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE group_members SET wishlist = ? WHERE group_id = ? AND user_id = ?",
            (req.wishlist.strip(), group_id, user["id"])
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Membership record not found.")

        return {"message": "Wishlist updated successfully! 🎁", "wishlist": req.wishlist.strip()}


@app.post("/api/groups/{group_id}/shuffle")
def shuffle_group(group_id: int, user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        # Verify group exists and user is member
        cursor.execute("SELECT id, name, creator_id FROM groups WHERE id = ?", (group_id,))
        grp = cursor.fetchone()
        if not grp:
            raise HTTPException(status_code=404, detail="Group not found.")

        # Get all member user_ids
        cursor.execute("SELECT user_id FROM group_members WHERE group_id = ?", (group_id,))
        member_rows = cursor.fetchall()
        user_ids = [r["user_id"] for r in member_rows]

        if user["id"] not in user_ids:
            raise HTTPException(status_code=403, detail="You are not a member of this group.")

        if len(user_ids) < 2:
            raise HTTPException(
                status_code=400,
                detail="At least 2 members are required to perform Secret Santa shuffle!"
            )

        # Derangement shuffle: Hamiltonian cycle ensures no one gets themselves
        shuffled = list(user_ids)
        random.shuffle(shuffled)
        n = len(shuffled)

        for i in range(n):
            giver = shuffled[i]
            receiver = shuffled[(i + 1) % n]
            cursor.execute(
                "UPDATE group_members SET assigned_recipient_id = ? WHERE group_id = ? AND user_id = ?",
                (receiver, group_id, giver)
            )

        cursor.execute("UPDATE groups SET is_shuffled = 1 WHERE id = ?", (group_id,))

        return {
            "message": f"Secret Santa shuffle complete for '{grp['name']}'! Everyone has their secret gift recipient! 🎅🎁",
            "is_shuffled": True
        }


# Mount static assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Christmas Chris Secret Santa API is running! 🎄"}


# Deployment entry point reading PORT env
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"[*] Starting Christmas Chris Secret Santa on port {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
