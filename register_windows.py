"""
Xiaomi Mimo Auto-Registration — Windows Edition v2
Jalankan di laptop Windows: py register_windows.py

Strategy: Gmail dot trick + auto IMAP polling
- Generate unique Gmail (y.a.y.b.l.u.e.3@gmail.com etc)
- All dot variations go to same inbox
- Poll verification code via Gmail IMAP (from VPS script)
- Fallback: manual code input

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
import imaplib
import email as email_lib
from pathlib import Path
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────
COUNT = 10
PASSWORD = "PelerKuda2026!"
REGION = "SG"

# Gmail (dot trick — all dots go to same inbox)
GMAIL_USER = "yayblue3@gmail.com"
GMAIL_APP_PASS = "iueambozpuihsloc"  # App Password IMAP

# Output
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


# ─── GMAIL DOT TRICK ──────────────────────────────────────────
def generate_gmail_address():
    """
    Generate unique Gmail via dot trick.
    yayblue3@gmail.com → ya.ybl.ue3@gmail.com
    All go to same inbox, but Xiaomi sees different addresses.
    """
    base = "yayblue3"
    # Insert 1-3 dots at random positions
    positions = sorted(random.sample(range(1, len(base)), random.randint(1, 3)))
    dotted = ""
    for i, c in enumerate(base):
        if i in positions:
            dotted += "."
        dotted += c
    return f"{dotted}@gmail.com"


# ─── GMAIL IMAP POLLING ──────────────────────────────────────
def poll_verification_code(expected_email=None, max_wait=120):
    """
    Poll Gmail IMAP for Xiaomi verification code.
    Checks inbox for new messages from Xiaomi.
    """
    print("    Polling Gmail for verification code...")
    
    for attempt in range(max_wait // 5):
        try:
            # Connect to Gmail IMAP
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(GMAIL_USER, GMAIL_APP_PASS)
            mail.select("INBOX")
            
            # Search for recent Xiaomi emails (last 5 min)
            since = datetime.now().strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(SINCE "{since}" FROM "xiaomi")')
            
            if status == "OK":
                msg_ids = messages[0].split()
                
                for msg_id in reversed(msg_ids[-5:]):  # Check last 5
                    status, data = mail.fetch(msg_id, "(RFC822)")
                    if status == "OK":
                        msg = email_lib.message_from_bytes(data[0][1])
                        body = ""
                        
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body += part.get_payload(decode=True).decode(errors="replace")
                                elif part.get_content_type() == "text/html":
                                    body += part.get_payload(decode=True).decode(errors="replace")
                        else:
                            body = msg.get_payload(decode=True).decode(errors="replace")
                        
                        # Extract 6-digit code
                        match = re.search(r'\b(\d{6})\b', body)
                        if match:
                            code = match.group(1)
                            subject = msg.get("Subject", "")
                            print(f"    ✅ Code found: {code}")
                            print(f"    Subject: {subject[:80]}")
                            mail.logout()
                            return code
            
            mail.logout()
            
        except Exception as e:
            print(f"    Poll attempt {attempt + 1}: {e}")
        
        if attempt < (max_wait // 5) - 1:
            print(f"    Waiting... (attempt {attempt + 1}/{max_wait // 5})")
            time.sleep(5)
    
    return None


# ─── MAIN REGISTRATION FLOW ──────────────────────────────────
async def register_account(page, account_num):
    """Register 1 akun Xiaomi Mimo"""
    
    print(f"\n{'='*60}")
    print(f"  ACCOUNT #{account_num}")
    print(f"{'='*60}")
    
    # Generate Gmail address (dot trick)
    email_addr = generate_gmail_address()
    print(f"  Email: {email_addr}")
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
    await page.fill("input[name=email]", email_addr)
    await page.fill("input[name=password]", PASSWORD)
    await page.fill("input[name=repassword]", PASSWORD)
    
    # Check agreement checkbox
    cb = await page.query_selector("input[type=checkbox]")
    if cb:
        await cb.check()
    await page.wait_for_timeout(500)
    
    # Click Next
    print("  [3/7] Clicking Next...")
    await page.click("button:has-text('Next')")
    await page.wait_for_timeout(3000)
    
    # Handle reCAPTCHA if present
    frames = page.frames
    captcha_handled = False
    for frame in frames:
        if "recaptcha" in frame.url and "anchor" in frame.url:
            print("  [4/7] reCAPTCHA detected — clicking checkbox...")
            try:
                checkbox = await frame.query_selector("#recaptcha-anchor")
                if checkbox:
                    await checkbox.click()
                    await page.wait_for_timeout(5000)
                    captcha_handled = True
                    print("  [4/7] ✅ reCAPTCHA clicked!")
            except Exception as e:
                print(f"  [4/7] reCAPTCHA error: {e}")
    
    if not captcha_handled:
        print("  [4/7] No reCAPTCHA or auto-passed")
    
    await page.wait_for_timeout(3000)
    
    # Check for captcha image challenge
    current_url = page.url
    body_text = await page.inner_text("body")
    
    # If still on registration page with captcha challenge
    if "captcha" in body_text.lower() or "challenge" in body_text.lower():
        print("  ⚠️ IMAGE CAPTCHA DETECTED!")
        screenshot_path = OUTPUT_DIR / f"captcha_{account_num}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"  Screenshot: {screenshot_path}")
        print("  SOLVE CAPTCHA DI BROWSER, lalu tekan ENTER di terminal ini...")
        
        # Wait for manual solve
        await asyncio.get_event_loop().run_in_executor(None, input)
        await page.wait_for_timeout(3000)
    
    # Check if email verification is needed
    body_text = await page.inner_text("body")
    
    if "code" in body_text.lower() or "verification" in body_text.lower() or "verify" in body_text.lower():
        print("  [5/7] Email verification needed!")
        
        # Try auto-poll first
        code = poll_verification_code(email_addr, max_wait=60)
        
        if not code:
            # Fallback: manual input
            print("  [5/7] ❌ Auto-poll failed!")
            print("  [5/7] Check email manually at: https://mail.google.com")
            print(f"  [5/7] Search for emails to: {email_addr}")
            code = input("  [5/7] Enter verification code: ").strip()
        
        if code and len(code) == 6:
            print(f"  [5/7] Entering code: {code}")
            
            # Find code input field
            code_input = await page.query_selector("input[name=code], input[type=tel], input[placeholder*='code']")
            if code_input:
                await code_input.fill(code)
                await page.wait_for_timeout(500)
            else:
                # Try clicking individual digit inputs
                digits = list(code)
                inputs = await page.query_selector_all("input[type=tel], input[maxlength='1']")
                for i, inp in enumerate(inputs):
                    if i < len(digits):
                        await inp.fill(digits[i])
                        await page.wait_for_timeout(100)
            
            # Click verify/submit button
            btn = await page.query_selector("button:has-text('Verify'), button:has-text('Confirm'), button:has-text('Submit'), button:has-text('Sign up')")
            if btn:
                await btn.click()
                print("  [5/7] ✅ Code submitted!")
            else:
                await page.keyboard.press("Enter")
                print("  [5/7] ✅ Enter pressed!")
            
            await page.wait_for_timeout(5000)
        else:
            print(f"  [5/7] ❌ Invalid code!")
            return None
    
    # Check registration result
    await page.wait_for_timeout(3000)
    body_text = await page.inner_text("body")
    current_url = page.url
    
    print(f"  [6/7] Current URL: {current_url[:100]}")
    print(f"  [6/7] Page text: {body_text[:150]}")
    
    # Check if redirected to Mimo platform (success)
    if "platform.xiaomimimo.com" in current_url and "register" not in current_url:
        print("  [6/7] ✅ Registration successful! Redirected to Mimo platform!")
        
        # Extract cookies
        cookies = await page.context.cookies()
        api_cookie = None
        for cookie in cookies:
            if "api-platform" in cookie.get("name", "") or "token" in cookie.get("name", ""):
                api_cookie = cookie["value"]
                print(f"  [6/7] Cookie: {cookie['name']}={api_cookie[:30]}...")
        
        # Navigate to API key page
        print("  [6/7] Navigating to API key page...")
        await page.goto("https://platform.xiaomimimo.com/console/apikey", timeout=30000)
        await page.wait_for_timeout(5000)
        
        # Try to create API key
        try:
            create_btn = await page.query_selector("button:has-text('Create'), button:has-text('New'), button:has-text('Generate')")
            if create_btn:
                await create_btn.click()
                await page.wait_for_timeout(3000)
        except:
            pass
        
        # Extract API key from page
        body_text = await page.inner_text("body")
        api_match = re.search(r'(tp-[a-zA-Z0-9]+)', body_text)
        if api_match:
            api_key = api_match.group(1)
            print(f"  [7/7] ✅ API KEY: {api_key}")
            
            # Save to file
            with open(OUTPUT_DIR / "api_keys.txt", "a") as f:
                f.write(f"{email_addr}|{PASSWORD}|{api_key}\n")
            
            return {"email": email_addr, "password": PASSWORD, "api_key": api_key}
        else:
            print(f"  [7/7] ⚠️ API key not found on page")
            print(f"  [7/7] Page text: {body_text[:300]}")
            
            with open(OUTPUT_DIR / "api_keys_pending.txt", "a") as f:
                f.write(f"{email_addr}|{PASSWORD}|NO_KEY_YET\n")
            
            return {"email": email_addr, "password": PASSWORD, "api_key": None}
    
    elif "success" in body_text.lower() or "complete" in body_text.lower():
        print("  [6/7] ✅ Registration completed!")
        return {"email": email_addr, "password": PASSWORD, "api_key": None}
    
    else:
        print(f"  [6/7] ❌ Unknown state")
        screenshot_path = OUTPUT_DIR / f"result_{account_num}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"  [6/7] Screenshot: {screenshot_path}")
        return None


# ─── MAIN ─────────────────────────────────────────────────────
async def main():
    from playwright.async_api import async_playwright
    
    print("="*60)
    print("  XIAOMI MIMO AUTO-REGISTRATION v2")
    print("  Gmail Dot Trick + Auto IMAP Polling")
    print("="*60)
    print(f"  Count: {COUNT}")
    print(f"  Gmail: {GMAIL_USER}")
    print(f"  Password: {PASSWORD}")
    print(f"  Output: {OUTPUT_DIR.absolute()}")
    print("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
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
                    print(f"\n  ✅ Account #{i} done!")
                else:
                    print(f"\n  ❌ Account #{i} failed!")
            except Exception as e:
                print(f"\n  ❌ ERROR: {e}")
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
    success = [r for r in results if r.get("api_key")]
    pending = [r for r in results if not r.get("api_key")]
    print(f"  Total: {COUNT}")
    print(f"  With API Key: {len(success)}")
    print(f"  Pending: {len(pending)}")
    
    if success:
        print(f"\n  API Keys:")
        for r in success:
            print(f"    {r['email']} | {r['api_key']}")
    
    print(f"\n  Output: {OUTPUT_DIR.absolute()}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
