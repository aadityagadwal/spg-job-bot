import requests
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Job filters
KEYWORDS = ['data', 'engineer', 'apprentice', 'software', 'development', 'data analyst', 'python', 'full stack']
LOCATION_FILTER = 'mumbai, maharashtra'

# Workday API URL
URL = "https://spgi.wd5.myworkdayjobs.com/wday/cxs/spgi/SPGI_Careers/jobs"

# Email config
EMAIL_SENDER = os.getenv('EMAIL_SENDER', 'aadityagadwal03@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'yzuw vfud jcpu wzhb')
EMAIL_RECEIVER = 'aadityagadwal11@gmail.com'

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

def fetch_jobs():
    response = requests.post(URL, json={"limit": 50, "offset": 0})
    jobs = response.json().get("jobPostings", [])
    matched_jobs = []

    for job in jobs:
        title = job.get("title", "").lower()
        location = job.get("locationsText", "").lower()
        if any(k in title for k in KEYWORDS) and LOCATION_FILTER in location:
            matched_jobs.append({
                "title": job.get("title"),
                "location": location.title(),
                "url": f"https://spgi.wd5.myworkdayjobs.com/SPGI_Careers{job.get('externalPath')}"
            })

    return matched_jobs

def main():
    jobs = fetch_jobs()
    if jobs:
        body = "\n\n".join(
            [f"Title: {j['title']}\nLocation: {j['location']}\nLink: {j['url']}" for j in jobs]
        )
        send_email("🧠 New S&P Global Job Alert", body)
    else:
        print("ℹ️ No matching jobs found.")

if __name__ == "__main__":
    main()
