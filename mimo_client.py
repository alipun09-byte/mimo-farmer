"""
Mimo Client — Requests-based Mimo API client.
Handles: email bind, confirm, plan activation, API key creation.
"""

import requests
import json
import time
from typing import Optional, Dict

class MimoClient:
    def __init__(self, sso_cookie: str, proxy: str = None):
        self.sso_cookie = sso_cookie
        self.base_url = "https://platform.xiaomimimo.com"
        self.api_url = f"{self.base_url}/api/v1"
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.base_url,
            "Origin": self.base_url
        })
        
        # Set cookies
        self.session.cookies.set("api-platform_ph", sso_cookie, domain="platform.xiaomimimo.com")
        
        # Set proxy
        if proxy:
            self.session.proxies = {
                "http": proxy,
                "https": proxy
            }
    
    def bind_email(self, email: str) -> Dict:
        """Bind email to Mimo account"""
        try:
            response = self.session.post(
                f"{self.api_url}/email/bind",
                json={"email": email},
                timeout=30
            )
            
            data = self._parse_response(response)
            print(f"Bind email response: {data}")
            return data
            
        except Exception as e:
            print(f"Bind email error: {e}")
            return {"error": str(e)}
    
    def confirm_bind(self, email: str, code: str) -> Dict:
        """Confirm email bind with verification code"""
        try:
            response = self.session.post(
                f"{self.api_url}/email/confirm",
                json={"email": email, "code": code},
                timeout=30
            )
            
            data = self._parse_response(response)
            print(f"Confirm bind response: {data}")
            return data
            
        except Exception as e:
            print(f"Confirm bind error: {e}")
            return {"error": str(e)}
    
    def get_plan_detail(self) -> Dict:
        """Get current plan details"""
        try:
            response = self.session.get(
                f"{self.api_url}/tokenPlan/detail",
                timeout=30
            )
            
            data = self._parse_response(response)
            return data
            
        except Exception as e:
            print(f"Get plan detail error: {e}")
            return {"error": str(e)}
    
    def wait_for_plan_activation(self, max_wait: int = 60, interval: int = 5) -> bool:
        """Wait for plan to be activated"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            plan = self.get_plan_detail()
            
            if plan.get("planCode"):
                print(f"Plan activated: {plan.get('planCode')}")
                return True
            
            print(f"Waiting for plan activation... ({int(time.time() - start_time)}s)")
            time.sleep(interval)
        
        print("Plan activation timeout")
        return False
    
    def create_apikey(self) -> Dict:
        """Create API key (requires active plan)"""
        try:
            response = self.session.post(
                f"{self.api_url}/tokenPlan/apiKey",
                timeout=30
            )
            
            data = self._parse_response(response)
            print(f"Create API key response: {data}")
            return data
            
        except Exception as e:
            print(f"Create API key error: {e}")
            return {"error": str(e)}
    
    def get_plan_list(self) -> list:
        """Get available plans"""
        try:
            response = self.session.get(
                f"{self.api_url}/tokenPlan/list",
                timeout=30
            )
            
            data = self._parse_response(response)
            return data.get("plans", [])
            
        except Exception as e:
            print(f"Get plan list error: {e}")
            return []
    
    def _parse_response(self, response: requests.Response) -> Dict:
        """Parse API response"""
        try:
            text = response.text
            
            # Strip &&&START&&& prefix if present
            if text.startswith("&&&START&&&"):
                text = text[11:]
            
            data = json.loads(text)
            return data
            
        except json.JSONDecodeError:
            return {"error": "Invalid JSON", "raw": response.text}
        except Exception as e:
            return {"error": str(e)}

def bind_email(sso_cookie: str, email: str, proxy: str = None) -> Dict:
    """Quick function to bind email"""
    client = MimoClient(sso_cookie=sso_cookie, proxy=proxy)
    return client.bind_email(email)

def confirm_bind(sso_cookie: str, email: str, code: str, proxy: str = None) -> Dict:
    """Quick function to confirm bind"""
    client = MimoClient(sso_cookie=sso_cookie, proxy=proxy)
    return client.confirm_bind(email, code)

def create_apikey(sso_cookie: str, proxy: str = None) -> Dict:
    """Quick function to create API key"""
    client = MimoClient(sso_cookie=sso_cookie, proxy=proxy)
    
    # Check if plan is active
    plan = client.get_plan_detail()
    if not plan.get("planCode"):
        print("No active plan, waiting...")
        if not client.wait_for_plan_activation():
            return {"error": "Plan not activated"}
    
    return client.create_apikey()

if __name__ == "__main__":
    # Test Mimo client
    print("Testing Mimo client...")
    
    # This would need a real SSO cookie
    # client = MimoClient(sso_cookie="test_cookie")
    # plan = client.get_plan_detail()
    # print(f"Plan: {plan}")
