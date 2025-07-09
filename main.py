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
import re

# 🧠 Improved Filters
KEYWORDS = [
    'data', 'engineer', 'apprentice', 'software', 'development', 'developer',
    'analyst', 'python', 'full stack', 'scientist', 'intern', 'programming',
    'backend', 'frontend', 'ml', 'machine learning', 'ai', 'artificial intelligence',
    'devops', 'cloud', 'java', 'javascript', 'react', 'angular', 'node'
]

# More flexible location matching
LOCATION_KEYWORDS = ['mumbai', 'maharashtra', 'bombay']  # Multiple variations
WEEKLY_DIGEST = False  # ⬅️ Set True for Monday-only emails
DEBUG_MODE = False  # Set True for detailed logging

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

def debug_print(message):
    """Print debug messages only if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(message)

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
        'Pragma': 'no-cache',
        'Referer': 'https://careers.workday.com/'
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
    job_id = job_id.lstrip('/')
    return f"{base_url}/job/{job_id}"

def matches_keywords(title):
    """Check if title matches any of our keywords (case-insensitive)"""
    title_lower = title.lower()
    matching_keywords = [kw for kw in KEYWORDS if kw in title_lower]
    return len(matching_keywords) > 0, matching_keywords

def matches_location(location):
    """Check if location matches our target areas (more flexible)"""
    location_lower = location.lower()
    # Remove extra spaces and normalize
    location_clean = re.sub(r'\s+', ' ', location_lower.strip())
    
    # Check for any of our location keywords
    for loc_keyword in LOCATION_KEYWORDS:
        if loc_keyword in location_clean:
            return True
    
    # Also check for "india" + any major city indicators
    if 'india' in location_clean and any(city in location_clean for city in ['mumbai', 'delhi', 'bangalore', 'pune']):
        return True
        
    return False

def get_job_field_safely(job, field_path):
    """Safely get nested field from job object"""
    try:
        current = job
        for field in field_path:
            if isinstance(current, dict) and field in current:
                current = current[field]
            else:
                return None
        return current
    except:
        return None

def extract_job_data(job):
    """Extract job data from various possible response formats"""
    # Try different possible field names for title
    title = (job.get("title") or 
             job.get("jobTitle") or 
             job.get("name") or 
             get_job_field_safely(job, ["title", "value"]) or "")
    
    # Try different possible field names for location
    location = (job.get("locationsText") or 
                job.get("location") or 
                job.get("locationText") or
                job.get("primaryLocation") or
                get_job_field_safely(job, ["location", "name"]) or
                get_job_field_safely(job, ["primaryLocation", "name"]) or "")
    
    # Try different possible field names for job ID
    job_id = (job.get("externalPath") or 
              job.get("jobId") or 
              job.get("id") or 
              job.get("requisitionId") or "")
    
    # Try different possible field names for posted date
    posted_date = (get_job_field_safely(job, ["postedOn", "value"]) or
                   get_job_field_safely(job, ["startDate", "value"]) or
                   job.get("postedDate") or
                   job.get("datePosted") or "N/A")
    
    return {
        'title': str(title),
        'location': str(location),
        'job_id': str(job_id),
        'posted_date': str(posted_date)
    }

def process_job(job, company, company_data):
    """Process a single job posting with improved filtering"""
    try:
        # Extract job data using multiple fallback methods
        job_data = extract_job_data(job)
        
        debug_print(f"🔍 Processing job from {company}:")
        debug_print(f"  Title: '{job_data['title']}'")
        debug_print(f"  Location: '{job_data['location']}'")
        debug_print(f"  Job ID: '{job_data['job_id']}'")
        debug_print(f"  Available fields: {list(job.keys())}")
        
        # Skip if essential fields are missing
        if not job_data['title'] or not job_data['job_id']:
            debug_print(f"  ❌ Missing essential fields (title or job_id)")
            return None
        
        # Check keyword matching
        keyword_match, matching_keywords = matches_keywords(job_data['title'])
        debug_print(f"  Keywords found: {matching_keywords}")
        
        if not keyword_match:
            debug_print(f"  ❌ No keywords matched in title")
            return None
        
        # Check location matching (more flexible)
        location_match = matches_location(job_data['location'])
        debug_print(f"  Location matches: {location_match}")
        debug_print(f"  Raw location: '{job_data['location']}'")
        
        # Skip location filter if location data is missing or unclear
        if job_data['location'] and not location_match:
            debug_print(f"  ❌ Location doesn't match target areas")
            return None
        
        # Construct proper job URL
        job_url = construct_job_url(company_data, job_data['job_id'])
        debug_print(f"  ✅ Job matched! URL: {job_url}")
        
        return {
            "company": company,
            "title": job_data['title'],
            "location": job_data['location'].title() if job_data['location'] else "Location not specified",
            "url": job_url,
            "posted": job_data['posted_date'],
            "job_id": job_data['job_id']
        }
        
    except Exception as e:
        debug_print(f"⚠️ Error processing job: {e}")
        return None

def fetch_jobs_from_company(company, company_data):
    """Fetch jobs from a single company with improved error handling"""
    url = company_data['url']
    headers = get_headers()
    
    # Try different payload structures
    payloads = [
        {
            "appliedFacets": {},
            "limit": 50,
            "offset": 0,
            "searchText": ""
        },
        {
            "appliedFacets": {},
            "limit": 50,
            "offset": 0
        },
        {
            "limit": 50,
            "offset": 0
        }
    ]
    
    for i, payload in enumerate(payloads):
        try:
            # Add random delay to avoid rate limiting
            time.sleep(random.uniform(2, 5))
            
            debug_print(f"📡 Trying payload {i+1} for {company}")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                debug_print(f"✅ Success with payload {i+1}")
                break
            else:
                debug_print(f"❌ Payload {i+1} failed with status {response.status_code}")
                continue
                
        except Exception as e:
            debug_print(f"❌ Payload {i+1} failed with error: {e}")
            continue
    else:
        print(f"❌ All payloads failed for {company}")
        return []
    
    try:
        # Try different possible response structures
        jobs = (data.get("jobPostings") or 
                data.get("jobs") or 
                data.get("data", {}).get("jobPostings") or
                data.get("data", {}).get("jobs") or [])
        
        debug_print(f"📦 {company} API Response:")
        debug_print(f"  Status: {response.status_code}")
        debug_print(f"  Response keys: {list(data.keys())}")
        debug_print(f"  Jobs found: {len(jobs)}")
        
        if not jobs:
            debug_print(f"  ⚠️ No jobs found. Sample response: {str(data)[:300]}...")
            return []
        
        # Show first job structure for debugging
        if jobs and DEBUG_MODE:
            debug_print(f"  🔍 First job structure: {list(jobs[0].keys())}")
            
        print(f"📦 {company}: {len(jobs)} jobs fetched")
        return jobs
        
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response from {company}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error processing response from {company}: {e}")
        return []

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
        
        # Add delay between companies
        time.sleep(random.uniform(1, 3))
    
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
    print(f"🐛 Debug mode: {'✅ Enabled' if DEBUG_MODE else '❌ Disabled'}")
    
    # Test email immediately
    if EMAIL_SENDER and EMAIL_PASSWORD:
        print("📧 Testing email configuration...")
        test_result = send_email(
            "🧪 Job Bot Test - Improved Configuration Check", 
            "<p>✅ Email configuration is working! Job bot will start monitoring with improved filtering now.</p>"
        )
        if not test_result:
            print("❌ Email test failed - check your Gmail app password")
            return
    else:
        print("❌ Email credentials missing - check environment variables")
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
    
    # Send email report - ALWAYS include current jobs
    html_body = """
    <html>
    <body style='font-family: Arial, sans-serif; line-height: 1.6; color: #333;'>
    <h1 style='color: #2E7D32;'>💼 Job Monitor: Your Personalized Job Alert (Improved)</h1>
    """
    
    html_body += format_summary_table(grouped_new, grouped_current)
    
    # Always show new jobs section (even if empty)
    if grouped_new:
        html_body += format_html_section("🆕 New Job Opportunities", grouped_new)
    else:
        html_body += "<h2>🆕 New Job Opportunities</h2><p><i>No new jobs found in this scan.</i></p><br>"
    
    # Always show current jobs section (even if empty)
    if grouped_current:
        html_body += format_html_section("📋 All Current Job Listings (Previously Seen)", grouped_current)
    else:
        html_body += "<h2>📋 All Current Job Listings</h2><p><i>No matching jobs currently available.</i></p><br>"
        
    html_body += """
    <hr style="margin: 20px 0;">
    <p style="font-size: 12px; color: #666;">
        <i>🤖 This alert was generated by your improved automated job monitoring system.<br>
        Keywords: data, engineer, software, development, analyst, python, full stack, scientist, intern, developer, ml, ai, devops, cloud<br>
        Location: Mumbai, Maharashtra, India (flexible matching)</i>
    </p>
    </body>
    </html>
    """
    
    # Send email with appropriate subject
    if new_jobs:
        subject = f"📡 Job Alert: {len(new_jobs)} New Jobs Found! (Improved)"
    else:
        subject = f"📋 Job Monitor: {len(current_jobs)} Current Jobs Available (Improved)"
    
    send_email(subject, html_body)
    
    # Log new jobs to Google Sheets
    if new_jobs:
        log_to_sheet(new_jobs)
    
    print("📧 Email sent with both new and current job listings!")
    print("🏁 Job Monitor Bot completed successfully!")

if __name__ == "__main__":
    main()
