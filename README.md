This is a self-hosted, Python-based messaging application that prioritizes security and privacy. The software features a Discord-like interface with direct messaging and group chat functionality, built using PyQt6 for a smooth and modern user experience.

🔒 Security & Encryption
-128-bit Encryption: All messages are encrypted using a 128-bit encryption key, ensuring data confidentiality during transmission.
-Server-Side Storage: User information and message history are securely stored on the server, minimizing the risk of data leaks on the client side.
-Cloud Key Storage: Keys are stored on the serverside for enhanced security.

🚀 Features
-Direct Messaging & Group Chats: Connect with friends and create group conversations seamlessly.
-Modern UI: Inspired by Discord, the interface is intuitive and easy to navigate.
-Cross-Platform Support: The application can run on any system with Python and PyQt6 installed.

⚙️ Setup
1. On the server side, ensure the latest version of Python (3.13 at release) is installed.
2. On server side, run "setup_server.py", followed by "run_server.py" when instructed.
3. Get your server side ipv4 address (type "ipconfig" in command prompt).
4. On client side, open/edit "client_config.py" and change the url to "http://(server ipv4 from step 3):8000/api".
5. On client side, run "main_messenger.py" to verify that everything is set up correctly.
6. If you want to use the application outside the house and let your friends use it, you must use a port forwarding method. Look up a tutorial for your specific router, and make sure to set a static ip address for your server side computer to avoid future complications.
7. On client side device, delete "ServerSide" file and compile the project using PyInstaller for easy sharing.

---
Please keep in mind this is a work in progress/proof of concept application, and is not optimised or seamless.
📄 **License:** This project is licensed under the [Apache License 2.0](LICENSE).  
🛠️ **Attribution:** If you use or modify this software, please provide proper credit to the original author: Mistxx or Nexencrypt Technologies.  
