import json
import os
import time
from encryption import EncryptionManager


class DataManager:
    def __init__(self, encryption_manager):
        self.encryption_manager = encryption_manager
        self.message_history = {}
        self.friends = []
        self.groups = []
        self.last_sync_time = 0
        self.load_local_data()

    def load_local_data(self):
        """Load all local data including message history, friends, and groups"""
        self.load_relations()
        self.load_message_history()
        self.load_sync_time()

    def load_relations(self):
        """Load friends and groups from relations.json"""
        try:
            with open('UserData/relations.json', 'r') as file:
                data = json.load(file)
                self.friends = []
                self.groups = []
                for key in data.keys():
                    if key.startswith('f_'):
                        self.friends.append(key[2:])
                    elif key.startswith('g_'):
                        self.groups.append(key[2:])
        except FileNotFoundError:
            print("Relations file not found, creating empty lists")
        except json.JSONDecodeError:
            print("Error decoding relations file, creating empty lists")

    def load_message_history(self):
        """Load message history for all friends and groups"""
        self.message_history = {}

        # Load friend messages
        for friend in self.friends:
            file_path = f'MessageHistory/{friend}.json'
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r') as file:
                        messages = json.load(file)
                        self.message_history[friend] = messages
            except Exception as e:
                print(f"Error loading message history for {friend}: {e}")
                self.message_history[friend] = []

        # Load group messages
        for group in self.groups:
            file_path = f'MessageHistory/group_{group}.json'
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r') as file:
                        messages = json.load(file)
                        self.message_history[f"group_{group}"] = messages
            except Exception as e:
                print(f"Error loading message history for group {group}: {e}")
                self.message_history[f"group_{group}"] = []

    def load_sync_time(self):
        """Load the last sync time"""
        try:
            with open('UserData/last_sync.txt', 'r') as file:
                self.last_sync_time = int(file.read().strip())
        except FileNotFoundError:
            self.last_sync_time = 0
        except ValueError:
            print("Error parsing last sync time, using 0")
            self.last_sync_time = 0

    def save_sync_time(self):
        """Save the current sync time"""
        os.makedirs('UserData', exist_ok=True)
        with open('UserData/last_sync.txt', 'w') as file:
            file.write(str(int(time.time())))
        self.last_sync_time = int(time.time())

    def save_message(self, recipient, message, is_group=False):
        """Save a message to local storage"""
        if is_group:
            key = f"group_{recipient}"
            file_path = f'MessageHistory/group_{recipient}.json'
        else:
            key = recipient
            file_path = f'MessageHistory/{recipient}.json'

        # Ensure the message history for this recipient exists
        if key not in self.message_history:
            self.message_history[key] = []

        # Add the message to memory
        self.message_history[key].append(message)

        # Save to file
        try:
            os.makedirs('MessageHistory', exist_ok=True)
            with open(file_path, 'w') as file:
                json.dump(self.message_history[key], file, indent=4)
            return True
        except Exception as e:
            print(f"Error saving message: {e}")
            return False

    def add_friend(self, username):
        """Add a friend to the relations list"""
        if username not in self.friends:
            self.friends.append(username)
            self.save_relations()
            return True
        return False

    def add_group(self, name, group_id):
        """Add a group to the relations list"""
        if name not in self.groups:
            self.groups.append(name)
            self.save_relations()

            # Save group ID
            os.makedirs('UserData/Groups', exist_ok=True)
            with open(f'UserData/Groups/{name}.json', 'w') as file:
                json.dump({'id': group_id, 'members': []}, file)

            return True
        return False

    def get_group_id(self, name):
        """Get the ID of a group"""
        try:
            with open(f'UserData/Groups/{name}.json', 'r') as file:
                data = json.load(file)
                return data['id']
        except FileNotFoundError:
            return None

    def get_group_members(self, name):
        """Get the members of a group"""
        try:
            with open(f'UserData/Groups/{name}.json', 'r') as file:
                data = json.load(file)
                return data['members']
        except FileNotFoundError:
            return []

    def add_group_member(self, group_name, username):
        """Add a member to a group"""
        try:
            with open(f'UserData/Groups/{group_name}.json', 'r') as file:
                data = json.load(file)

            if username not in data['members']:
                data['members'].append(username)

                with open(f'UserData/Groups/{group_name}.json', 'w') as file:
                    json.dump(data, file)

                return True
            return False
        except FileNotFoundError:
            return False

    def save_relations(self):
        """Save the relations to file"""
        data = {}
        for friend in self.friends:
            data[f"f_{friend}"] = {}
        for group in self.groups:
            data[f"g_{group}"] = {}

        try:
            os.makedirs('UserData', exist_ok=True)
            with open('UserData/relations.json', 'w') as file:
                json.dump(data, file, indent=4)
            return True
        except Exception as e:
            print(f"Error saving relations: {e}")
            return False

    def prepare_backup_data(self):
        """Prepare data for backup to server"""
        backup_data = {
            'friends': self.friends,
            'groups': self.groups,
            'message_history': {},
            'timestamp': int(time.time())
        }

        # Encrypt message history for backup
        for key, messages in self.message_history.items():
            encrypted_messages = self.encryption_manager.encrypt_data_for_storage(messages)
            if encrypted_messages:
                backup_data['message_history'][key] = encrypted_messages

        return backup_data

    def restore_from_backup(self, backup_data):
        """Restore data from a server backup"""
        if not backup_data:
            return False

        try:
            # Restore friends and groups
            self.friends = backup_data.get('friends', [])
            self.groups = backup_data.get('groups', [])
            self.save_relations()

            # Restore message history
            for key, encrypted_messages in backup_data.get('message_history', {}).items():
                decrypted_messages = self.encryption_manager.decrypt_data_from_storage(encrypted_messages)
                if decrypted_messages:
                    messages = json.loads(decrypted_messages.decode('utf-8'))

                    # Save to memory
                    self.message_history[key] = messages

                    # Save to file
                    if key.startswith('group_'):
                        file_path = f'MessageHistory/{key}.json'
                    else:
                        file_path = f'MessageHistory/{key}.json'

                    os.makedirs('MessageHistory', exist_ok=True)
                    with open(file_path, 'w') as file:
                        json.dump(messages, file, indent=4)

            # Update sync time
            self.last_sync_time = backup_data.get('timestamp', int(time.time()))
            self.save_sync_time()

            return True
        except Exception as e:
            print(f"Error restoring from backup: {e}")
            return False


import json
import os
import time
from encryption import EncryptionManager


class DataManager:
    def __init__(self, encryption_manager):
        self.encryption_manager = encryption_manager
        self.message_history = {}
        self.friends = []
        self.groups = []
        self.last_sync_time = 0
        self.load_local_data()

    def load_local_data(self):
        """Load all local data including message history, friends, and groups"""
        self.load_relations()
        self.load_message_history()
        self.load_sync_time()

    def load_relations(self):
        """Load friends and groups from relations.json"""
        try:
            with open('UserData/relations.json', 'r') as file:
                data = json.load(file)
                self.friends = []
                self.groups = []
                for key in data.keys():
                    if key.startswith('f_'):
                        self.friends.append(key[2:])
                    elif key.startswith('g_'):
                        self.groups.append(key[2:])
        except FileNotFoundError:
            print("Relations file not found, creating empty lists")
        except json.JSONDecodeError:
            print("Error decoding relations file, creating empty lists")

    def load_message_history(self):
        """Load message history for all friends and groups"""
        self.message_history = {}

        # Load friend messages
        for friend in self.friends:
            file_path = f'MessageHistory/{friend}.json'
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r') as file:
                        messages = json.load(file)
                        self.message_history[friend] = messages
            except Exception as e:
                print(f"Error loading message history for {friend}: {e}")
                self.message_history[friend] = []

        # Load group messages
        for group in self.groups:
            file_path = f'MessageHistory/group_{group}.json'
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r') as file:
                        messages = json.load(file)
                        self.message_history[f"group_{group}"] = messages
            except Exception as e:
                print(f"Error loading message history for group {group}: {e}")
                self.message_history[f"group_{group}"] = []

    def load_sync_time(self):
        """Load the last sync time"""
        try:
            with open('UserData/last_sync.txt', 'r') as file:
                self.last_sync_time = int(file.read().strip())
        except FileNotFoundError:
            self.last_sync_time = 0
        except ValueError:
            print("Error parsing last sync time, using 0")
            self.last_sync_time = 0

    def save_sync_time(self):
        """Save the current sync time"""
        os.makedirs('UserData', exist_ok=True)
        with open('UserData/last_sync.txt', 'w') as file:
            file.write(str(int(time.time())))
        self.last_sync_time = int(time.time())

    def save_message(self, recipient, message, is_group=False):
        """Save a message to local storage"""
        if is_group:
            key = f"group_{recipient}"
            file_path = f'MessageHistory/group_{recipient}.json'
        else:
            key = recipient
            file_path = f'MessageHistory/{recipient}.json'

        # Ensure the message history for this recipient exists
        if key not in self.message_history:
            self.message_history[key] = []

        # Add the message to memory
        self.message_history[key].append(message)

        # Save to file
        try:
            os.makedirs('MessageHistory', exist_ok=True)
            with open(file_path, 'w') as file:
                json.dump(self.message_history[key], file, indent=4)
            return True
        except Exception as e:
            print(f"Error saving message: {e}")
            return False

    def add_friend(self, username):
        """Add a friend to the relations list"""
        if username not in self.friends:
            self.friends.append(username)
            self.save_relations()
            return True
        return False

    def add_group(self, group_name):
        """Add a group to the relations list"""
        if group_name not in self.groups:
            self.groups.append(group_name)
            self.save_relations()
            return True
        return False

    def save_relations(self):
        """Save the relations to file"""
        data = {}
        for friend in self.friends:
            data[f"f_{friend}"] = {}
        for group in self.groups:
            data[f"g_{group}"] = {}

        try:
            os.makedirs('UserData', exist_ok=True)
            with open('UserData/relations.json', 'w') as file:
                json.dump(data, file, indent=4)
            return True
        except Exception as e:
            print(f"Error saving relations: {e}")
            return False

    def prepare_backup_data(self):
        """Prepare data for backup to server"""
        backup_data = {
            'friends': self.friends,
            'groups': self.groups,
            'message_history': {},
            'timestamp': int(time.time())
        }

        # Encrypt message history for backup
        for key, messages in self.message_history.items():
            encrypted_messages = self.encryption_manager.encrypt_data_for_storage(messages)
            if encrypted_messages:
                backup_data['message_history'][key] = encrypted_messages

        return backup_data

    def restore_from_backup(self, backup_data):
        """Restore data from a server backup"""
        if not backup_data:
            return False

        try:
            # Restore friends and groups
            self.friends = backup_data.get('friends', [])
            self.groups = backup_data.get('groups', [])
            self.save_relations()

            # Restore message history
            for key, encrypted_messages in backup_data.get('message_history', {}).items():
                decrypted_messages = self.encryption_manager.decrypt_data_from_storage(encrypted_messages)
                if decrypted_messages:
                    messages = json.loads(decrypted_messages.decode('utf-8'))

                    # Save to memory
                    self.message_history[key] = messages

                    # Save to file
                    if key.startswith('group_'):
                        file_path = f'MessageHistory/{key}.json'
                    else:
                        file_path = f'MessageHistory/{key}.json'

                    os.makedirs('MessageHistory', exist_ok=True)
                    with open(file_path, 'w') as file:
                        json.dump(messages, file, indent=4)

            # Update sync time
            self.last_sync_time = backup_data.get('timestamp', int(time.time()))
            self.save_sync_time()

            return True
        except Exception as e:
            print(f"Error restoring from backup: {e}")
            return False

