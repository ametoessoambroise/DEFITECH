# 🎓 DEFITECH - Student Management Platform

A comprehensive education management system designed for DEFITECH university. This multi-role platform (Admin, Teacher, Student) integrates modern technologies to streamline academic management, real-time communication, and AI-assisted learning.

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8+
- PostgreSQL (Recommended) or MySQL 5.7+
- `pip` (Python package manager)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/ametoessoambroise/DEFITECH.git
cd DEFITECH

# Install dependencies
pip install -r requirements.txt

# Setup Database
python setup_database.py

# Launch the application
python app.py
```

Access the application at: `http://localhost:5000`

### 3. Default Credentials

- **Admin**: `admin@defitech.com` / `admin123`

---

## ✨ Key Features

### 🔐 Multi-Role Dashboards

- **Administrators**: Real-time stats, user validation, system notifications, and data exports.
- **Teachers**: Manage grades, track attendance, and manage course materials/assignments.
- **Students**: View grades, access personal schedules, and track upcoming deadlines.

### 🤖 DefAI - AI Assistant

An advanced AI assistant powered by Gemini, capable of:

- **Conversation History**: Real-time streaming and persistent history.
- **Multimodal Support**: Web search integration and image generation.
- **Smart Tools**: Accessing academic data via a secure internal request system.

### 📚 Specialized Tools

- **Study Planner**: AI-optimized study plans with Pomodoro session management.
- **Analytics Engine**: Interactive charts for academic performance and system usage.
- **Messaging**: Real-time Socket.IO chat between students/teachers and administration.
- **Notification Center**: Real-time alerts (email and internal) for critical events.

---

## 🛠️ Technical Stack

- **Backend**: Python (Flask)
- **Database**: PostgreSQL (SQLAlchemy ORM)
- **Real-time**: Socket.IO (WebSockets)
- **AI**: Google Gemini API
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **Security**: Flask-Login, HMAC Signatures (DefAI), CSRF Protection
- **Exports**: ReportLab (PDF), python-docx (Word), Pandas (Excel/CSV)

---

## 📁 Project Structure

```bash
DEFITECH/
├── app/
│   ├── models/          # Database schemas (SQLAlchemy)
│   ├── routes/          # Flask blueprints (Admin, Teacher, Student, AI)
│   ├── services/        # Business logic (AI, validation, upload)
│   ├── static/          # CSS (Tailwind), JS, and Assets
│   ├── templates/       # HTML Jinja2 Templates
│   └── docs/            # Detailed documentation archive
├── app.py               # Main entry point
├── requirements.txt     # Python dependencies
└── setup_database.py    # Database initialization script
```

---

## 🔧 Configuration & Security

### Environment Variables

Create a `.env` file based on your environment:

```env
SQLALCHEMY_DATABASE_URI=postgresql://user:password@localhost/defitech_db
SECRET_KEY=your_secret_key
DEFAI_SECRET_KEY=your_defai_hmac_key
GEMINI_API_KEY=your_api_key
CLOUDINARY_URL=your_cloudinary_url
```

### Advanced Systems

- **DefAI Middleware**: A secure internal request system (`defai_middleware.py`) allows the AI to query application data using restricted HMAC-signed requests.
- **Data Integrity**: V11 brought 13 critical field corrections across models to ensure 100% relational integrity.

---

## 🆘 Support & Maintenance

- **Logs**: Access security and access logs in `logs/` directory.
- **Migrations**: Use `flask db migrate` and `flask db upgrade` for schema changes.
- **Documentation**: For deep technical details, refer to the files in `app/docs/`.

---

**Developed with ❤️ for DEFITECH**
*Version: 2026.1 (Baseline v11)*
