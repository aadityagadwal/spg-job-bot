import requests
import smtplib
import json
import os
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import random

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

# 🔗 Updated Workday Job APIs with proper headers and request structure
COMPANY_SOURCES = {
    "S&P Global": {
        "url": "https://spgi.wd5.myworkdayjobs.com/wday/cxs/spgi/SPGI_Careers/jobs",
        "base_url": "https://spgi.wd5.myworkdayjobs.com/SPGI_Careers"
    },
    "KPMG India": {
        "url": "https://kpmg.wd1.myworkdayjobs.com/wday/cxs/kpmgcareers/KPMG_Careers/jobs",
        "base_url": "https://kpmg.wd1.myworkdayjobs.com/KPMG_Careers"
    },
    "Capgemini India": {
        "url": "https://capgemini.wd3.myworkdayjobs.com/wday/cxs/capgemini/Capgemini_India/jobs",
        "base_url": "https://capgemini.wd3.myworkdayjobs.com/Capgemini_India"
    },
    "Nasdaq": {
        "url": "https://nasdaq.wd1.myworkdayjobs.com/wday/cxs/nasdaqcareers/NasdaqCareers/jobs",
        "base_url": "https://nasdaq.wd1.myworkdayjobs.com/NasdaqCareers"
    },
    "PwC": {
        "url": "https://pwc.wd3.myworkdayjobs.com/wday/cxs/pwc/External_Careers/jobs",
        "base_url": "https://pwc.wd3.myworkdayjobs.com/External_Careers"
    },
    "Genpact": {
        "url": "https://genpact.wd1.myworkdayjobs.com/wday/cxs/genpactcareers/Genpact_Careers/jobs",
        "base_url": "https://genpact.wd1.myworkdayjobs.com/Genpact_Careers"
    },
    "DXC Technology": {
        "url": "https://dxc.wd1.myworkdayjobs.com/wday/cxs/dxctechnology/External_Careers/jobs",
        "base_url": "https://dxc.wd1.myworkdayjobs.com/External_Careers"
    },
    "McKinsey & Co": {
        "url": "https://mckinsey.wd1.myworkdayjobs.com/wday/cxs/mckinseycareers/McKinseyCareers/jobs",
        "base_url": "https://mckinsey.wd1.myworkdayjobs.com/McKinseyCareers"
    },
    "HP": {
        "url": "https://hp.wd5.myworkdayjobs.com/wday/cxs/hpcareers/HP/jobs",
        "base_url": "https://hp.wd5.myworkdayjobs.com/HP"
    },
    "Cognizant": {
        "url": "https://cognizant.wd5.myworkdayjobs.com/wday/cxs/cognizantcareers/CognizantCareers/jobs",
        "base_url": "https://cognizant.wd5.myworkdayjobs.com/CognizantCareers"
    }
}

def get_headers():
    """Return proper headers for Workday API requests"""
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }

def send_email(subject, html_body):
    """Send HTML email with error handling"""
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("❌ Email credentials not configured")
        return False
        
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
        print("✅ Email sent successfully")
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False

def load_seen_jobs():
    """Load previously seen job IDs from cache file"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            print("⚠️ Cache file corrupted, starting fresh")
            return []
    return []

def save_seen_jobs(ids):
    """Save job IDs to cache file"""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(ids, f, indent=2)
        print(f"💾 Saved {len(ids)} job IDs to cache")
    except Exception as e:
        print(f"❌ Failed to save cache: {e}")

def log_to_sheet(jobs):
    """Log new jobs to Google Sheets"""
    if not SHEET_ID:
        print("⚠️ Google Sheets not configured")
        return
        
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        
        for job in jobs:
            sheet.append_row([
                job['company'], 
                job['title'], 
                job['location'], 
                job['url'], 
                job['posted'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ])
        print(f"📄 Logged {len(jobs)} jobs to Google Sheets")
    except Exception as e:
        print(f"⚠️ Google Sheet error: {e}")

def construct_job_url(company_data, job_id):
    """Construct proper job URL from job ID"""
    base_url = company_data['base_url']
    # Remove leading slash if present
    job_id = job_id.lstrip('/')
    return f"{base_url}/job/{job_id}"

def fetch_jobs_from_company(company, company_data):
    """Fetch jobs from a single company with proper error handling"""
    url = company_data['url']
    headers = get_headers()
    
    # Updated payload structure for Workday API
    payload = {
        "appliedFacets": {},
        "limit": 50,
        "offset": 0,
        "searchText": ""
    }
    
    try:
        # Add random delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        jobs = data.get("jobPostings", [])
        
        if not jobs:
            print(f"⚠️ No jobs returned from {company}")
            return []
            
        print(f"📦 {company}: {len(jobs)} jobs fetched")
        return jobs
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout fetching from {company}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed for {company}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response from {company}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error fetching from {company}: {e}")
        return []

def process_job(job, company, company_data):
    """Process a single job posting"""
    try:
        title = job.get("title", "").lower()
        location = job.get("locationsText", "").lower()
        job_id = job.get("externalPath", "")
        posted_date = job.get("postedOn", {}).get("value", "N/A")
        
        # If postedOn is not available, try startDate
        if posted_date == "N/A":
            posted_date = job.get("startDate", {}).get("value", "N/A")
        
        # Check if job matches our criteria
        if not any(keyword in title for keyword in KEYWORDS):
            return None
            
        if LOCATION_FILTER not in location:
            return None
            
        # Construct proper job URL
        job_url = construct_job_url(company_data, job_id)
        
        return {
            "company": company,
            "title": job.get("title", ""),
            "location": location.title(),
            "url": job_url,
            "posted": posted_date,
            "job_id": job_id
        }
        
    except Exception as e:
        print(f"⚠️ Error processing job: {e}")
        return None

def fetch_jobs():
    """Main function to fetch jobs from all companies"""
    seen = load_seen_jobs()
    new_ids = seen.copy()
    new_jobs = []
    current_jobs = []
    
    print(f"🔍 Starting job search with {len(seen)} previously seen jobs")
    
    for company, company_data in COMPANY_SOURCES.items():
        print(f"\n📡 Fetching jobs from {company}...")
        jobs = fetch_jobs_from_company(company, company_data)
        
        if not jobs:
            continue
            
        matching_jobs = 0
        for job in jobs:
            processed_job = process_job(job, company, company_data)
            if not processed_job:
                continue
                
            matching_jobs += 1
            job_id = processed_job['job_id']
            
            if job_id not in seen:
                new_jobs.append(processed_job)
                new_ids.append(job_id)
                print(f"  🆕 New: {processed_job['title']}")
            else:
                current_jobs.append(processed_job)
        
        print(f"  ✅ {matching_jobs} matching jobs found")
    
    print(f"\n📊 Summary:")
    print(f"🆕 New Matching Jobs: {len(new_jobs)}")
    print(f"📋 Previously Seen Matching Jobs: {len(current_jobs)}")
    
    save_seen_jobs(new_ids)
    return new_jobs, current_jobs

def group_jobs_by_company(jobs):
    """Group jobs by company and sort with S&P Global first"""
    grouped = {}
    for job in jobs:
        grouped.setdefault(job['company'], []).append(job)
    return dict(sorted(grouped.items(), key=lambda x: (x[0] != "S&P Global", x[0])))

def format_summary_table(new_grouped, current_grouped):
    """Format summary table for email"""
    all_companies = set(new_grouped) | set(current_grouped)
    rows = []
    total_new = sum(len(jobs) for jobs in new_grouped.values())
    total_seen = sum(len(jobs) for jobs in current_grouped.values())
    
    for company in sorted(all_companies):
        new_count = len(new_grouped.get(company, []))
        seen_count = len(current_grouped.get(company, []))
        rows.append(f"<tr><td>{company}</td><td>{new_count}</td><td>{seen_count}</td></tr>")
    
    # Add total row
    rows.append(f"<tr style='font-weight: bold; background-color: #f0f0f0;'><td>TOTAL</td><td>{total_new}</td><td>{total_seen}</td></tr>")
    
    return f"""
    <h2>📊 Job Search Summary</h2>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
        <tr style="background-color: #4CAF50; color: white;">
            <th>Company</th><th>New Jobs</th><th>Previously Seen</th>
        </tr>
        {''.join(rows)}
    </table><br>
    """

def format_html_section(title, jobs_grouped):
    """Format HTML section for job listings"""
    if not jobs_grouped:
        return ""
        
    html = f"<h2>{title}</h2>"
    for company, jobs in jobs_grouped.items():
        html += f"<h3>🏢 <b>{company}</b> ({len(jobs)} jobs)</h3><ul>"
        for job in jobs:
            html += f"""
            <li style="margin-bottom: 10px;">
                <b>{job['title']}</b><br>
                📍 {job['location']}<br>
                📅 Posted: {job['posted']}<br>
                <a href='{job['url']}' style="color: #1976D2; text-decoration: none;">🔗 Apply Now</a>
            </li>
            """
        html += "</ul><br>"
    return html

def main():
    """Main execution function"""
    print("🚀 Starting Job Monitor Bot...")
    print(f"📧 Email sender: {'✅ Set' if EMAIL_SENDER else '❌ Missing'}")
    print(f"🔑 Email password: {'✅ Set' if EMAIL_PASSWORD else '❌ Missing'}")
    print(f"📊 Sheet ID: {'✅ Set' if SHEET_ID else '❌ Missing'}")
    
    # Test email immediately
    if EMAIL_SENDER and EMAIL_PASSWORD:
        print("📧 Testing email configuration...")
        test_result = send_email(
            "🧪 Job Bot Test - Configuration Check", 
            "<p>✅ Email configuration is working! Job bot will start monitoring now.</p>"
        )
        if not test_result:
            print("❌ Email test failed - check your Gmail app password")
            return
    else:
        print("❌ Email credentials missing - check GitHub secrets")
        return
    
    # Check for weekly digest mode
    if WEEKLY_DIGEST:
        now = datetime.utcnow()
        india_hour = (now.hour + 5) % 24
        if not (now.weekday() == 0 and india_hour == 10):
            print("⏱️ Skipping — Weekly digest mode enabled, not Monday 10AM IST")
            return
    
    # Fetch jobs
    new_jobs, current_jobs = fetch_jobs()
    grouped_new = group_jobs_by_company(new_jobs)
    grouped_current = group_jobs_by_company(current_jobs)
    
    # Send email report
    if grouped_new or grouped_current:
        html_body = """
        <html>
        <body style='font-family: Arial, sans-serif; line-height: 1.6; color: #333;'>
        <h1 style='color: #2E7D32;'>💼 Job Monitor: Your Personalized Job Alert</h1>
        """
        
        html_body += format_summary_table(grouped_new, grouped_current)
        
        if grouped_new:
            html_body += format_html_section("🆕 New Job Opportunities", grouped_new)
        
        if grouped_current:
            html_body += format_html_section("📋 Previously Notified Jobs (Still Available)", grouped_current)
        
        html_body += """
        <hr style="margin: 20px 0;">
        <p style="font-size: 12px; color: #666;">
            <i>🤖 This alert was generated by your automated job monitoring system.<br>
            Keywords: data, engineer, software, development, analyst, python, full stack, scientist, intern<br>
            Location: Mumbai, Maharashtra</i>
        </p>
        </body>
        </html>
        """
        
        subject = f"📡 Job Alert: {len(new_jobs)} New Jobs Found!" if new_jobs else "📋 Job Monitor Update"
        send_email(subject, html_body)
        
        # Log new jobs to Google Sheets
        if new_jobs:
            log_to_sheet(new_jobs)
            
    else:
        # Send check-in email when no jobs found
        html_body = """
        <html>
        <body style='font-family: Arial, sans-serif;'>
        <h2>✅ Job Monitor Check-In</h2>
        <p>Your job monitoring system ran successfully, but no new matching jobs were found at this time.</p>
        <p><i>The system will continue monitoring and will notify you when new opportunities become available.</i></p>
        </body>
        </html>
        """
        send_email("✅ Job Monitor: No New Jobs Found", html_body)
        print("ℹ️ No matching jobs found in this run.")
    
    print("🏁 Job Monitor Bot completed successfully!")

if __name__ == "__main__":
    main()
