"""
Xiaomi Mimo Auto-Registration — Windows Edition
Jalankan di laptop Windows: py register.py

Flow:
1. Buka Chrome (visible)
2. Generate random email
3. Fill form + click Next
4. reCAPTCHA checkbox auto-pass (residential IP)
5. Extract verification code dari email
6. Complete registration
7. Bind email + get API key
8. Simpan ke output/api_keys.txt

Dependencies:
  pip install playwright requests
  playwright install chromium
"""

import asyncio
import json
import os
import re
import sys
import time
import random
import string
import requests as req
from pathlib import Path
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────
COUNT = 10  # Jumlah akun yang mau di-register
PASSWORD = "PelerKuda2026!"
REGION = "SG"  # Singapore (default)

# Gmail untuk terima kode verifikasi
GMAIL_USER = "yayblue3@gmail.com"
GMAIL_APP_PASS = "iueambozpuihslo..."

# Output
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ─── TEMP EMAIL GENERATOR ─────────────────────────────────────
def generate_temp_email():
    """Generate temporary email dari emailnator.com"""
    try:
        # Try emailnator
        r = req.get("https://www.emailnator.com/generate-email", timeout=10)
        if r.status_code == 200:
            data = r.json()
            email = data.get("email", [None])[0]
            if email:
                return email, "emailnator"
    except:
        pass
    
    # Fallback: random prefix + known domain
    prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    domains = [
        "cuaks.fun", "yugi.services", "allegro-looks.com",
        "dhy.cc", "nx.edu.pl", "bca.cx"
    ]
    domain = random.choice(domains)
    return f"{prefix}@{domain}", "random"


def get_email_messages(email, provider="emailnator"):
    """Ambil messages dari temp email"""
    try:
        if provider == "emailnator":
            r = req.post(
                "https://www.emailnator.com/message-list",
                json={"email": email},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if r.status_code == 200:
                return r.json().get("messageData", [])
    except:
        pass
    return []


def extract_verification_code(messages):
    """Extract 6-digit code dari email messages"""
    for msg in messages:
        text = msg.get("messageID", "") + msg.get("subject", "") + msg.get("snippet", "")
        match = re.search(r'\b(\d{6})\b', text)
        if match:
            return match.group(1)
    return None


# ─── MAIN REGISTRATION FLOW ──────────────────────────────────
async def register_account(page, account_num):
    """Register 1 akun Xiaomi Mimo"""
    
    print(f"\n{'='*60}")
    print(f"  ACCOUNT #{account_num}")
    print(f"{'='*60}")
    
    # Generate temp email
    email, provider = generate_temp_email()
    print(f"  Email: {email} ({provider})")
    print(f"  Password: {PASSWORD}")
    
    # Navigate to Mimo login
    await page.goto("https://platform.xiaomimimo.com/login", timeout=30000)
    await page.wait_for_timeout(3000)
    
    # Click Sign up
    print("  [1/7] Clicking Sign up...")
    await page.click("text=Sign up")
    await page.wait_for_timeout(3000)
    
    # Fill form
    print("  [2/7] Filling form...")
    await page.fill("input[name=email]", email)
    await page.fill("input[name=password]", PASSWORD)
    await page.fill("input[name=repassword]", PASSWORD)
    
    # Check agreement
    cb = await page.query_selector("input[type=checkbox]")
    if cb:
        await cb.check()
    await page.wait_for_timeout(500)
    
    # Click Next
    print("  [3/7] Clicking Next...")
    
    # Intercept request
    encrypted_data = {}
    
    async def on_request(request):
        if "sendEmailRegTicket" in request.url:
            encrypted_data["url"] = request.url
            encrypted_data["post_data"] = request.post_data
            encrypted_data["headers"] = dict(request.headers)
            print(f"  [CAPTURED] sendEmailRegTicket intercepted!")
    
    page.on("request", on_request)
    
    await page.click("button:has-text('Next')")
    await page.wait_for_timeout(3000)
    
    # Check for captcha
    frames = page.frames
    captcha_present = any("recaptcha" in f.url for f in frames)
    
    if captcha_present:
        print("  [4/7] reCAPTCHA detected — clicking checkbox...")
        
        # Find reCAPTCHA frame and click checkbox
        for frame in frames:
            if "recaptcha" in frame.url and "anchor" in frame.url:
                try:
                    checkbox = await frame.query_selector("#recaptcha-anchor")
                    if checkbox:
                        await checkbox.click()
                        print("  [4/7] Checkbox clicked!")
                        await page.wait_for_timeout(5000)
                        break
                except Exception as e:
                    print(f"  [4/7] Click error: {e}")
        
        # Check if still on captcha (image challenge appeared)
        await page.wait_for_timeout(2000)
        
        # Take screenshot
        screenshot_path = OUTPUT_DIR / f"captcha_{account_num}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        
        # Check if captcha passed
        current_url = page.url
        if "register" in current_url and "verify" not in current_url:
            print(f"  [4/7] ⚠️ CAPTCHA IMAGE CHALLENGE!")
            print(f"  [4/7] Screenshot saved: {screenshot_path}")
            print(f"  [4/7] SOLVE CAPTCHA MANUALLY IN BROWSER!")
            
            # Wait for manual solve (max 120 seconds)
            print(f"  [4/7] Waiting for captcha solve (max 120s)...")
            for i in range(120):
                await page.wait_for_timeout(1000)
                new_url = page.url
                if "verify" in new_url or "code" in new_url or "bind" in new_url:
                    print(f"  [4/7] ✅ Captcha solved!")
                    break
                if i % 10 == 0 and i > 0:
                    print(f"  [4/7] Still waiting... ({i}s)")
        else:
            print(f"  [4/7] ✅ Captcha auto-passed!")
    else:
        print(f"  [4/7] No captcha — registration progressed!")
    
    # Check current page state
    await page.wait_for_timeout(2000)
    text = await page.inner_text("body")
    print(f"  [5/7] Current page: {text[:100]}")
    
    # Check if we need email verification
    if "code" in text.lower() or "verification" in text.lower() or "verify" in text.lower():
        print(f"  [5/7] Email verification needed!")
        
        # Poll for verification code
        code = None
        for attempt in range(12):  # 60 seconds
            await page.wait_for_timeout(5000)
            messages = get_email_messages(email, provider)
            code = extract_verification_code(messages)
            if code:
                break
            print(f"  [5/7] Waiting for code... ({attempt * 5}s)")
        
        if code:
            print(f"  [5/7] Code received: {code}")
            
            # Fill code
            code_input = await page.query_selector("input[name=code], input[type=tel]")
            if code_input:
                await code_input.fill(code)
                await page.wait_for_timeout(500)
            
            # Click verify button
            verify_btn = await page.query_selector("button:has-text('Verify'), button:has-text('Confirm'), button:has-text('Submit')")
            if verify_btn:
                await verify_btn.click()
                await page.wait_for_timeout(3000)
                print(f"  [5/7] ✅ Code submitted!")
            else:
                print(f"  [5/7] ⚠️ Verify button not found")
        else:
            print(f"  [5/7] ❌ No verification code received!")
            return None
    
    # Check for SSO redirect / API key
    await page.wait_for_timeout(3000)
    current_url = page.url
    print(f"  [6/7] URL after registration: {current_url[:100]}")
    
    # Extract cookies
    cookies = await page.context.cookies()
    api_cookie = None
    for cookie in cookies:
        if "api-platform" in cookie.get("name", ""):
            api_cookie = cookie["value"]
            print(f"  [6/7] ✅ API cookie found: {cookie['name']}={api_cookie[:20]}...")
            break
    
    # Extract API key from page
    api_key = None
    try:
        text = await page.inner_text("body")
        # Look for API key pattern
        match = re.search(r'(tp-[a-zA-Z0-9]+)', text)
        if match:
            api_key = match.group(1)
            print(f"  [6/7] ✅ API key found: {api_key}")
    except:
        pass
    
    # Try to get API key from Mimo console
    if not api_key and api_cookie:
        try:
            # Navigate to Mimo console
            await page.goto("https://platform.xiaomimimo.com/console/apikey", timeout=30000)
            await page.wait_for_timeout(3000)
            
            text = await page.inner_text("body")
            match = re.search(r'(tp-[a-zA-Z0-9]+)', text)
            if match:
                api_key = match.group(1)
                print(f"  [6/7] ✅ API key from console: {api_key}")
        except:
            pass
    
    # Save result
    result = {
        "email": email,
        "password": PASSWORD,
        "api_key": api_key,
        "api_cookie": api_cookie,
        "timestamp": datetime.now().isoformat(),
        "account_num": account_num
    }
    
    # Save to file
    if api_key:
        with open(OUTPUT_DIR / "api_keys.txt", "a") as f:
            f.write(f"{email}|{PASSWORD}|{api_key}\n")
        print(f"  [7/7] ✅ SAVED: {email}|{PASSWORD}|{api_key}")
    else:
        with open(OUTPUT_DIR / "api_keys_pending.txt", "a") as f:
            f.write(f"{email}|{PASSWORD}|NO_KEY\n")
        print(f"  [7/7] ⚠️ SAVED (pending): {email}|{PASSWORD}|NO_KEY")
    
    return result


# ─── MAIN ─────────────────────────────────────────────────────
async def main():
    from playwright.async_api import async_playwright
    
    print("="*60)
    print("  XIAOMI MIMO AUTO-REGISTRATION")
    print("  Windows Edition — Visible Browser")
    print("="*60)
    print(f"  Count: {COUNT}")
    print(f"  Password: {PASSWORD}")
    print(f"  Region: {REGION}")
    print(f"  Output: {OUTPUT_DIR.absolute()}")
    print("="*60)
    
    async with async_playwright() as p:
        # Launch Chrome (visible, non-headless)
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome"  # Use system Chrome
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        )
        
        results = []
        
        for i in range(1, COUNT + 1):
            page = await context.new_page()
            try:
                result = await register_account(page, i)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
            finally:
                await page.close()
            
            # Delay between accounts
            if i < COUNT:
                delay = random.randint(10, 30)
                print(f"\n  Waiting {delay}s before next account...")
                await asyncio.sleep(delay)
        
        await browser.close()
    
    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Total: {COUNT}")
    print(f"  Success: {len([r for r in results if r.get('api_key')])}")
    print(f"  Pending: {len([r for r in results if not r.get('api_key')])}")
    print(f"  Output: {OUTPUT_DIR.absolute()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
