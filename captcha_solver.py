"""
Captcha Solver — Solve reCAPTCHA Enterprise using Boterdrop-Solver or 2Captcha.
"""

import requests
import time
import json

class CaptchaSolver:
    def __init__(self, mode="boterdrop", boterdrop_url="http://localhost:8000", twocaptcha_api_key=None):
        self.mode = mode
        self.boterdrop_url = boterdrop_url.rstrip("/")
        self.twocaptcha_api_key = twocaptcha_api_key
        self.max_retries = 3
        
        if mode == "boterdrop":
            self._check_boterdrop()
        elif mode == "2captcha" and not twocaptcha_api_key:
            raise ValueError("2Captcha API key required")
    
    def _check_boterdrop(self):
        """Check if Boterdrop-Solver is running"""
        try:
            response = requests.get(f"{self.boterdrop_url}/docs", timeout=5)
            if response.status_code == 200:
                print("Boterdrop-Solver is running")
                return True
            else:
                print("Boterdrop-Solver not responding properly")
                return False
        except:
            print("Boterdrop-Solver is not running")
            return False
    
    def solve_recaptcha_enterprise(self, sitekey, page_url):
        """Solve reCAPTCHA Enterprise"""
        for attempt in range(self.max_retries):
            try:
                if self.mode == "boterdrop":
                    token = self._solve_boterdrop(sitekey, page_url)
                else:
                    token = self._solve_2captcha(sitekey, page_url)
                
                if token:
                    return token
                
                print(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(2)
                
            except Exception as e:
                print(f"Attempt {attempt + 1} error: {e}")
                time.sleep(2)
        
        return None
    
    def _solve_boterdrop(self, sitekey, page_url):
        """Solve using Boterdrop-Solver"""
        try:
            # Step 1: Get task ID
            response = requests.post(
                f"{self.boterdrop_url}/turnstile",
                json={
                    "sitekey": sitekey,
                    "url": page_url
                },
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"Boterdrop task error: {response.text}")
                return None
            
            task_data = response.json()
            task_id = task_data.get("task_id")
            
            if not task_id:
                print("No task ID returned")
                return None
            
            # Step 2: Poll for result
            for _ in range(30):  # Max 30 seconds
                time.sleep(1)
                
                result_response = requests.get(
                    f"{self.boterdrop_url}/result",
                    params={"task_id": task_id},
                    timeout=5
                )
                
                if result_response.status_code == 200:
                    result = result_response.json()
                    
                    if result.get("status") == "completed":
                        return result.get("token")
                    elif result.get("status") == "failed":
                        print(f"Boterdrop failed: {result.get('error')}")
                        return None
            
            print("Boterdrop timeout")
            return None
            
        except Exception as e:
            print(f"Boterdrop error: {e}")
            return None
    
    def _solve_2captcha(self, sitekey, page_url):
        """Solve using 2Captcha"""
        try:
            # Step 1: Submit task
            response = requests.post(
                "http://2captcha.com/in.php",
                data={
                    "key": self.twocaptcha_api_key,
                    "method": "enterprise",
                    "googlekey": sitekey,
                    "pageurl": page_url,
                    "json": 1
                },
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"2Captcha submit error: {response.text}")
                return None
            
            data = response.json()
            if data.get("status") != 1:
                print(f"2Captcha error: {data.get('request')}")
                return None
            
            task_id = data.get("request")
            
            # Step 2: Poll for result
            for _ in range(60):  # Max 60 seconds
                time.sleep(2)
                
                result_response = requests.get(
                    "http://2captcha.com/res.php",
                    params={
                        "key": self.twocaptcha_api_key,
                        "action": "get",
                        "id": task_id,
                        "json": 1
                    },
                    timeout=5
                )
                
                if result_response.status_code == 200:
                    result = result_response.json()
                    
                    if result.get("status") == 1:
                        return result.get("request")
                    elif result.get("request") != "CAPCHA_NOT_READY":
                        print(f"2Captcha failed: {result.get('request')}")
                        return None
            
            print("2Captcha timeout")
            return None
            
        except Exception as e:
            print(f"2Captcha error: {e}")
            return None

def solve_captcha(sitekey, page_url, mode="boterdrop", **kwargs):
    """Quick function to solve captcha"""
    solver = CaptchaSolver(mode=mode, **kwargs)
    return solver.solve_recaptcha_enterprise(sitekey, page_url)

if __name__ == "__main__":
    # Test Boterdrop-Solver
    print("Testing Boterdrop-Solver...")
    solver = CaptchaSolver(mode="boterdrop")
    
    # Test with a dummy sitekey
    token = solver.solve_recaptcha_enterprise(
        sitekey="6LeBM0ocAAAAAEwYcFUjtxpVbs-0rnbSVXBBXmh4",
        page_url="https://account.xiaomi.com/pass/register"
    )
    
    if token:
        print(f"Captcha solved: {token[:50]}...")
    else:
        print("Captcha failed")
