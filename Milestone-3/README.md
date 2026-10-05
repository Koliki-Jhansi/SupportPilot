# SupportPilot – Milestone 3

## Multi-Agent AI Ticket Resolution

SupportPilot Milestone 3 introduces a collaborative Multi-Agent AI architecture designed to autonomously diagnose incoming support tickets, retrieve relevant IT solutions from a knowledge base, synthesize verified troubleshooting steps, calculate a weighted confidence score, and make deterministic auto-resolution or escalation decisions.

---

### Agents

1. **Diagnosis Agent**: Analyzes ticket content (title, description), identifies the technical domain (Network/VPN, Authentication, Hardware, Security, etc.), and determines symptom clarity.
2. **Retrieval Agent**: Interfaces with the RAG pipeline using TF-IDF and Cosine Similarity to query the IT knowledge base (`data/knowledge_base.json`) for matching solutions.
3. **Resolution Agent**: Synthesizes structured, step-by-step troubleshooting actions and calculates resolution completeness.
4. **Validation Agent**: Computes an overall weighted confidence score combining diagnostic accuracy, retrieval similarity, and resolution completeness.
5. **Escalation Agent**: Determines whether the ticket can be safely auto-resolved or requires escalation based on confidence threshold rules.

---

### Workflow

```text
Ticket
  ↓
Diagnosis
  ↓
Knowledge Retrieval
  ↓
Resolution Generation
  ↓
Validation (Weighted Confidence Scoring)
  ↓
Escalation Decision (AUTO_RESOLVE vs ESCALATE)
```

---

### Algorithms / Techniques

- **Multi-Agent Orchestration**: Sequential pipeline where specialized agents produce structured diagnostic artifacts consumed by downstream agents.
- **TF-IDF & Cosine Similarity**: Vector representation and semantic matching against knowledge-base articles.
- **RAG (Retrieval-Augmented Generation)**: Contextual retrieval and augmentation for accurate troubleshooting synthesis.
- **Weighted Confidence Scoring**:
  $$\text{Final Score} = (\text{Diagnosis Confidence} \times 40\%) + (\text{Retrieval Similarity} \times 40\%) + (\text{Resolution Completeness} \times 20\%)$$
  $$\text{AI Confidence} = \text{round}(\text{Final Score} \times 100, 2)$$
- **Threshold-Based Escalation**:
  - If $\text{AI Confidence} \ge 70.0\%$ $\rightarrow$ **`AUTO_RESOLVE`**
  - If $\text{AI Confidence} < 70.0\%$ $\rightarrow$ **`ESCALATE`**

---

### Files

```text
Milestone-3/
├── agents.py                  # MultiAgentSupportPilot and 5 specialized agents
├── app.py                     # Flask web app and multi-agent workflow routes
├── classifier.py              # ML ticket classification
├── database.py                # Database persistence
├── email_service.py           # Email notification handler
├── jira_service.py            # Atlassian Jira issue creation integration
├── priority.py                # Priority calculation
├── severity.py                # Severity calculation
├── status.py                  # Status management
├── test_rag.py                # RAG validation script
├── train_model.py             # Classifier training script
├── requirements.txt           # Python dependencies
├── .env.example               # Safe environment variable template
├── data/
│   └── knowledge_base.json    # IT support knowledge base
├── rag/                       # RAG Pipeline modules
│   ├── analyzer.py
│   ├── generator.py
│   ├── pipeline.py
│   └── retriever.py
├── templates/                 # Jinja2 HTML templates
│   ├── agents.html            # Multi-agent diagnostic UI
│   ├── ai_resolution.html     # AI resolution UI
│   ├── dashboard.html         # Analytics dashboard
│   ├── index.html             # Ticket creation form
│   ├── login.html             # Login
│   ├── register.html          # Registration
│   └── severity_guide.html    # Severity guide
└── static/                    # Static styling and images
```

---

### Technologies Used

- **AI & NLP**: Python 3.10+, Scikit-learn, TF-IDF, Cosine Similarity
- **Integrations**: Atlassian Jira Cloud REST API, SMTP SSL/TLS Email
- **Backend**: Flask, Flask-JWT-Extended, SQLite3
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, FontAwesome, Chart.js

---

### Installation & Execution

1. **Navigate to Milestone-3**:
   ```bash
   cd Milestone-3
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

4. **Run the server**:
   ```bash
   python app.py
   ```
   Open `http://127.0.0.1:5001/agents` to execute the multi-agent workflow on tickets.
