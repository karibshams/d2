# 🚀 AI Social Media Dashboard

An AI-powered, multi-platform social media management dashboard built with **Streamlit**, designed to automate content generation, intelligent comment replies, and seamless integrations with platforms like YouTube, Facebook, Instagram, LinkedIn, Twitter, and GoHighLevel (GHL).
## 📦 Project Structure


├── .env                      # Environment variables (DO NOT share publicly)
├── requirements.txt          # Python dependencies
├── run.py                    # Main entry point to launch the Streamlit app
├── setup\_database.py         # Script to initialize the database
│
├── app/                      # Main application package
│   ├── **init**.py
│   ├── config.py             # Configuration management
│   ├── dashboard.py          # Streamlit dashboard UI
│
│   ├── core/                 # Core AI logic
│   │   ├── **init**.py
│   │   ├── ai\_processor.py   # AI processing engine
│   │   ├── comment\_processor.py  # Comment management
│   │   ├── content\_generator.py  # Content generation tools
│   │   └── ghl\_manager.py    # GoHighLevel integration
│
│   ├── database/             # Database layer
│   │   ├── **init**.py
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── crud.py           # Database operations
│   │   └── connection.py     # Database connection setup
│
│   ├── integrations/         # Social media platform integrations
│   │   ├── **init**.py
│   │   ├── youtube.py
│   │   ├── facebook.py
│   │   ├── instagram.py
│   │   ├── linkedin.py
│   │   └── twitter.py
│
│   └── utils/                # Utilities and helpers
│       ├── **init**.py
│       ├── scheduler.py      # Background task scheduling
│       └── helpers.py
│
└── tests/                    # Unit tests
├── **init**.py
└── test\_manual\_comment.py

````

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/yourrepo.git
cd yourrepo
````

### 2. Create a Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate   # On Windows
# source venv/bin/activate  # On Mac/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file at the project root:

```ini
# Example .env
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql+psycopg2://user:password@localhost/dbname
```

---

## 🚀 Running the Application

Use the provided `run.py` to launch the dashboard:

```bash
python run.py
```

The dashboard will be accessible at:

```
http://localhost:8501
```

---

## ✨ Key Features

✅ AI-Powered Comment Generation
✅ Social Media Integrations (YouTube, Facebook, Instagram, LinkedIn, Twitter)
✅ GoHighLevel (GHL) Workflow Support
✅ Background Task Scheduler
✅ Modern Streamlit UI with Dark Theme
✅ Modular, Scalable Python Project Structure

---

## 🧪 Running Tests

```bash
pytest tests/
```

---

## 📌 Notes

* **Never share your `.env` file or API keys publicly.**
* Recommended to use Python 3.9+ for compatibility.

---

## 💡 Future Enhancements

* Sentiment Analysis on Comments
* Automated Post Scheduling
* Multi-User Authentication
* Enhanced Admin Dashboard


 
 
