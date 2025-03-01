import sys
import json
import os
from PyQt6 import QtWidgets, QtCore, QtGui


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


def load_relations(file_path='UserData/relations.json'):
    relations = {'friends': [], 'groups': []}
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            for key in data.keys():
                if key.startswith('f_'):
                    relations['friends'].append(key[2:])
                elif key.startswith('g_'):
                    relations['groups'].append(key[2:])
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' is not a valid JSON file.")
    return relations


class MessengerWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureConnect Messenger")
        self.setWindowIcon(QtGui.QIcon('SecureConnect Logo.webp'))  # Set the window icon
        self.setGeometry(100, 100, 1000, 500)
        self.setFixedSize(1000, 500)  # Lock the window size
        self.init_ui()
        self.chat_history = {}
        self.ensure_message_files_exist()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        top_bar_layout = QtWidgets.QHBoxLayout()
        top_bar_layout.addStretch(1)


        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Search for users...")
        self.search_input.setStyleSheet("background-color: #40444B; color: white; padding: 5px; border-radius: 5px;")
        self.search_input.setFixedWidth(300)  # Set the width of the search bar
        top_bar_layout.addWidget(self.search_input)

        top_bar_layout.addStretch(1)

        user_data = load_user_info()
        self.username_label = QtWidgets.QLabel(user_data.get('Username', 'Unknown User'))
        self.username_label.setStyleSheet("font-size: 19px; color: white; padding: 10px;")
        top_bar_layout.addWidget(self.username_label)

        self.settings_button = QtWidgets.QPushButton("Settings")
        self.settings_button.setStyleSheet("background-color: #40444B; color: white; padding: 10px;")
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

        self.group_list_label = QtWidgets.QLabel("Groups")
        self.group_list_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        sidebar_layout.addWidget(self.group_list_label)

        self.group_list = QtWidgets.QListWidget()
        sidebar_layout.addWidget(self.group_list)

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
        self.message_input_layout.addWidget(self.message_input)

        self.send_button = QtWidgets.QPushButton("Send")
        self.send_button.setStyleSheet("background-color: #40444B; color: white; padding: 10px;")
        self.send_button.clicked.connect(self.send_message)
        self.message_input_layout.addWidget(self.send_button)

        main_layout.addLayout(self.message_input_layout)
        main_layout.addStretch(1)

        self.load_relations()

    def load_relations(self):
        relations = load_relations()
        self.friend_list.clear()
        self.group_list.clear()
        self.friend_list.addItems(relations['friends'])
        self.group_list.addItems(relations['groups'])

    def ensure_message_files_exist(self):
        os.makedirs('MessageHistory', exist_ok=True)
        for friend in load_relations()['friends']:
            file_path = f'MessageHistory/{friend}.json'
            if not os.path.exists(file_path):
                with open(file_path, 'w') as file:
                    json.dump([], file)

    def on_friend_selected(self, item):
        selected_friend = item.text()
        self.chat_area.clear()
        file_path = f'MessageHistory/{selected_friend}.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                messages = json.load(file)
                for message in messages:
                    self.chat_area.append(message)

    def send_message(self):
        message = self.message_input.text()
        if message:
            selected_friend = self.friend_list.currentItem().text()
            self.chat_area.append(f"You: {message}")
            self.save_message(selected_friend, f"You: {message}")
            self.message_input.clear()

    def save_message(self, friend, message):
        file_path = f'MessageHistory/{friend}.json'
        try:
            with open(file_path, 'r') as file:
                messages = json.load(file)
            messages.append(message)
            with open(file_path, 'w') as file:
                json.dump(messages, file, indent=4)
        except Exception as e:
            print(f"Error saving message: {e}")

    def show_notification(self, message):
        notification = QtWidgets.QMessageBox()
        notification.setWindowTitle("Notification")
        notification.setText(message)
        notification.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        notification.exec()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MessengerWindow()
    window.show()
    sys.exit(app.exec())
