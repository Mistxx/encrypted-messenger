import base64
import os
import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet


class EncryptionManager:
    def __init__(self):
        self.symmetric_key = None
        self.private_key = None
        self.public_key = None
        self.friend_public_keys = {}
        self.load_or_generate_keys()

    def load_or_generate_keys(self):
        """Load existing keys or generate new ones if they don't exist"""
        os.makedirs('UserData/Keys', exist_ok=True)

        # Load or generate symmetric key
        try:
            with open('UserData/Keys/symmetric.key', 'rb') as key_file:
                self.symmetric_key = key_file.read()
        except FileNotFoundError:
            self.symmetric_key = Fernet.generate_key()
            with open('UserData/Keys/symmetric.key', 'wb') as key_file:
                key_file.write(self.symmetric_key)

        # Load or generate asymmetric keys
        try:
            with open('UserData/Keys/private.pem', 'rb') as key_file:
                self.private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None
                )

            with open('UserData/Keys/public.pem', 'rb') as key_file:
                self.public_key = serialization.load_pem_public_key(
                    key_file.read()
                )
        except FileNotFoundError:
            # Generate new RSA key pair
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            self.public_key = self.private_key.public_key()

            # Save private key
            pem_private = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open('UserData/Keys/private.pem', 'wb') as key_file:
                key_file.write(pem_private)

            # Save public key
            pem_public = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            with open('UserData/Keys/public.pem', 'wb') as key_file:
                key_file.write(pem_public)

    def load_friend_public_key(self, friend_username):
        """Load a friend's public key from file"""
        key_path = f'UserData/Keys/friends/{friend_username}.pem'
        try:
            with open(key_path, 'rb') as key_file:
                key_data = key_file.read()
                self.friend_public_keys[friend_username] = serialization.load_pem_public_key(key_data)
                return True
        except (FileNotFoundError, Exception) as e:
            print(f"Error loading public key for {friend_username}: {e}")
            return False

    def save_friend_public_key(self, friend_username, public_key_pem):
        """Save a friend's public key to file"""
        os.makedirs('UserData/Keys/friends', exist_ok=True)
        key_path = f'UserData/Keys/friends/{friend_username}.pem'
        try:
            with open(key_path, 'wb') as key_file:
                key_file.write(public_key_pem)
            # Also load it into memory
            self.friend_public_keys[friend_username] = serialization.load_pem_public_key(public_key_pem)
            return True
        except Exception as e:
            print(f"Error saving public key for {friend_username}: {e}")
            return False

    def encrypt_message(self, message, recipient_username):
        """Encrypt a message for a specific recipient using their public key"""
        if recipient_username not in self.friend_public_keys:
            if not self.load_friend_public_key(recipient_username):
                return None

        try:
            # Generate a one-time symmetric key for this message
            message_key = Fernet.generate_key()
            cipher = Fernet(message_key)

            # Encrypt the message with the symmetric key
            encrypted_message = cipher.encrypt(message.encode('utf-8'))

            # Encrypt the symmetric key with the recipient's public key
            encrypted_key = self.friend_public_keys[recipient_username].encrypt(
                message_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            # Combine the encrypted key and message
            result = {
                'key': base64.b64encode(encrypted_key).decode('utf-8'),
                'message': base64.b64encode(encrypted_message).decode('utf-8')
            }

            return result
        except Exception as e:
            print(f"Encryption error: {e}")
            return None

    def decrypt_message(self, encrypted_data):
        """Decrypt a message using the private key"""
        try:
            # Decode the encrypted key and message
            encrypted_key = base64.b64decode(encrypted_data['key'])
            encrypted_message = base64.b64decode(encrypted_data['message'])

            # Decrypt the symmetric key with our private key
            message_key = self.private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

            # Decrypt the message with the symmetric key
            cipher = Fernet(message_key)
            decrypted_message = cipher.decrypt(encrypted_message).decode('utf-8')

            return decrypted_message
        except Exception as e:
            print(f"Decryption error: {e}")
            return None

    def get_public_key_pem(self):
        """Get the user's public key in PEM format"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def encrypt_data_for_storage(self, data):
        """Encrypt data for local storage using symmetric encryption"""
        try:
            cipher = Fernet(self.symmetric_key)
            if isinstance(data, str):
                data = data.encode('utf-8')
            elif isinstance(data, dict) or isinstance(data, list):
                data = json.dumps(data).encode('utf-8')

            encrypted_data = cipher.encrypt(data)
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            print(f"Storage encryption error: {e}")
            return None

    def decrypt_data_from_storage(self, encrypted_data):
        """Decrypt data from local storage using symmetric encryption"""
        try:
            cipher = Fernet(self.symmetric_key)
            decrypted_data = cipher.decrypt(base64.b64decode(encrypted_data))
            return decrypted_data
        except Exception as e:
            print(f"Storage decryption error: {e}")
            return None

    def encrypt_group_message(self, message, group_members):
        """Encrypt a message for multiple recipients"""
        encrypted_messages = {}

        for member in group_members:
            encrypted_message = self.encrypt_message(message, member)
            if encrypted_message:
                encrypted_messages[member] = encrypted_message
            else:
                return None

        return encrypted_messages

