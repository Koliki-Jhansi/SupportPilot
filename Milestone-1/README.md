# SupportPilot — Milestone 1: Core Ticket Management & Classification

SupportPilot is an AI-powered IT Support Ticket Management and Classification platform. Milestone 1 establishes the foundational infrastructure, user authentication, ticket intake, automated classification, severity/priority assignment, SQLite persistence, and interactive dashboard analytics.

---

## 🚀 Key Features

1. **User Authentication & Authorization**:
   - Secure registration and login flows.
   - Role-based session management and JWT authentication.

2. **Ticket Intake & Lifecycle Management**:
   - Web-based ticket submission with title, description, category, and priority inputs.
   - Comprehensive status tracking: `Open`, `In Progress`, `Resolved`, `Closed`.

3. **Intelligent Ticket Classification**:
   - Machine learning classifier (`classifier.py`, `train_model.py`) for automatic category categorization (`Hardware`, `Software`, `Network / VPN`, `Access / Identity`, `Security`).
   - Confidence scoring on predictions.

4. **Severity & Priority Rule Engine**:
   - Rule-based evaluation (`priority.py`, `severity.py`) mapping business impact and urgency into standardized levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).

5. **Operational Dashboard & Visual Analytics**:
   - Real-time ticket statistics.
   - Category distribution, priority breakdown, and severity charts using Chart.js.

6. **Database Persistence**:
   - SQLite relational schema (`database.py`) storing users, tickets, and operational metrics.

---

## 📁 Main Files & Structure

```text
Milestone-1/
├── app.py                     # Main Flask application and HTTP route handlers
├── classifier.py              # ML classification inference logic
├── database.py                # SQLite schema creation and CRUD query operations
├── priority.py                # Priority assignment rules
├── severity.py                # Severity level definitions and calculations
├── status.py                  # Ticket status transition utilities
├── train_model.py             # Scikit-learn model training script
├── requirements.txt           # Python dependencies
├── .env.example               # Example environment variable template
├── templates/                 # Jinja2 HTML templates
│   ├── dashboard.html         # Main support agent dashboard
│   ├── index.html             # Ticket creation form
│   ├── login.html             # User login page
│   ├── register.html          # User registration page
│   └── severity_guide.html    # Severity classification reference guide
└── static/                    # Styling, icons, and background assets
```

---

## 🛠️ Technologies Used

- **Backend**: Python 3.10+, Flask, Werkzeug, Flask-JWT-Extended
- **Database**: SQLite3
- **Machine Learning**: Scikit-learn, NumPy, Pandas, Joblib
- **Frontend**: HTML5, Vanilla CSS, Bootstrap 5, FontAwesome, Chart.js

---

## 📦 Installation & Setup

1. **Clone the repository and navigate to Milestone-1**:
   ```bash
   cd Milestone-1
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   ```

5. **Train the classification model (optional/initial setup)**:
   ```bash
   python train_model.py
   ```

6. **Start the Flask server**:
   ```bash
   python app.py
   ```
   Open your browser at `http://127.0.0.1:5001`.
