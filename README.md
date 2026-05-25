# RC Bandito 🚗

A secure, camera-equipped RC car controlled over a local network — built to demonstrate practical IoT security hardening.

## Team
- Jorge Icabalceta Aust (100247561)
- Alvin Tay (100408097)
- Nihkil Sood (100409908)
- Rayzel Liang

---

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python Flask |
| Database | MySQL |
| Hardware | Raspberry Pi + Camera Module |
| Security | TLS/HTTPS, RBAC, Rate Limiting, AES logging |

---

## Project Structure
```
rc-bandito/
├── backend/
│   ├── app.py              # Flask app factory
│   ├── requirements.txt
│   ├── models/
│   │   └── models.py       # User, AuditLog DB models
│   └── routes/
│       ├── auth.py         # Login / logout / lockout
│       ├── control.py      # Command validation + rate limiting
│       ├── admin.py        # Admin: users, logs, roles
│       └── stream.py       # MJPEG live video stream
├── frontend/
│   ├── templates/
│   └── static/
│       ├── css/
│       └── js/
└── docs/
```

---

## Setup

### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment
Create a `.env` file in `/backend`:
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=mysql+pymysql://root:password@localhost/rc_bandito
```

### 3. Initialize database
```bash
flask shell
>>> from app import db, create_app
>>> app = create_app()
>>> with app.app_context(): db.create_all()
```

### 4. Run the server
```bash
python app.py
```

---

## Security Features
- **Authentication**: Login with account lockout after 5 failed attempts
- **RBAC**: Admin vs Operator roles with enforced route permissions
- **Command Validation**: Only whitelisted commands (`forward`, `backward`, `left`, `right`, `stop`) accepted
- **Rate Limiting**: Max 30 commands/minute per user
- **Watchdog**: Auto-stops car after 3 seconds with no command
- **Audit Logging**: All logins, commands, and admin actions logged to DB
- **TLS**: Run behind HTTPS in production
