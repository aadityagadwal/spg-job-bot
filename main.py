import requests
import json
import time
from datetime import datetime

# Test configuration
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
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }

def test_api_endpoint(company, company_data):
    """Test a single API endpoint"""
    print(f"\n{'='*50}")
    print(f"🧪 Testing: {company}")
    print(f"URL: {company_data['url']}")
    print(f"{'='*50}")
    
    headers = get_headers()
    payload = {
        "appliedFacets": {},
        "limit": 5,  # Small limit for testing
        "offset": 0,
        "searchText": ""
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            company_data['url'], 
            json=payload, 
            headers=headers, 
            timeout=15
        )
        response_time = time.time() - start_time
        
        print(f"⏱️ Response time: {response_time:.2f}s")
        print(f"📊 Status code: {response.status_code}")
        print(f"📏 Response size: {len(response.content)} bytes")
        
        if response.status_code == 200:
            try:
                data = response.json()
                jobs = data.get("jobPostings", [])
                print(f"✅ SUCCESS: {len(jobs)} jobs found")
                
                # Show sample job data
                if jobs:
                    sample_job = jobs[0]
                    print(f"📋 Sample job:")
                    print(f"   Title: {sample_job.get('title', 'N/A')}")
                    print(f"   Location: {sample_job.get('locationsText', 'N/A')}")
                    print(f"   Posted: {sample_job.get('postedOn', {}).get('value', 'N/A')}")
                    print(f"   ID: {sample_job.get('externalPath', 'N/A')}")
                
                return True, len(jobs)
                
            except json.JSONDecodeError:
                print("❌ FAILED: Invalid JSON response")
                print(f"Response preview: {response.text[:200]}...")
                return False, 0
                
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"Response preview: {response.text[:200]}...")
            return False, 0
            
    except requests.exceptions.Timeout:
        print("❌ FAILED: Request timeout")
        return False, 0
    except requests.exceptions.ConnectionError:
        print("❌ FAILED: Connection error")
        return False, 0
    except requests.exceptions.RequestException as e:
        print(f"❌ FAILED: Request error - {e}")
        return False, 0
    except Exception as e:
        print(f"❌ FAILED: Unexpected error - {e}")
        return False, 0

def test_alternative_endpoints():
    """Test alternative API patterns"""
    print(f"\n{'='*50}")
    print("🔄 Testing Alternative API Patterns")
    print(f"{'='*50}")
    
    # Try different API patterns that might work
    alternatives = [
        {
            "name": "S&P Global (Alternative 1)",
            "url": "https://spgi.wd5.myworkdayjobs.com/SPGI_Careers",
            "method": "GET"
        },
        {
            "name": "S&P Global (Alternative 2)", 
            "url": "https://spgi.wd5.myworkdayjobs.com/wday/cxs/spgi/SPGI_Careers",
            "method": "GET"
        }
    ]
    
    for alt in alternatives:
        print(f"\n🔍 Testing {alt['name']}")
        try:
            if alt['method'] == 'GET':
                response = requests.get(alt['url'], timeout=10)
            else:
                response = requests.post(alt['url'], json={}, timeout=10)
                
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ GET request successful")
            else:
                print(f"❌ Failed with status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Main testing function"""
    print("🚀 Starting Workday API Endpoint Tests")
    print(f"🕐 Test started at: {datetime.now()}")
    
    results = {}
    total_jobs = 0
    
    # Test each company endpoint
    for company, company_data in COMPANY_SOURCES.items():
        success, job_count = test_api_endpoint(company, company_data)
        results[company] = {
            'success': success,
            'job_count': job_count
        }
        total_jobs += job_count
        time.sleep(2)  # Rate limiting
    
    # Test alternatives
    test_alternative_endpoints()
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print(f"{'='*50}")
    
    successful = sum(1 for r in results.values() if r['success'])
    total_companies = len(results)
    
    print(f"✅ Successful APIs: {successful}/{total_companies}")
    print(f"📋 Total jobs found: {total_jobs}")
    print(f"🕐 Test completed at: {datetime.now()}")
    
    print(f"\n📋 Detailed Results:")
    for company, result in results.items():
        status = "✅ WORKING" if result['success'] else "❌ FAILED"
        job_count = f"({result['job_count']} jobs)" if result['success'] else ""
        print(f"  {company}: {status} {job_count}")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if successful > 0:
        print("✅ Some APIs are working! Your job scraper should find jobs.")
    else:
        print("❌ No APIs are working. Consider alternative approaches:")
        print("   - Try web scraping the public job pages")
        print("   - Use job aggregator APIs (LinkedIn, Indeed)")
        print("   - Check if companies have RSS feeds")
    
    print(f"\n🏁 Test completed!")

if __name__ == "__main__":
    main()
