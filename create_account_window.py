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
        encrypted_data = base64.b64encode(cipher.iv + encrypted).decode()  # Combine IV and encrypted data, then encode to base64
        return encrypted_data
    except Exception as e:
        print(f"Error during encryption: {e}")
        return None

class CreateAccountWindow(QtWidgets.QWidget):
    account_created = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Create Account")
        self.setWindowIcon(QtGui.QIcon('SecureConnect Logo.webp'))  # Set the window icon
        self.setGeometry(100, 100, 300, 200)
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # Input fields
        self.first_name_input = QtWidgets.QLineEdit()
        self.first_name_input.setPlaceholderText("First Name")
        layout.addWidget(self.first_name_input)

        self.last_name_input = QtWidgets.QLineEdit()
        self.last_name_input.setPlaceholderText("Last Name")
        layout.addWidget(self.last_name_input)

        self.grade_input = QtWidgets.QComboBox()
        self.grade_input.addItems(["Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"])
        layout.addWidget(self.grade_input)

        self.username_input = QtWidgets.QLineEdit()
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)

        self.password_input = QtWidgets.QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        self.verify_password_input = QtWidgets.QLineEdit()
        self.verify_password_input.setPlaceholderText("Verify Password")
        self.verify_password_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        layout.addWidget(self.verify_password_input)

        # Submit button
        create_account_button = QtWidgets.QPushButton("Create Account")
        create_account_button.clicked.connect(self.handle_create_account)
        layout.addWidget(create_account_button)

    def handle_create_account(self):
        username = self.username_input.text()
        password = self.password_input.text()
        passverify = self.verify_password_input.text()
        fname = self.first_name_input.text()
        lname = self.last_name_input.text()
        grade = self.grade_input.currentText()  # Get selected grade

        # Check all entered data
        if not username or not password or not passverify or not fname or not lname or not grade:
            QtWidgets.QMessageBox.warning(self, "Error", "Please fill in all the fields.")
        else:
            if password != passverify:
                QtWidgets.QMessageBox.warning(self, "Error", "The passwords do not match. Please try again.")
            else:
                # Define a 128-bit AES key (16 bytes) as a string
                key = 'F4AFE9B89DD4FF1B7D5ECFBF4B625' #placeholder  # 128-bit key

                # Encrypt each piece of data
                encrypted_username = encrypt_data(username, key)
                encrypted_password = encrypt_data(password, key)
                encrypted_fname = encrypt_data(fname, key)
                encrypted_lname = encrypt_data(lname, key)

                # Check if encryption failed for any field
                if None in [encrypted_username, encrypted_password, encrypted_fname, encrypted_lname]:
                    QtWidgets.QMessageBox.warning(self, "Error", "Encryption failed for one or more fields.")
                else:
                    # Join the encrypted data with dashes
                    encrypted_data = f"{encrypted_username}-{encrypted_password}-{encrypted_fname}-{encrypted_lname}-{grade}"
                    print(f"Encrypted data: {encrypted_data}")
                    self.account_created.emit()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = CreateAccountWindow()
    window.show()
    sys.exit(app.exec())
