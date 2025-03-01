import requests
import json
import base64
import os
import time
from urllib.parse import urljoin

# Import the configuration
try:
    from client_config import SERVER_URL
except ImportError:
    SERVER_URL = "http://localhost:8000/api/"


class ServerAPI:
    def __init__(self, base_url=SERVER_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
        self.user_id = None
        self.load_auth_token()

    def load_auth_token(self):
        """Load authentication token from file if it exists"""
        try:
            with open('UserData/auth_token.txt', 'r') as file:
                self.auth_token = file.read().strip()
                self.session.headers.update({'Authorization': f'Bearer {self.auth_token}'})
                return True
        except FileNotFoundError:
            return False

    def save_auth_token(self, token):
        """Save authentication token to file"""
        os.makedirs('UserData', exist_ok=True)
        with open('UserData/auth_token.txt', 'w') as file:
            file.write(token)
        self.auth_token = token
        self.session.headers.update({'Authorization': f'Bearer {token}'})

    def register(self, username, password, email, public_key_pem):
        """Register a new user"""
        url = urljoin(self.base_url, 'auth/register')
        data = {
            'username': username,
            'password': password,
            'email': email,
            'public_key': base64.b64encode(public_key_pem).decode('utf-8')
        }

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                self.save_auth_token(result.get('token'))
                self.user_id = result.get('user_id')
                return True, result.get('message', 'Registration successful')
            else:
                return False, result.get('message', 'Registration failed')
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}"

    def login(self, username, password):
        """Login to the server"""
        url = urljoin(self.base_url, 'auth/login')
        data = {
            'username': username,
            'password': password
        }

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                self.save_auth_token(result.get('token'))
                self.user_id = result.get('user_id')
                return True, result.get('message', 'Login successful')
            else:
                return False, result.get('message', 'Login failed')
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}"

    def send_message(self, recipient_id, encrypted_message):
        """Send an encrypted message to a recipient"""
        if not self.auth_token:
            return False, "Not authenticated"

        url = urljoin(self.base_url, 'messages/send')
        data = {
            'recipient_id': recipient_id,
            'encrypted_key': encrypted_message['key'],
            'encrypted_content': encrypted_message['message'],
            'timestamp': int(time.time())
        }

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return True, result.get('message_id')
            else:
                return False, result.get('message', 'Failed to send message')
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}"

    def get_messages(self, since_timestamp=0):
        """Get new messages from the server"""
        if not self.auth_token:
            return False, "Not authenticated", []

        url = urljoin(self.base_url, 'messages/receive')
        params = {'since': since_timestamp}

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return True, "Messages retrieved", result.get('messages', [])
            else:
                return False, result.get('message', 'Failed to retrieve messages'), []
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}", []

    def get_friend_public_key(self, friend_username):
        """Get a friend's public key from the server"""
        if not self.auth_token:
            return False, "Not authenticated", None

        url = urljoin(self.base_url, 'users/public-key')
        params = {'username': friend_username}

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                public_key_pem = base64.b64decode(result.get('public_key'))
                return True, "Public key retrieved", public_key_pem
            else:
                return False, result.get('message', 'Failed to retrieve public key'), None
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}", None

    def add_friend(self, friend_username):
        """Send a friend request to another user"""
        if not self.auth_token:
            return False, "Not authenticated"

        url = urljoin(self.base_url, 'friends/add')
        data = {'username': friend_username}

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return True, result.get('message', 'Friend request sent')
            else:
                return False, result.get('message', 'Failed to send friend request')
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}"

    def get_friend_requests(self):
        """Get pending friend requests"""
        if not self.auth_token:
            return False, "Not authenticated", []

        url = urljoin(self.base_url, 'friends/requests')

        try:
            response = self.session.get(url)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return True, "Friend requests retrieved", result.get('requests', [])
            else:
                return False, result.get('message', 'Failed to retrieve friend requests'), []
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}", []

    def backup_user_data(self, data):
        """Backup user data to the server"""
        if not self.auth_token:
            return False, "Not authenticated"

        url = urljoin(self.base_url, 'users/backup')

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return True, result.get('message', 'Data backed up successfully')
            else:
                return False, result.get('message', 'Failed to backup data')
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}"

    def restore_user_data(self):
        """Restore user data from the server"""
        if not self.auth_token:
            return False, "Not authenticated", None

        url = urljoin(self.base_url, 'users/restore')

        try:
            response = self.session.get(url)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return True, "Data restored successfully", result.get('data')
            else:
                return False, result.get('message', 'Failed to restore data'), None
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}", None

    def search_users(self, query):
        """Search for users on the server"""
        if not self.auth_token:
            return False, "Not authenticated", []

        url = urljoin(self.base_url, 'users/search')
        params = {'query': query}

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return True, "Users found", result.get('users', [])
            else:
                return False, result.get('message', 'Failed to search users'), []
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}", []

    def create_group(self, name, members):
        """Create a new group chat"""
        if not self.auth_token:
            return False, "Not authenticated"

        url = urljoin(self.base_url, 'groups/create')
        data = {
            'name': name,
            'members': members
        }

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return True, result.get('group_id')
            else:
                return False, result.get('message', 'Failed to create group')
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}"

    def get_group_messages(self, since_timestamp=0):
        """Get new group messages from the server"""
        if not self.auth_token:
            return False, "Not authenticated", []

        url = urljoin(self.base_url, 'messages/group')
        params = {'since': since_timestamp}

        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return True, "Group messages retrieved", result.get('messages', [])
            else:
                return False, result.get('message', 'Failed to retrieve group messages'), []
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}", []

    def send_group_message(self, group_id, encrypted_message):
        """Send an encrypted message to a group"""
        if not self.auth_token:
            return False, "Not authenticated"

        url = urljoin(self.base_url, 'messages/send')
        data = {
            'recipient_id': group_id,
            'encrypted_key': encrypted_message['key'],
            'encrypted_content': encrypted_message['message'],
            'timestamp': int(time.time()),
            'is_group': True
        }

        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                return True, result.get('message_id')
            else:
                return False, result.get('message', 'Failed to send group message')
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}"

