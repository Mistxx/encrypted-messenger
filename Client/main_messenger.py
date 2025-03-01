import sys
import json
import os
import time
from PyQt6 import QtWidgets, QtCore, QtGui
from encryption import EncryptionManager
from server_api import ServerAPI
from data_manager import DataManager


def load_user_info(file_path='UserData/UserInfo.txt'):
    user_info = {}
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    user_info[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    return user_info


class MessengerWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureConnect Messenger")
        self.setWindowIcon(QtGui.QIcon('SecureConnect Logo.webp'))
        self.setGeometry(100, 100, 1000, 500)
        self.setFixedSize(1000, 500)

        # Initialize encryption, server API, and data manager
        self.encryption_manager = EncryptionManager()
        self.server_api = ServerAPI()
        self.data_manager = DataManager(self.encryption_manager)

        # Set up message polling timer
        self.message_poll_timer = QtCore.QTimer(self)
        self.message_poll_timer.timeout.connect(self.poll_for_messages)
        self.message_poll_timer.start(5000)  # Poll every 5 seconds

        # Set up backup timer
        self.backup_timer = QtCore.QTimer(self)
        self.backup_timer.timeout.connect(self.backup_user_data)
        self.backup_timer.start(300000)  # Backup every 5 minutes

        self.init_ui()
        self.current_chat = None
        self.ensure_message_files_exist()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        top_bar_layout = QtWidgets.QHBoxLayout()
        top_bar_layout.addStretch(1)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Search for users...")
        self.search_input.setStyleSheet("background-color: #40444B; color: white; padding: 5px; border-radius: 5px;")
        self.search_input.setFixedWidth(300)
        top_bar_layout.addWidget(self.search_input)

        self.search_button = QtWidgets.QPushButton("Search")
        self.search_button.setStyleSheet("background-color: #40444B; color: white; padding: 5px;")
        self.search_button.clicked.connect(self.search_users)
        top_bar_layout.addWidget(self.search_button)

        top_bar_layout.addStretch(1)

        user_data = load_user_info()
        self.username_label = QtWidgets.QLabel(user_data.get('Username', 'Unknown User'))
        self.username_label.setStyleSheet("font-size: 19px; color: white; padding: 10px;")
        top_bar_layout.addWidget(self.username_label)

        self.settings_button = QtWidgets.QPushButton("Settings")
        self.settings_button.setStyleSheet("background-color: #40444B; color: white; padding: 10px;")
        self.settings_button.clicked.connect(self.open_settings)
        top_bar_layout.addWidget(self.settings_button)

        main_layout.addLayout(top_bar_layout)

        main_content_layout = QtWidgets.QHBoxLayout()
        sidebar_layout = QtWidgets.QVBoxLayout()

        self.friend_list_label = QtWidgets.QLabel("Friends")
        self.friend_list_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        sidebar_layout.addWidget(self.friend_list_label)

        self.friend_list = QtWidgets.QListWidget()
        self.friend_list.itemClicked.connect(self.on_friend_selected)
        sidebar_layout.addWidget(self.friend_list)

        self.add_friend_button = QtWidgets.QPushButton("Add Friend")
        self.add_friend_button.setStyleSheet("background-color: #40444B; color: white; padding: 5px;")
        self.add_friend_button.clicked.connect(self.show_add_friend_dialog)
        sidebar_layout.addWidget(self.add_friend_button)

        self.group_list_label = QtWidgets.QLabel("Groups")
        self.group_list_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        sidebar_layout.addWidget(self.group_list_label)

        self.group_list = QtWidgets.QListWidget()
        self.group_list.itemClicked.connect(self.on_group_selected)
        sidebar_layout.addWidget(self.group_list)

        self.create_group_button = QtWidgets.QPushButton("Create Group")
        self.create_group_button.setStyleSheet("background-color: #40444B; color: white; padding: 5px;")
        self.create_group_button.clicked.connect(self.show_create_group_dialog)
        sidebar_layout.addWidget(self.create_group_button)

        main_content_layout.addLayout(sidebar_layout, 1)

        self.chat_area = QtWidgets.QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setStyleSheet("background-color: #2C2F38; color: white; padding: 10px;")
        main_content_layout.addWidget(self.chat_area, 3)

        main_layout.addLayout(main_content_layout)

        self.message_input_layout = QtWidgets.QHBoxLayout()

        self.message_input = QtWidgets.QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")
        self.message_input.setStyleSheet("background-color: #40444B; color: white; padding: 10px; border-radius: 5px;")
        self.message_input.returnPressed.connect(self.send_message)
        self.message_input_layout.addWidget(self.message_input)

        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.setStyleSheet("background-color: #40444B; color: white; padding: 10px;")
        self.send_button.clicked.connect(self.send_message)
        self.message_input_layout.addWidget(self.send_button)

        main_layout.addLayout(self.message_input_layout)
        main_layout.addStretch(1)

        self.load_relations()
        self.check_server_connection()

    def check_server_connection(self):
        """Check if we're connected to the server and try to restore data if needed"""
        if self.server_api.auth_token:
            # We have a token, try to restore data if it's our first launch
            if self.data_manager.last_sync_time == 0:
                success, message, data = self.server_api.restore_user_data()
                if success and data:
                    self.data_manager.restore_from_backup(data)
                    self.show_notification("Data restored from server")
                    self.load_relations()
        else:
            # Not logged in, show login dialog
            self.show_login_dialog()

    def load_relations(self):
        """Load friends and groups from the data manager"""
        self.friend_list.clear()
        self.group_list.clear()
        self.friend_list.addItems(self.data_manager.friends)
        self.group_list.addItems(self.data_manager.groups)

    def ensure_message_files_exist(self):
        """Ensure message history files exist for all friends and groups"""
        os.makedirs('MessageHistory', exist_ok=True)
        for friend in self.data_manager.friends:
            file_path = f'MessageHistory/{friend}.json'
            if not os.path.exists(file_path):
                with open(file_path, 'w') as file:
                    json.dump([], file)

        for group in self.data_manager.groups:
            file_path = f'MessageHistory/group_{group}.json'
            if not os.path.exists(file_path):
                with open(file_path, 'w') as file:
                    json.dump([], file)

    def on_friend_selected(self, item):
        """Handle friend selection from the list"""
        selected_friend = item.text()
        self.current_chat = selected_friend
        self.chat_area.clear()

        # Load messages from data manager
        if selected_friend in self.data_manager.message_history:
            messages = self.data_manager.message_history[selected_friend]
            for message in messages:
                self.chat_area.append(message)
        else:
            self.data_manager.message_history[selected_friend] = []

    def on_group_selected(self, item):
        """Handle group selection from the list"""
        selected_group = item.text()
        self.current_chat = f"group_{selected_group}"
        self.chat_area.clear()

        # Load messages from data manager
        if f"group_{selected_group}" in self.data_manager.message_history:
            messages = self.data_manager.message_history[f"group_{selected_group}"]
            for message in messages:
                self.chat_area.append(message)
        else:
            self.data_manager.message_history[f"group_{selected_group}"] = []

    def send_message(self):
        """Send a message to the current chat"""
        message = self.message_input.text()
        if not message or not self.current_chat:
            return

        is_group = self.current_chat.startswith("group_")
        recipient = self.current_chat[6:] if is_group else self.current_chat

        # Format the message for display
        formatted_message = f"You: {message}"

        if is_group:
            # Group message handling
            group_id = self.data_manager.get_group_id(recipient)
            if not group_id:
                self.show_notification("Error: Group not found")
                return

            # Encrypt the message for each group member
            encrypted_messages = {}
            for member in self.data_manager.get_group_members(recipient):
                encrypted_message = self.encryption_manager.encrypt_message(message, member)
                if encrypted_message:
                    encrypted_messages[member] = encrypted_message
                else:
                    self.show_notification(f"Failed to encrypt message for {member}")
                    return

            # Send the encrypted messages to the server
            success, result = self.server_api.send_group_message(group_id, encrypted_messages)
            if success:
                self.data_manager.save_message(recipient, formatted_message, is_group=True)
                self.chat_area.append(formatted_message)
            else:
                self.show_notification(f"Failed to send group message: {result}")
        else:
            # Direct message handling
            encrypted_message = self.encryption_manager.encrypt_message(message, recipient)

            if encrypted_message:
                # Save locally first
                self.data_manager.save_message(recipient, formatted_message)
                self.chat_area.append(formatted_message)

                # Send to server
                success, result = self.server_api.send_message(recipient, encrypted_message)
                if not success:
                    self.show_notification(f"Failed to send message: {result}")
            else:
                self.show_notification("Failed to encrypt message. Make sure you have the recipient's public key.")

        self.message_input.clear()

    def poll_for_messages(self):
        """Poll the server for new messages"""
        if not self.server_api.auth_token:
            return

        # Poll for direct messages
        success, message, messages = self.server_api.get_messages(self.data_manager.last_sync_time)

        if success and messages:
            for msg in messages:
                sender = msg.get('sender')
                encrypted_key = msg.get('encrypted_key')
                encrypted_content = msg.get('encrypted_content')

                # Decrypt the message
                encrypted_data = {
                    'key': encrypted_key,
                    'message': encrypted_content
                }

                decrypted_message = self.encryption_manager.decrypt_message(encrypted_data)

                if decrypted_message:
                    formatted_message = f"{sender}: {decrypted_message}"

                    # Save to data manager
                    self.data_manager.save_message(sender, formatted_message)

                    # If this is the current chat, update the display
                    if self.current_chat == sender:
                        self.chat_area.append(formatted_message)

                    # Show notification for new message
                    if self.current_chat != sender:
                        self.show_notification(f"New message from {sender}")

        # Poll for group messages
        success, message, group_messages = self.server_api.get_group_messages(self.data_manager.last_sync_time)

        if success and group_messages:
            for msg in group_messages:
                sender = msg.get('sender')
                group_id = msg.get('group_id')
                group_name = msg.get('group_name')
                encrypted_key = msg.get('encrypted_key')
                encrypted_content = msg.get('encrypted_content')

                # Decrypt the message
                encrypted_data = {
                    'key': encrypted_key,
                    'message': encrypted_content
                }

                decrypted_message = self.encryption_manager.decrypt_message(encrypted_data)

                if decrypted_message:
                    formatted_message = f"{sender} (in {group_name}): {decrypted_message}"

                    # Save to data manager
                    self.data_manager.save_message(group_name, formatted_message, is_group=True)

                    # If this is the current chat, update the display
                    if self.current_chat == f"group_{group_name}":
                        self.chat_area.append(formatted_message)

                    # Show notification for new message
                    if self.current_chat != f"group_{group_name}":
                        self.show_notification(f"New message in group {group_name}")

    def backup_user_data(self):
        """Backup user data to the server"""
        if not self.server_api.auth_token:
            return

        backup_data = self.data_manager.prepare_backup_data()
        success, message = self.server_api.backup_user_data(backup_data)

        if success:
            self.data_manager.save_sync_time()
            print("Data backed up successfully")
        else:
            print(f"Backup failed: {message}")

    def search_users(self):
        """Search for users on the server"""
        search_term = self.search_input.text()
        if not search_term:
            return

        success, message, users = self.server_api.search_users(search_term)

        if success:
            self.show_search_results(users)
        else:
            self.show_notification(f"Failed to search users: {message}")

    def show_search_results(self, users):
        """Show search results in a dialog"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Search Results")
        dialog.setFixedSize(300, 400)

        layout = QtWidgets.QVBoxLayout(dialog)

        results_list = QtWidgets.QListWidget()
        for user in users:
            results_list.addItem(user['username'])

        layout.addWidget(results_list)

        add_friend_button = QtWidgets.QPushButton("Add Friend")
        add_friend_button.clicked.connect(lambda: self.add_friend(results_list.currentItem().text(), dialog))
        layout.addWidget(add_friend_button)

        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.exec()

    def show_add_friend_dialog(self):
        """Show dialog to add a new friend"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Add Friend")
        dialog.setFixedSize(300, 150)

        layout = QtWidgets.QVBoxLayout(dialog)

        username_label = QtWidgets.QLabel("Username:")
        layout.addWidget(username_label)

        username_input = QtWidgets.QLineEdit()
        layout.addWidget(username_input)

        button_layout = QtWidgets.QHBoxLayout()
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        add_button = QtWidgets.QPushButton("Add")
        add_button.clicked.connect(lambda: self.add_friend(username_input.text(), dialog))
        button_layout.addWidget(add_button)

        layout.addLayout(button_layout)

        dialog.exec()

    def add_friend(self, username, dialog):
        """Add a friend and get their public key"""
        if not username:
            return

        # Get the user's public key from the server
        success, message, public_key_pem = self.server_api.get_friend_public_key(username)

        if success and public_key_pem:
            # Save the public key
            self.encryption_manager.save_friend_public_key(username, public_key_pem)

            # Add to friends list
            self.data_manager.add_friend(username)
            self.friend_list.addItem(username)

            # Send friend request
            self.server_api.add_friend(username)

            dialog.accept()
            self.show_notification(f"Added {username} to friends")
        else:
            self.show_notification(f"Failed to add friend: {message}")

    def show_create_group_dialog(self):
        """Show dialog to create a new group"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Create Group")
        dialog.setFixedSize(300, 200)

        layout = QtWidgets.QVBoxLayout(dialog)

        name_label = QtWidgets.QLabel("Group Name:")
        layout.addWidget(name_label)

        name_input = QtWidgets.QLineEdit()
        layout.addWidget(name_input)

        members_label = QtWidgets.QLabel("Members (comma separated):")
        layout.addWidget(members_label)

        members_input = QtWidgets.QLineEdit()
        layout.addWidget(members_input)

        button_layout = QtWidgets.QHBoxLayout()
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        create_button = QtWidgets.QPushButton("Create")
        create_button.clicked.connect(lambda: self.create_group(name_input.text(), members_input.text(), dialog))
        button_layout.addWidget(create_button)

        layout.addLayout(button_layout)

        dialog.exec()

    def create_group(self, name, members_text, dialog):
        """Create a new group chat"""
        if not name:
            return

        members = [member.strip() for member in members_text.split(',') if member.strip()]

        success, result = self.server_api.create_group(name, members)

        if success:
            group_id = result
            self.data_manager.add_group(name, group_id)
            self.group_list.addItem(name)
            dialog.accept()
            self.show_notification(f"Created group {name}")
        else:
            self.show_notification(f"Failed to create group: {result}")

    def show_login_dialog(self):
        """Show login dialog"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Login")
        dialog.setFixedSize(300, 200)

        layout = QtWidgets.QVBoxLayout(dialog)

        username_label = QtWidgets.QLabel("Username:")
        layout.addWidget(username_label)

        username_input = QtWidgets.QLineEdit()
        layout.addWidget(username_input)

        password_label = QtWidgets.QLabel("Password:")
        layout.addWidget(password_label)

        password_input = QtWidgets.QLineEdit()
        password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        layout.addWidget(password_input)

        button_layout = QtWidgets.QHBoxLayout()
        register_button = QtWidgets.QPushButton("Register")
        register_button.clicked.connect(lambda: self.show_register_dialog(dialog))
        button_layout.addWidget(register_button)

        login_button = QtWidgets.QPushButton("Login")
        login_button.clicked.connect(lambda: self.login(username_input.text(), password_input.text(), dialog))
        button_layout.addWidget(login_button)

        layout.addLayout(button_layout)

        dialog.exec()

    def login(self, username, password, dialog):
        """Login to the server"""
        if not username or not password:
            return

        success, message = self.server_api.login(username, password)

        if success:
            dialog.accept()
            self.show_notification("Login successful")

            # Update user info
            os.makedirs('UserData', exist_ok=True)
            with open('UserData/UserInfo.txt', 'w') as file:
                file.write(f"Username={username}\n")

            self.username_label.setText(username)

            # Restore data from server
            success, message, data = self.server_api.restore_user_data()
            if success and data:
                self.data_manager.restore_from_backup(data)
                self.load_relations()
        else:
            self.show_notification(f"Login failed: {message}")

    def show_register_dialog(self, login_dialog=None):
        """Show registration dialog"""
        if login_dialog:
            login_dialog.close()

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Register")
        dialog.setFixedSize(300, 250)

        layout = QtWidgets.QVBoxLayout(dialog)

        username_label = QtWidgets.QLabel("Username:")
        layout.addWidget(username_label)

        username_input = QtWidgets.QLineEdit()
        layout.addWidget(username_input)

        email_label = QtWidgets.QLabel("Email:")
        layout.addWidget(email_label)

        email_input = QtWidgets.QLineEdit()
        layout.addWidget(email_input)

        password_label = QtWidgets.QLabel("Password:")
        layout.addWidget(password_label)

        password_input = QtWidgets.QLineEdit()
        password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        layout.addWidget(password_input)

        confirm_label = QtWidgets.QLabel("Confirm Password:")
        layout.addWidget(confirm_label)

        confirm_input = QtWidgets.QLineEdit()
        confirm_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        layout.addWidget(confirm_input)

        button_layout = QtWidgets.QHBoxLayout()
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        register_button = QtWidgets.QPushButton("Register")
        register_button.clicked.connect(lambda: self.register(
            username_input.text(),
            email_input.text(),
            password_input.text(),
            confirm_input.text(),
            dialog
        ))
        button_layout.addWidget(register_button)

        layout.addLayout(button_layout)

        dialog.exec()

    def register(self, username, email, password, confirm_password, dialog):
        """Register a new user"""
        if not username or not email or not password:
            self.show_notification("All fields are required")
            return

        if password != confirm_password:
            self.show_notification("Passwords do not match")
            return

        # Get public key in PEM format
        public_key_pem = self.encryption_manager.get_public_key_pem()

        success, message = self.server_api.register(username, password, email, public_key_pem)

        if success:
            dialog.accept()
            self.show_notification("Registration successful")

            # Update user info
            os.makedirs('UserData', exist_ok=True)
            with open('UserData/UserInfo.txt', 'w') as file:
                file.write(f"Username={username}\n")
                file.write(f"Email={email}\n")

            self.username_label.setText(username)
        else:
            self.show_notification(f"Registration failed: {message}")

    def open_settings(self):
        """Open settings dialog"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setFixedSize(400, 300)

        layout = QtWidgets.QVBoxLayout(dialog)

        # ServerSide settings
        server_group = QtWidgets.QGroupBox("ServerSide Settings")
        server_layout = QtWidgets.QFormLayout()

        server_url_input = QtWidgets.QLineEdit(self.server_api.base_url)
        server_layout.addRow("ServerSide URL:", server_url_input)

        backup_interval_input = QtWidgets.QSpinBox()
        backup_interval_input.setMinimum(1)
        backup_interval_input.setMaximum(60)
        backup_interval_input.setValue(5)  # Default 5 minutes
        server_layout.addRow("Backup Interval (minutes):", backup_interval_input)

        server_group.setLayout(server_layout)
        layout.addWidget(server_group)

        # Security settings
        security_group = QtWidgets.QGroupBox("Security")
        security_layout = QtWidgets.QFormLayout()

        regenerate_keys_button = QtWidgets.QPushButton("Regenerate Encryption Keys")
        regenerate_keys_button.clicked.connect(self.regenerate_keys)
        security_layout.addRow("", regenerate_keys_button)

        export_keys_button = QtWidgets.QPushButton("Export Public Key")
        export_keys_button.clicked.connect(self.export_public_key)
        security_layout.addRow("", export_keys_button)

        security_group.setLayout(security_layout)
        layout.addWidget(security_group)

        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        save_button = QtWidgets.QPushButton("Save")
        save_button.clicked.connect(lambda: self.save_settings(
            server_url_input.text(),
            backup_interval_input.value(),
            dialog
        ))
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

        dialog.exec()

    def save_settings(self, server_url, backup_interval, dialog):
        """Save settings"""
        # Update server URL
        self.server_api.base_url = server_url

        # Update backup interval
        self.backup_timer.stop()
        self.backup_timer.start(backup_interval * 60 * 1000)

        dialog.accept()
        self.show_notification("Settings saved")

    def regenerate_keys(self):
        """Regenerate encryption keys"""
        # This is a placeholder - in a real app, you'd want to confirm this action
        # and handle the key rotation carefully
        self.show_notification("Key regeneration not implemented in this demo")

    def export_public_key(self):
        """Export the user's public key"""
        public_key_pem = self.encryption_manager.get_public_key_pem()

        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Public Key", "", "PEM Files (*.pem);;All Files (*)"
        )

        if file_path:
            with open(file_path, 'wb') as file:
                file.write(public_key_pem)
            self.show_notification(f"Public key exported to {file_path}")

    def show_notification(self, message):
        """Show a notification message"""
        notification = QtWidgets.QMessageBox()
        notification.setWindowTitle("Notification")
        notification.setText(message)
        notification.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        notification.exec()

    def closeEvent(self, event):
        """Handle application close event"""
        # Backup data before closing
        self.backup_user_data()
        event.accept()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    # Set application style
    app.setStyle("Fusion")

    # Set dark theme palette
    dark_palette = QtGui.QPalette()
    dark_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(255, 255, 255))
    dark_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(25, 25, 25))
    dark_palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor(255, 255, 255))
    dark_palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor(255, 255, 255))
    dark_palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(255, 255, 255))
    dark_palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor(255, 255, 255))
    dark_palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor(255, 0, 0))
    dark_palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(0, 0, 0))
    app.setPalette(dark_palette)

    window = MessengerWindow()
    window.show()
    sys.exit(app.exec())

