"""
Xiaomi Register — Playwright core for registration flow.
Handles: _sign extraction, encrypted values, EUI header, SSO cookie.
"""

import asyncio
import json
import re
import time
from playwright.async_api import async_playwright, Page, BrowserContext

class XiaomiRegister:
    def __init__(self, headless=True, timeout=30000):
        self.headless = headless
        self.timeout = timeout
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # Captured data
        self._sign = None
        self.encrypted_email = None
        self.encrypted_password = None
        self.eui_header = None
        self.sso_cookie = None
        
        # Request interception
        self.captured_requests = []
        self.captured_responses = []
    
    async def start(self):
        """Start Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
                "--disable-gpu"
            ]
        )
        
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        self.page = await self.context.new_page()
        
        # Setup request interception
        self.page.on("request", self._on_request)
        self.page.on("response", self._on_response)
        
        print("Playwright browser started")
    
    async def stop(self):
        """Stop Playwright browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("Playwright browser stopped")
    
    async def _on_request(self, request):
        """Capture outgoing requests"""
        url = request.url
        if "xiaomi" in url or "mimo" in url:
            self.captured_requests.append({
                "url": url,
                "method": request.method,
                "headers": request.headers,
                "post_data": request.post_data
            })
    
    async def _on_response(self, response):
        """Capture incoming responses"""
        url = response.url
        if "xiaomi" in url or "mimo" in url:
            try:
                body = await response.text()
                self.captured_responses.append({
                    "url": url,
                    "status": response.status,
                    "body": body
                })
            except:
                pass
    
    async def get_registration_data(self, email: str, password: str):
        """Navigate to registration page and extract data"""
        try:
            # Navigate to Mimo login page
            await self.page.goto("https://platform.xiaomimimo.com/login", timeout=self.timeout)
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            
            # Click "Sign up" or "Register" link
            signup_selectors = [
                'text="Sign up"',
                'text="Register"',
                'text="注册"',
                'a[href*="register"]',
                'button:has-text("Sign up")',
                'button:has-text("Register")'
            ]
            
            for selector in signup_selectors:
                try:
                    await self.page.click(selector, timeout=5000)
                    break
                except:
                    continue
            
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            
            # Extract _sign from URL
            current_url = self.page.url
            if "_sign" in current_url:
                match = re.search(r'_sign=([^&]+)', current_url)
                if match:
                    self._sign = match.group(1)
                    print(f"Extracted _sign: {self._sign[:20]}...")
            
            # Also try to extract from page source
            if not self._sign:
                page_content = await self.page.content()
                match = re.search(r'_sign["\s:=]+["\']([^"\']+)', page_content)
                if match:
                    self._sign = match.group(1)
                    print(f"Extracted _sign from source: {self._sign[:20]}...")
            
            # Fill form and capture encrypted values
            await self._fill_registration_form(email, password)
            
            # Extract EUI header from captured requests
            for req in self.captured_requests:
                if "EUI" in str(req.get("headers", {})):
                    self.eui_header = req["headers"].get("EUI") or req["headers"].get("eui")
                    print(f"Extracted EUI: {self.eui_header[:20]}...")
                    break
            
            # Extract encrypted email and password
            for req in self.captured_requests:
                post_data = req.get("post_data", "")
                if post_data and "email" in post_data and "password" in post_data:
                    try:
                        data = json.loads(post_data)
                        self.encrypted_email = data.get("email")
                        self.encrypted_password = data.get("password")
                        print(f"Extracted encrypted email: {self.encrypted_email[:20]}...")
                        break
                    except:
                        pass
            
            return {
                "_sign": self._sign,
                "encrypted_email": self.encrypted_email,
                "encrypted_password": self.encrypted_password,
                "eui_header": self.eui_header,
                "url": current_url
            }
            
        except Exception as e:
            print(f"Error getting registration data: {e}")
            return None
    
    async def _fill_registration_form(self, email: str, password: str):
        """Fill registration form"""
        # Wait for form to load
        await self.page.wait_for_timeout(2000)
        
        # Fill email field
        email_selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[placeholder*="email"]',
            'input[placeholder*="Email"]',
            '#email'
        ]
        
        for selector in email_selectors:
            try:
                await self.page.fill(selector, email, timeout=5000)
                break
            except:
                continue
        
        # Fill password field
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[placeholder*="password"]',
            'input[placeholder*="Password"]',
            '#password'
        ]
        
        for selector in password_selectors:
            try:
                await self.page.fill(selector, password, timeout=5000)
                break
            except:
                continue
        
        # Wait for encryption
        await self.page.wait_for_timeout(1000)
    
    async def follow_sso_redirect(self):
        """Follow SSO redirect and extract cookie"""
        try:
            # Wait for redirect
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            
            # Extract api-platform_ph cookie
            cookies = await self.context.cookies()
            for cookie in cookies:
                if cookie["name"] == "api-platform_ph":
                    self.sso_cookie = cookie["value"]
                    print(f"Extracted SSO cookie: {self.sso_cookie[:20]}...")
                    break
            
            return self.sso_cookie
            
        except Exception as e:
            print(f"Error following SSO redirect: {e}")
            return None
    
    async def get_captcha_data(self):
        """Get captcha data from page"""
        try:
            # Look for captcha iframe or container
            captcha_selectors = [
                'iframe[src*="recaptcha"]',
                'div.g-recaptcha',
                '#captcha',
                '.captcha'
            ]
            
            for selector in captcha_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        # Extract sitekey
                        sitekey = await element.get_attribute("data-sitekey")
                        if sitekey:
                            return {"sitekey": sitekey}
                except:
                    continue
            
            # Try to find sitekey in page source
            page_content = await self.page.content()
            match = re.search(r'data-sitekey="([^"]+)"', page_content)
            if match:
                return {"sitekey": match.group(1)}
            
            return None
            
        except Exception as e:
            print(f"Error getting captcha data: {e}")
            return None

async def get_registration_data(email: str, password: str, headless=True):
    """Quick function to get registration data"""
    register = XiaomiRegister(headless=headless)
    await register.start()
    
    try:
        data = await register.get_registration_data(email, password)
        return data
    finally:
        await register.stop()

async def follow_sso_redirect(headless=True):
    """Quick function to follow SSO redirect"""
    register = XiaomiRegister(headless=headless)
    await register.start()
    
    try:
        cookie = await register.follow_sso_redirect()
        return cookie
    finally:
        await register.stop()

if __name__ == "__main__":
    # Test registration data extraction
    async def test():
        data = await get_registration_data(
            email="test@example.com",
            password="TestPassword123!",
            headless=True
        )
        print(f"Registration data: {data}")
    
    asyncio.run(test())
