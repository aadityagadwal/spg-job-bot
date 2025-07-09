import requests
import smtplib
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 🧠 Filters
KEYWORDS = [
    'data', 'engineer', 'apprentice', 'software', 'development',
    'data analyst', 'python', 'full stack', 'data scientist', 'intern'
]
LOCATION_FILTER = 'mumbai, maharashtra'

# 📬 Email config
EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_RECEIVER = 'aadityagadwal11@gmail.com'

# 📊 Google Sheet
SHEET_ID = os.getenv('SHEET_ID')
CACHE_FILE = 'job_ids.json'
GOOGLE_CREDS_FILE = 'sgpjobtracker-465403-99d56dd31314.json'

# 🔗 Workday Job APIs (10 Companies)
COMPANY_SOURCES = {
    "S&P Global": "https://spgi.wd5.myworkdayjobs.com/wday/cxs/spgi/SPGI_Careers/jobs",
    "KPMG India": "https://kpmg.wd1.myworkdayjobs.com/wday/cxs/kpmgcareers/KPMG_Careers/jobs",
    "Capgemini India": "https://capgemini.wd3.myworkdayjobs.com/wday/cxs/capgemini/Capgemini_India/jobs",
    "Nasdaq": "https://nasdaq.wd1.myworkdayjobs.com/wday/cxs/nasdaqcareers/NasdaqCareers/jobs",
    "PwC": "https://pwc.wd3.myworkdayjobs.com/wday/cxs/pwc/External_Careers/jobs",
    "Genpact": "https://genpact.wd1.myworkdayjobs.com/wday/cxs/genpactcareers/Genpact_Careers/jobs",
    "DXC Technology": "https://dxc.wd1.myworkdayjobs.com/wday/cxs/dxctechnology/External_Careers/jobs",
    "McKinsey & Co": "https://mckinsey.wd1.myworkdayjobs.com/wday/cxs/mckinseycareers/McKinseyCareers/jobs",
    "HP": "https://hp.wd5.myworkdayjobs.com/wday/cxs/hpcareers/HP/jobs",
    "Cognizant": "https://cognizant.wd5.myworkdayjobs.com/wday/cxs/cognizantcareers/CognizantCareers/jobs"
}

# ✅ Send email alert
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

# ✅ Load job ID cache
def load_seen_jobs():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return []

# ✅ Save updated cache
def save_seen_jobs(ids):
    with open(CACHE_FILE, 'w') as f:
        json.dump(ids, f)

# ✅ Log new jobs to Google Sheet
def log_to_sheet(jobs):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        for job in jobs:
            sheet.append_row([job['company'], job['title'], job['location'], job['url']])
        print("📄 Logged to Google Sheets")
    except Exception as e:
        print(f"⚠️ Google Sheet error: {e}")

# ✅ Fetch jobs from all sources
def fetch_jobs():
    seen = load_seen_jobs()
    new_ids = seen.copy()
    all_new_jobs = []

    for company, url in COMPANY_SOURCES.items():
        try:
            response = requests.post(url, json={"limit": 50, "offset": 0})
            response.raise_for_status()
            jobs = response.json().get("jobPostings", [])
        except Exception as e:
            print(f"⚠️ Failed to fetch jobs from {company}: {e}")
            continue

        for job in jobs:
            title = job.get("title", "").lower()
            location = job.get("locationsText", "").lower()
            job_id = job.get("externalPath", "")
            if any(k in title for k in KEYWORDS) and LOCATION_FILTER in location and job_id not in seen:
                job_link = f"{url.split('/wday')[0]}/en-US/{'/'.join(job_id.strip('/').split('/')[-2:])}"
                all_new_jobs.append({
                    "company": company,
                    "title": job.get("title"),
                    "location": location.title(),
                    "url": job_link
                })
                new_ids.append(job_id)

    if all_new_jobs:
        save_seen_jobs(new_ids)
    return all_new_jobs

# 🚀 Main logic
def main():
    jobs = fetch_jobs()
    if jobs:
        # ✅ Prioritize S&P Global jobs first
        spg_jobs = [j for j in jobs if j['company'] == 'S&P Global']
        other_jobs = [j for j in jobs if j['company'] != 'S&P Global']
        sorted_jobs = spg_jobs + other_jobs

        body = "\n\n".join([
            f"Company: {j['company']}\nTitle: {j['title']}\nLocation: {j['location']}\nLink: {j['url']}"
            for j in sorted_jobs
        ])

        send_email("🧠 New Job Alerts from Top Companies", body)
        log_to_sheet(jobs)
    else:
        # ✅ Send confirmation email when no jobs found
        send_email(
            "✅ Job Bot Check-In: No New Jobs",
            "The job alert bot ran successfully.\n\nNo new matching jobs were found this time, but everything is working fine. ✅"
        )
        print("ℹ️ No new matching jobs found.")

if __name__ == "__main__":
    main()
