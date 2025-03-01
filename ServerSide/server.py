import os
import time
import json
import secrets
import hashlib
import base64
import uvicorn
from typing import Dict, List, Optional, Any, Union
from fastapi import FastAPI, HTTPException, Depends, Header, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from database import Database

# Initialize FastAPI app
app = FastAPI(title="SecureConnect ServerSide")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your client's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = Database()


# Models for request/response data
class UserRegister(BaseModel):
    username: str
    password: str
    email: EmailStr
    public_key: str


class UserLogin(BaseModel):
    username: str
    password: str


class FriendRequest(BaseModel):
    username: str


class MessageSend(BaseModel):
    recipient_id: str
    encrypted_key: str
    encrypted_content: str
    timestamp: int
    is_group: bool = False


class GroupCreate(BaseModel):
    name: str
    members: List[str] = []


class GroupAddMember(BaseModel):
    username: str


# Authentication dependency
async def get_current_user(authorization: str = Header(None)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    user_id = db.validate_auth_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


# Helper functions
def hash_password(password: str) -> str:
    """Hash a password for storage"""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    return base64.b64encode(salt + key).decode('utf-8')


def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        stored_bytes = base64.b64decode(stored_password)
        salt = stored_bytes[:32]
        stored_key = stored_bytes[32:]

        key = hashlib.pbkdf2_hmac(
            'sha256',
            provided_password.encode('utf-8'),
            salt,
            100000
        )

        return key == stored_key
    except:
        return False


def generate_token() -> str:
    """Generate a secure random token"""
    return secrets.token_hex(32)


# Routes
@app.get("/")
async def root():
    return {"message": "SecureConnect ServerSide API"}


# Authentication routes
@app.post("/api/auth/register")
async def register(user: UserRegister):
    # Hash the password
    password_hash = hash_password(user.password)

    # Create the user
    user_id = db.create_user(
        user.username,
        user.email,
        password_hash,
        user.public_key
    )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )

    # Create an authentication token
    token = generate_token()
    db.create_auth_token(user_id, token)

    return {
        "success": True,
        "message": "Registration successful",
        "token": token,
        "user_id": user_id
    }


@app.post("/api/auth/login")
async def login(user: UserLogin):
    # Get the user
    db_user = db.get_user_by_username(user.username)

    if not db_user or not verify_password(db_user["password_hash"], user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Update last login time
    db.update_last_login(db_user["id"])

    # Create a new token
    token = generate_token()
    db.create_auth_token(db_user["id"], token)

    return {
        "success": True,
        "message": "Login successful",
        "token": token,
        "user_id": db_user["id"]
    }


@app.post("/api/auth/logout")
async def logout(user_id: int = Depends(get_current_user), authorization: str = Header(None)):
    token = authorization.split(" ")[1]
    db.delete_auth_token(token)

    return {
        "success": True,
        "message": "Logout successful"
    }


# User routes
@app.get("/api/users/public-key")
async def get_public_key(username: str, user_id: int = Depends(get_current_user)):
    user = db.get_user_by_username(username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "success": True,
        "username": user["username"],
        "public_key": user["public_key"]
    }


@app.get("/api/users/search")
async def search_users(query: str, user_id: int = Depends(get_current_user)):
    # This is a simple implementation - in a real app, you'd want more sophisticated search
    cursor = db.conn.cursor()
    cursor.execute(
        "SELECT id, username FROM users WHERE username LIKE ? AND id != ? LIMIT 20",
        (f"%{query}%", user_id)
    )

    users = []
    for row in cursor.fetchall():
        users.append(dict(row))

    return {
        "success": True,
        "users": users
    }


# Friend routes
@app.post("/api/friends/add")
async def add_friend(request: FriendRequest, user_id: int = Depends(get_current_user)):
    result = db.add_friend_request(user_id, request.username)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    return result


@app.get("/api/friends/requests")
async def get_friend_requests(user_id: int = Depends(get_current_user)):
    requests = db.get_friend_requests(user_id)

    return {
        "success": True,
        "requests": requests
    }


@app.post("/api/friends/respond/{request_id}")
async def respond_to_friend_request(
        request_id: int,
        accept: bool,
        user_id: int = Depends(get_current_user)
):
    result = db.respond_to_friend_request(request_id, user_id, accept)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )

    return result


@app.get("/api/friends")
async def get_friends(user_id: int = Depends(get_current_user)):
    friends = db.get_friends(user_id)

    return {
        "success": True,
        "friends": friends
    }


# Message routes
@app.post("/api/messages/send")
async def send_message(message: MessageSend, user_id: int = Depends(get_current_user)):
    # Convert recipient_id to int
    try:
        recipient_id = int(message.recipient_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recipient ID"
        )

    # Check if recipient exists
    recipient = db.get_user_by_id(recipient_id)
    if not recipient and not message.is_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient not found"
        )

    # Save the message
    message_id = db.save_message(
        user_id,
        recipient_id,
        message.encrypted_key,
        message.encrypted_content,
        message.is_group
    )

    return {
        "success": True,
        "message_id": message_id
    }


@app.get("/api/messages/receive")
async def receive_messages(since: int = 0, user_id: int = Depends(get_current_user)):
    messages = db.get_messages(user_id, since)

    return {
        "success": True,
        "messages": messages
    }


@app.get("/api/messages/group")
async def receive_group_messages(since: int = 0, user_id: int = Depends(get_current_user)):
    messages = db.get_group_messages(user_id, since)

    return {
        "success": True,
        "messages": messages
    }


# Group routes
@app.post("/api/groups/create")
async def create_group(group: GroupCreate, user_id: int = Depends(get_current_user)):
    group_id = db.create_group(group.name, user_id)

    # Add members
    for username in group.members:
        user = db.get_user_by_username(username)
        if user:
            db.add_group_member(group_id, user["id"])

    return {
        "success": True,
        "group_id": group_id,
        "message": "Group created successfully"
    }


@app.post("/api/groups/{group_id}/add")
async def add_group_member(
        group_id: int,
        request: GroupAddMember,
        user_id: int = Depends(get_current_user)
):
    # Check if the user is a member of the group
    cursor = db.conn.cursor()
    cursor.execute(
        "SELECT * FROM group_members WHERE group_id = ? AND user_id = ?",
        (group_id, user_id)
    )

    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group"
        )

    # Get the user to add
    user_to_add = db.get_user_by_username(request.username)
    if not user_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Add the user to the group
    success = db.add_group_member(group_id, user_to_add["id"])

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this group"
        )

    return {
        "success": True,
        "message": f"Added {request.username} to the group"
    }


@app.get("/api/groups")
async def get_groups(user_id: int = Depends(get_current_user)):
    groups = db.get_user_groups(user_id)

    return {
        "success": True,
        "groups": groups
    }


@app.get("/api/groups/{group_id}/members")
async def get_group_members(group_id: int, user_id: int = Depends(get_current_user)):
    # Check if the user is a member of the group
    cursor = db.conn.cursor()
    cursor.execute(
        "SELECT * FROM group_members WHERE group_id = ? AND user_id = ?",
        (group_id, user_id)
    )

    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group"
        )

    members = db.get_group_members(group_id)

    return {
        "success": True,
        "members": members
    }


# Backup routes
@app.post("/api/users/backup")
async def True,


"members": members
}

# Backup routes
@app.post("/api/users/backup")
async


def backup_user_data(request: Request, user_id: int = Depends(get_current_user)):
    # Get the request body as JSON
    backup_data = await request.json()

    # Save the backup
    success = db.save_user_backup(user_id, json.dumps(backup_data))

    return {
        "success": success,
        "message": "Data backed up successfully" if success else "Failed to backup data"
    }


@app.get("/api/users/restore")
async def restore_user_data(user_id: int = Depends(get_current_user)):
    backup = db.get_user_backup(user_id)

    if not backup:
        return {
            "success": False,
            "message": "No backup found"
        }

    try:
        data = json.loads(backup["backup_data"])
        return {
            "success": True,
            "message": "Data restored successfully",
            "data": data
        }
    except json.JSONDecodeError:
        return {
            "success": False,
            "message": "Failed to parse backup data"
        }


# Main entry point
if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
