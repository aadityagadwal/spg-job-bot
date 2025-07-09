import requests
import smtplib
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Setup
KEYWORDS = ['data', 'engineer', 'apprentice', 'software', 'development', 'data analyst', 'python', 'full stack']
LOCATION_FILTER = 'mumbai, maharashtra'
URL = "https://spgi.wd5.myworkdayjobs.com/wday/cxs/spgi/SPGI_Careers/jobs"
EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_RECEIVER = 'aadityagadwal11@gmail.com'
SHEET_ID = os.getenv('SHEET_ID')
CACHE_FILE = 'job_ids.json'
GOOGLE_CREDS_FILE = 'sgpjobtracker-465403-99d56dd31314.json'

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Email sent")
    except Exception as e:
        print(f"❌ Email failed: {e}")

def load_seen_jobs():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return []

def save_seen_jobs(ids):
    with open(CACHE_FILE, 'w') as f:
        json.dump(ids, f)

def log_to_sheet(jobs):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        for job in jobs:
            sheet.append_row([job['title'], job['location'], job['url']])
        print("📄 Logged to Google Sheets")
    except Exception as e:
        print(f"⚠️ Failed to log to sheet: {e}")

def fetch_jobs():
    response = requests.post(URL, json={"limit": 50, "offset": 0})
    jobs = response.json().get("jobPostings", [])
    matched_jobs = []
    seen = load_seen_jobs()
    new_ids = seen.copy()

    for job in jobs:
        title = job.get("title", "").lower()
        location = job.get("locationsText", "").lower()
        job_id = job.get("externalPath", "")
        if any(k in title for k in KEYWORDS) and LOCATION_FILTER in location and job_id not in seen:
            full_url = f"https://spgi.wd5.myworkdayjobs.com/SPGI_Careers{job_id}"
            matched_jobs.append({
                "title": job.get("title"),
                "location": location.title(),
                "url": full_url
            })
            new_ids.append(job_id)

    if matched_jobs:
        save_seen_jobs(new_ids)
    return matched_jobs

def main():
    jobs = fetch_jobs()
    if jobs:
        body = "\n\n".join([f"Title: {j['title']}\nLocation: {j['location']}\nLink: {j['url']}" for j in jobs])
        send_email("🧠 New S&P Global Job Alert", body)
        log_to_sheet(jobs)
    else:
        print("ℹ️ No new matching jobs found.")

if __name__ == "__main__":
    main()
