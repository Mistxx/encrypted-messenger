import os
import json
import time
from typing import Dict, List, Optional, Any, Union
import sqlite3
from pathlib import Path


class Database:
    def __init__(self, db_path: str = "server/data/secureconnect.db"):
        """Initialize the database connection"""
        self.db_path = db_path
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = self._create_connection()
        self._create_tables()

    def _create_connection(self) -> sqlite3.Connection:
        """Create a database connection"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn

    def _create_tables(self):
        """Create the necessary tables if they don't exist"""
        cursor = self.conn.cursor()

        # Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            public_key TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            last_login INTEGER
        )
        ''')

        # Auth tokens table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

        # Friends table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            friend_id INTEGER NOT NULL,
            status TEXT NOT NULL,  -- 'pending', 'accepted', 'rejected'
            created_at INTEGER NOT NULL,
            updated_at INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (friend_id) REFERENCES users (id),
            UNIQUE(user_id, friend_id)
        )
        ''')

        # Groups table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
        ''')

        # Group members table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at INTEGER NOT NULL,
            FOREIGN KEY (group_id) REFERENCES groups (id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(group_id, user_id)
        )
        ''')

        # Messages table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER NOT NULL,
            encrypted_key TEXT NOT NULL,
            encrypted_content TEXT NOT NULL,
            is_group BOOLEAN NOT NULL DEFAULT 0,
            timestamp INTEGER NOT NULL,
            delivered BOOLEAN NOT NULL DEFAULT 0,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (recipient_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')

        # User backups table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            backup_data TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        ''')

        self.conn.commit()

    # User management methods
    def create_user(self, username: str, email: str, password_hash: str, public_key: str) -> int:
        """Create a new user and return the user ID"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, public_key, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, email, password_hash, public_key, int(time.time()))
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Username or email already exists
            return 0

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get a user by username"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        return dict(user) if user else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get a user by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return dict(user) if user else None

    def update_last_login(self, user_id: int):
        """Update the last login timestamp for a user"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (int(time.time()), user_id)
        )
        self.conn.commit()

    # Authentication methods
    def create_auth_token(self, user_id: int, token: str, expires_in: int = 604800) -> bool:
        """Create a new authentication token (default expiry: 7 days)"""
        cursor = self.conn.cursor()
        now = int(time.time())
        expires_at = now + expires_in

        try:
            cursor.execute(
                "INSERT INTO auth_tokens (user_id, token, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (user_id, token, now, expires_at)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def validate_auth_token(self, token: str) -> Optional[int]:
        """Validate an authentication token and return the user ID if valid"""
        cursor = self.conn.cursor()
        now = int(time.time())

        cursor.execute(
            "SELECT user_id FROM auth_tokens WHERE token = ? AND expires_at > ?",
            (token, now)
        )
        result = cursor.fetchone()

        return result['user_id'] if result else None

    def delete_auth_token(self, token: str) -> bool:
        """Delete an authentication token (logout)"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        self.conn.commit()
        return cursor.rowcount > 0

    # Friend management methods
    def add_friend_request(self, user_id: int, friend_username: str) -> Dict[str, Any]:
        """Send a friend request"""
        cursor = self.conn.cursor()

        # Get the friend's user ID
        cursor.execute("SELECT id FROM users WHERE username = ?", (friend_username,))
        friend = cursor.fetchone()

        if not friend:
            return {"success": False, "message": "User not found"}

        friend_id = friend['id']

        if user_id == friend_id:
            return {"success": False, "message": "You cannot add yourself as a friend"}

        # Check if a friend request already exists
        cursor.execute(
            "SELECT * FROM friends WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)",
            (user_id, friend_id, friend_id, user_id)
        )
        existing = cursor.fetchone()

        if existing:
            if existing['status'] == 'accepted':
                return {"success": False, "message": "Already friends"}
            elif existing['status'] == 'pending':
                return {"success": False, "message": "Friend request already pending"}
            elif existing['status'] == 'rejected':
                # Update the rejected request to pending
                cursor.execute(
                    "UPDATE friends SET status = 'pending', updated_at = ? WHERE id = ?",
                    (int(time.time()), existing['id'])
                )
                self.conn.commit()
                return {"success": True, "message": "Friend request sent"}

        # Create a new friend request
        now = int(time.time())
        cursor.execute(
            "INSERT INTO friends (user_id, friend_id, status, created_at) VALUES (?, ?, 'pending', ?)",
            (user_id, friend_id, now)
        )
        self.conn.commit()

        return {"success": True, "message": "Friend request sent"}

    def get_friend_requests(self, user_id: int) -> List[Dict]:
        """Get pending friend requests for a user"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT f.id, f.user_id, f.status, f.created_at, u.username 
            FROM friends f
            JOIN users u ON f.user_id = u.id
            WHERE f.friend_id = ? AND f.status = 'pending'
        """, (user_id,))

        requests = []
        for row in cursor.fetchall():
            requests.append(dict(row))

        return requests

    def respond_to_friend_request(self, request_id: int, user_id: int, accept: bool) -> Dict[str, Any]:
        """Accept or reject a friend request"""
        cursor = self.conn.cursor()

        # Verify the request is for this user
        cursor.execute(
            "SELECT * FROM friends WHERE id = ? AND friend_id = ?",
            (request_id, user_id)
        )
        request = cursor.fetchone()

        if not request:
            return {"success": False, "message": "Friend request not found"}

        status = 'accepted' if accept else 'rejected'
        now = int(time.time())

        cursor.execute(
            "UPDATE friends SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, request_id)
        )

        if accept:
            # Create the reverse relationship
            cursor.execute(
                "INSERT INTO friends (user_id, friend_id, status, created_at) VALUES (?, ?, 'accepted', ?)",
                (user_id, request['user_id'], now)
            )

        self.conn.commit()

        return {
            "success": True,
            "message": f"Friend request {status}"
        }

    def get_friends(self, user_id: int) -> List[Dict]:
        """Get a user's friends"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT u.id, u.username, f.created_at as friends_since
            FROM friends f
            JOIN users u ON f.friend_id = u.id
            WHERE f.user_id = ? AND f.status = 'accepted'
        """, (user_id,))

        friends = []
        for row in cursor.fetchall():
            friends.append(dict(row))

        return friends

    # Message methods
    def save_message(self, sender_id: int, recipient_id: int, encrypted_key: str,
                     encrypted_content: str, is_group: bool = False) -> int:
        """Save a message and return the message ID"""
        cursor = self.conn.cursor()

        cursor.execute(
            """INSERT INTO messages 
               (sender_id, recipient_id, encrypted_key, encrypted_content, is_group, timestamp) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (sender_id, recipient_id, encrypted_key, encrypted_content,
             1 if is_group else 0, int(time.time()))
        )
        self.conn.commit()

        return cursor.lastrowid

    def get_messages(self, user_id: int, since_timestamp: int = 0) -> List[Dict]:
        """Get messages for a user since a specific timestamp"""
        cursor = self.conn.cursor()

        # Get direct messages where the user is the recipient
        cursor.execute("""
            SELECT m.id, m.sender_id, u.username as sender, m.encrypted_key, 
                   m.encrypted_content, m.timestamp, m.is_group
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.recipient_id = ? AND m.timestamp > ? AND m.is_group = 0
            ORDER BY m.timestamp ASC
        """, (user_id, since_timestamp))

        messages = []
        for row in cursor.fetchall():
            messages.append(dict(row))

        # Mark messages as delivered
        if messages:
            message_ids = [m['id'] for m in messages]
            placeholders = ','.join(['?'] * len(message_ids))
            cursor.execute(
                f"UPDATE messages SET delivered = 1 WHERE id IN ({placeholders})",
                message_ids
            )
            self.conn.commit()

        return messages

    def get_group_messages(self, user_id: int, since_timestamp: int = 0) -> List[Dict]:
        """Get group messages for a user since a specific timestamp"""
        cursor = self.conn.cursor()

        # Get group messages for groups the user is a member of
        cursor.execute("""
            SELECT m.id, m.sender_id, u.username as sender, g.id as group_id, 
                   g.name as group_name, m.encrypted_key, m.encrypted_content, m.timestamp
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            JOIN groups g ON m.recipient_id = g.id
            JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.user_id = ? AND m.timestamp > ? AND m.is_group = 1
            ORDER BY m.timestamp ASC
        """, (user_id, since_timestamp))

        messages = []
        for row in cursor.fetchall():
            messages.append(dict(row))

        return messages

    # Group methods
    def create_group(self, name: str, created_by: int) -> int:
        """Create a new group and return the group ID"""
        cursor = self.conn.cursor()
        now = int(time.time())

        cursor.execute(
            "INSERT INTO groups (name, created_by, created_at) VALUES (?, ?, ?)",
            (name, created_by, now)
        )
        group_id = cursor.lastrowid

        # Add the creator as a member
        cursor.execute(
            "INSERT INTO group_members (group_id, user_id, joined_at) VALUES (?, ?, ?)",
            (group_id, created_by, now)
        )

        self.conn.commit()
        return group_id

    def add_group_member(self, group_id: int, user_id: int) -> bool:
        """Add a user to a group"""
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO group_members (group_id, user_id, joined_at) VALUES (?, ?, ?)",
                (group_id, user_id, int(time.time()))
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_user_groups(self, user_id: int) -> List[Dict]:
        """Get groups a user is a member of"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT g.id, g.name, g.created_at, u.username as created_by
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            JOIN users u ON g.created_by = u.id
            WHERE gm.user_id = ?
        """, (user_id,))

        groups = []
        for row in cursor.fetchall():
            groups.append(dict(row))

        return groups

    def get_group_members(self, group_id: int) -> List[Dict]:
        """Get members of a group"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT u.id, u.username, gm.joined_at
            FROM group_members gm
            JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id = ?
        """, (group_id,))

        members = []
        for row in cursor.fetchall():
            members.append(dict(row))

        return members

    # Backup methods
    def save_user_backup(self, user_id: int, backup_data: str) -> bool:
        """Save a user's backup data"""
        cursor = self.conn.cursor()
        now = int(time.time())

        # First delete any existing backups for this user
        cursor.execute("DELETE FROM user_backups WHERE user_id = ?", (user_id,))

        # Then save the new backup
        cursor.execute(
            "INSERT INTO user_backups (user_id, backup_data, timestamp) VALUES (?, ?, ?)",
            (user_id, backup_data, now)
        )
        self.conn.commit()

        return True

    def get_user_backup(self, user_id: int) -> Optional[Dict]:
        """Get a user's most recent backup"""
        cursor = self.conn.cursor()

        cursor.execute(
            "SELECT * FROM user_backups WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
            (user_id,)
        )

        backup = cursor.fetchone()
        return dict(backup) if backup else None

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
