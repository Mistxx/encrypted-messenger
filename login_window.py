import sys
from PyQt6 import QtWidgets, QtCore, QtGui
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64


# Encryption function
def encrypt_data(data, key):
    try:
        # Ensure the key is 16 bytes long
        key = key[:16].encode('utf-8')  # Trim or pad the key to 16 bytes if necessary
        # Ensure that data is in bytes if it's not already
        if isinstance(data, str):
            data = data.encode('utf-8')  # Encode if it's a string
        cipher = AES.new(key, AES.MODE_CBC)  # AES with CBC mode
        padded_data = pad(data, AES.block_size)  # Padding to match block size
        encrypted = cipher.encrypt(padded_data)
        encrypted_data = base64.b64encode(
            cipher.iv + encrypted).decode()  # Combine IV and encrypted data, then encode to base64
        return encrypted_data
    except Exception as e:
        print(f"Error during encryption: {e}")
        return None


class LoginWindow(QtWidgets.QWidget):
    login_success = QtCore.pyqtSignal(str)
    create_account_requested = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Secure Login")
        self.setWindowIcon(QtGui.QIcon('SecureConnect Logo.webp'))  # Set the window icon
        self.setGeometry(100, 100, 300, 200)
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Username input
        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setStyleSheet(
            "background-color: #40444B; border-radius: 5px; padding: 10px; color: #FFFFFF;")
        layout.addWidget(self.username_input)

        # Password input
        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(
            "background-color: #40444B; border-radius: 5px; padding: 10px; color: #FFFFFF;")
        layout.addWidget(self.password_input)

        # Login and Create Account buttons
        button_container = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout(button_container)
        button_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        login_button = QtWidgets.QPushButton("Login")
        login_button.setStyleSheet("background-color: #7289DA; border-radius: 5px; padding: 10px; color: #FFFFFF;")
        login_button.clicked.connect(self.handle_login)
        button_layout.addWidget(login_button)

        create_account_button = QtWidgets.QPushButton("Create Account")
        create_account_button.setStyleSheet(
            "background-color: #99AAB5; border-radius: 5px; padding: 10px; color: #FFFFFF;")
        create_account_button.clicked.connect(self.create_account_requested.emit)
        button_layout.addWidget(create_account_button)

        layout.addWidget(button_container)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        # Define the AES key for encryption (same as account creation)
        key = 'F4AFE9B89DD4FF1B7D5ECFBF4B625' #placeholder  # 128-bit key

        if username and password:  # Basic validation
            # Encrypt the entered username and password
            encrypted_username = encrypt_data(username, key)
            encrypted_password = encrypt_data(password, key)

            if None in [encrypted_username, encrypted_password]:
                QtWidgets.QMessageBox.warning(self, "Error", "Encryption failed. Please try again.")
            else:
                self.login_success.emit(username)
                print(f"Encrypted Username: {encrypted_username}")
                print(f"Encrypted Password: {encrypted_password}")

        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Please fill in both username and password.")


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())
