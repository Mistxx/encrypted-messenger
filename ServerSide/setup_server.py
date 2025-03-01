import os
import sys
import subprocess
import platform


def check_python_version():
    """Check if Python version is 3.7 or higher"""
    if sys.version_info < (3, 7):
        print("Error: Python 3.7 or higher is required")
        sys.exit(1)


def install_requirements():
    """Install required packages"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("Error: Failed to install dependencies")
        sys.exit(1)


def create_data_directory():
    """Create data directory if it doesn't exist"""
    os.makedirs("data", exist_ok=True)
    print("✓ Data directory created")


def main():
    """Main setup function"""
    print("Setting up SecureConnect ServerSide...")

    # Check Python version
    check_python_version()
    print("✓ Python version check passed")

    # Install requirements
    install_requirements()

    # Create data directory
    create_data_directory()

    print("\nSetup complete! You can now run the server with:")
    if platform.system() == "Windows":
        print("python run_server.py")
    else:
        print("python3 run_server.py")


if __name__ == "__main__":
    main()
