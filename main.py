import requests
import smtplib
import json
import os
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 🧠 Filters
KEYWORDS = [
    'data', 'engineer', 'apprentice', 'software', 'development',
    'data analyst', 'python', 'full stack', 'data scientist', 'intern', 'data engineer'
]
LOCATION_FILTER = 'mumbai, maharashtra'
WEEKLY_DIGEST = False  # ⬅️ Set True for Monday-only emails

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

def send_email(subject, html_body):
    msg = MIMEMultipart("alternative")
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

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
            sheet.append_row([job['company'], job['title'], job['location'], job['url']])
        print("📄 Logged to Google Sheets")
    except Exception as e:
        print(f"⚠️ Google Sheet error: {e}")

def fetch_jobs():
    seen = load_seen_jobs()
    new_ids = seen.copy()
    new_jobs = []
    current_jobs = []

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
            posted_date = job.get("startDate", {}).get("value", "N/A")

            if any(k in title for k in KEYWORDS) and LOCATION_FILTER in location:
                job_link = f"{url.split('/wday')[0]}/en-US/{'/'.join(job_id.strip('/').split('/')[-2:])}"
                job_obj = {
                    "company": company,
                    "title": job.get("title"),
                    "location": location.title(),
                    "url": job_link,
                    "posted": posted_date
                }

                if job_id not in seen:
                    new_jobs.append(job_obj)
                    new_ids.append(job_id)
                else:
                    current_jobs.append(job_obj)

    save_seen_jobs(new_ids)
    return new_jobs, current_jobs

def group_jobs_by_company(jobs):
    grouped = {}
    for job in jobs:
        grouped.setdefault(job['company'], []).append(job)
    return dict(sorted(grouped.items(), key=lambda x: (x[0] != "S&P Global", x[0])))

def format_summary_table(new_grouped, current_grouped):
    all_companies = set(new_grouped) | set(current_grouped)
    rows = []
    for company in sorted(all_companies):
        new_count = len(new_grouped.get(company, []))
        seen_count = len(current_grouped.get(company, []))
        rows.append(f"<tr><td>{company}</td><td>{new_count}</td><td>{seen_count}</td></tr>")
    return f"""
    <h2>📊 Summary</h2>
    <table border="1" cellpadding="6" cellspacing="0">
        <tr><th>Company</th><th>New Jobs</th><th>Seen</th></tr>
        {''.join(rows)}
    </table><br>
    """

def format_html_section(title, jobs_grouped):
    if not jobs_grouped:
        return ""
    html = f"<h2>{title}</h2>"
    for company, jobs in jobs_grouped.items():
        html += f"<h3>🏢 <b>{company}</b></h3><ul>"
        for job in jobs:
            html += f"<li><b>{job['title']}</b> – {job['location']} – <i>Posted: {job['posted']}</i><br><a href='{job['url']}'>Apply</a></li>"
        html += "</ul><br>"
    return html

def main():
    if WEEKLY_DIGEST:
        now = datetime.utcnow()
        india_hour = (now.hour + 5) % 24
        if not (now.weekday() == 0 and india_hour == 10):
            print("⏱ Skipping — not Monday 10AM IST")
            return

    new_jobs, current_jobs = fetch_jobs()
    grouped_new = group_jobs_by_company(new_jobs)
    grouped_current = group_jobs_by_company(current_jobs)

    if grouped_new or grouped_current:
        html_body = "<html><body style='font-family: Arial;'>"
        html_body += "<h1>💼 Job Monitor: Top Roles for You</h1>"
        html_body += format_summary_table(grouped_new, grouped_current)
        html_body += format_html_section("🆕 New Matching Jobs", grouped_new)
        html_body += format_html_section("📋 Current Listings (Already Seen)", grouped_current)
        html_body += "<p><i>🧠 Powered by your job alert bot</i></p></body></html>"

        send_email("📡 Job Alert Summary", html_body)

        if new_jobs:
            log_to_sheet(new_jobs)
    else:
        send_email(
            "✅ Job Bot Check-In: No New Jobs",
            "<p>The job bot ran fine but no new or matching jobs were found this time. ✅</p>"
        )
        print("ℹ️ No jobs matched.")

if __name__ == "__main__":
    main()
