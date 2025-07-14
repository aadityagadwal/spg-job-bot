# 🤖 SPG Job Bot

A fully automated job scraper and notifier that tracks real-time job openings (especially from **S&P Global**) and sends **HTML-formatted email alerts** and optionally **WhatsApp notifications**. Built with Python and scheduled using GitHub Actions.

---

## 🔍 Features

- ✅ Real-time job scraping (every 30 minutes)
- 🏢 Prioritizes **S&P Global** job listings
- 📍 Filters based on location (e.g., Mumbai)
- ✉️ Sends HTML-styled job alerts via Gmail
- 📲 Optional WhatsApp notifications
- ⏱️ Powered by GitHub Actions (cron jobs)
- 📁 Weekly digest mode (optional)
- 📦 Clean, modular Python codebase

---

## ⚙️ Tech Stack

- **Python** (requests, BeautifulSoup, SMTP)
- **GitHub Actions** for automation
- **Gmail SMTP** for email delivery
- Optional: **Twilio** or **WhatsApp Web API** for messaging

---

## 🗂️ File Structure
spg-job-bot/
├── job_scraper.py # Scrapes & filters job listings
├── email_alert.py # Generates & sends styled emails
├── whatsapp_alert.py # (Optional) WhatsApp alerts
├── config.py # Configs & filters
├── .github/workflows/
│ └── job-scraper.yml # Scheduled GitHub Action
├── templates/
│ └── email_template.html # Prettified HTML email layout
└── README.md



