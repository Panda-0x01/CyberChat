# 🔐 Secure Chat App

A Flask-based encrypted real-time chat application with strong security features including server-side encryption, secure authentication, and WebSocket-powered messaging.

---

## 📁 Project Structure

```
secure-chat-app/
├── app.py                 # Main Flask application
├── encrypted_database.py  # Handles encryption logic and secure DB operations
├── requirements.txt       # Python dependencies
├── master.key             # Auto-generated encryption key (KEEP SECRET)
├── chat_app.db            # SQLite database (auto-created)
├── static/
│   ├── style.css          # UI styling
│   ├── app.js             # Main frontend logic
│   └── crypto.js          # Client-side encryption (if applicable)
├── templates/
│   └── index.html         # HTML UI template
└── README.md              # Project documentation
```

---

## 🔐 Key Security Features

### ✅ Server-Side
- **Fernet Encryption** – AES-128 CBC mode + HMAC (via `cryptography`)
- **Hashed Passwords** – Secure user credentials with PBKDF2-SHA256 + unique salt
- **Encrypted Database** – All sensitive fields (messages, usernames, timestamps) encrypted before storage
- **Master Key** – Symmetric encryption key, auto-generated and used securely

### ✅ Client-Side
- **WebSocket Chat** – Real-time messaging via Flask-SocketIO
- **Login & Registration** – Simple and secure user management
- **Room Support** – Create or join encrypted chat rooms
- **Encrypted Message Persistence** – History stored encrypted and securely retrieved

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/secure-chat-app.git
cd secure-chat-app
```

### 2. Create a Virtual Environment

```bash
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

---

## ⚙️ Configuration

### Optional: `.env` File for Configuration

Create a `.env` file in the root:

```
SECRET_KEY=your-secret-key
FLASK_ENV=production
DATABASE_URL=sqlite:///chat_app.db
```

### Notes
- Never commit `master.key` to version control.
- Always change `SECRET_KEY` in production.
- Use HTTPS with a valid certificate in production deployments.

---

## 🧪 Testing

### ✅ Functional Testing
- Register & login with multiple accounts
- Create & join chat rooms
- Send and receive messages in real-time

### 🔐 Security Testing
- Inspect the database (all messages should be encrypted)
- Confirm password hashing and authentication behavior
- Validate protection against basic injection attacks

---

## 🧱 Built With

- [Flask](https://palletsprojects.com/p/flask/) – Lightweight Python web framework
- [Flask-SocketIO](https://flask-socketio.readthedocs.io/) – Real-time communication layer
- [cryptography](https://cryptography.io/en/latest/) – Industry-standard encryption tools
- SQLite – Simple embedded relational database

---

## 🧠 Advanced Features (Planned / Optional)

- ✅ End-to-end encryption with key exchange
- ✅ Forward secrecy with ephemeral keys
- ✅ Digital signatures for message verification
- ✅ Message pagination and search
- ✅ User blocking/muting
- ✅ Admin/moderation tools

---

## 🐞 Troubleshooting

| Issue | Solution |
|-------|----------|
| `Port 5000 in use` | Change port in `app.py` |
| `chat_app.db` errors | Delete it and restart the app |
| Encryption errors | Delete and regenerate `master.key` |
| WebSocket not connecting | Check firewall or browser console |

---

## 📌 Security Best Practices

- 🔐 Do **not** upload `master.key` to GitHub
- 🔄 Rotate keys periodically
- 📦 Use production-grade DB in deployment
- 🚧 Sanitize all user inputs
- 🔁 Implement rate-limiting & throttling

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome!

```bash
# Fork the repository
# Create a new branch
# Submit a pull request
```

---

## 📬 Contact

Feel free to [open an issue](https://github.com/yourusername/secure-chat-app/issues) or reach out via email for questions, feedback, or collaboration ideas.

---

**Built with ❤️ and secured with 🔐**
