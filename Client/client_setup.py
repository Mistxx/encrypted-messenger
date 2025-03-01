import os
import sys
import subprocess


def create_directories():
    directories = ['UserData', 'UserData/Keys', 'UserData/Keys/friends', 'MessageHistory']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    print("Directories created successfully.")


def install_requirements():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Requirements installed successfully.")
    except subprocess.CalledProcessError:
        print("Error: Failed to install requirements.")
        sys.exit(1)


def create_config():
    config_content = """# Client Configuration

SERVER_URL = "http://localhost:8000/api/"

# You can add more configuration options here as needed
"""
    with open('client_config.py', 'w') as f:
        f.write(config_content)
    print("Client configuration file created.")


def main():
    print("Setting up SecureConnect Messenger Client...")

    # Create necessary directories
    create_directories()

    # Install requirements
    install_requirements()

    # Create configuration file
    create_config()

    print("\nSetup complete! You can now run the client using:")
    print("python main_messenger.py")


if __name__ == "__main__":
    main()

