"""
Xiaomi Mimo Auto-Registration v3 — Gmail Dot Trick + IMAP Auto-Poll
Jalankan: py register_windows.py

Flow:
1. Buka Chrome (visible)
2. Generate Gmail dot trick address (all go to yayblue3@gmail.com)
3. Fill form + click Next
4. reCAPTCHA: auto-pass on residential IP, manual on VPS
5. Email code: auto-poll via Gmail IMAP dari VPS helper
   ATAU: manual input dari terminal

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

# Email provider: "outlook" or "gmail"
# "outlook" = random@outlook.com, forwarded to Gmail, poll Gmail IMAP
# "gmail"   = Gmail dot trick (yayblue3+xxx@gmail.com)
EMAIL_PROVIDER = "outlook"

# Gmail (for polling verification codes)
GMAIL_USER = "yayblue3@gmail.com"
GMAIL_APP_PASS = "iueambozpuihsloc"

# Output
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


# ─── OUTLOOK EMAIL GENERATOR ──────────────────────────────────
def generate_outlook_email():
    """
    Generate random Outlook email address: random123@outlook.com
    Email ini akan di-forward ke Gmail via Outlook Forwarding.
    """
    prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    return f"{prefix}@outlook.com"


def generate_email():
    """
    Generate email based on EMAIL_PROVIDER setting.
    Returns (email_address, provider_used)
    """
    if EMAIL_PROVIDER == "outlook":
        return generate_outlook_email(), "outlook"
    else:
        return generate_gmail_address(), "gmail"


# ─── GMAIL DOT TRICK ──────────────────────────────────────────
def generate_gmail_address():
    """
    Generate unique Gmail via dot trick.
    yayblue3@gmail.com → ya.ybl.ue3@gmail.com
    All go to same inbox, but Xiaomi sees different addresses.
    """
    base = "yayblue3"
    # Insert 1-3 dots at random positions (avoid first and last char)
    insert_positions = list(range(1, len(base)))
    num_dots = random.randint(1, min(3, len(insert_positions)))
    positions = sorted(random.sample(insert_positions, num_dots))
    
    dotted = ""
    for i, c in enumerate(base):
        if i in positions:
            dotted += "."
        dotted += c
    return f"{dotted}@gmail.com"


# ─── GMAIL IMAP POLLING ──────────────────────────────────────
def poll_verification_code(max_wait=180):
    """
    Poll Gmail IMAP for Xiaomi verification code.
    Checks every 5 seconds for max_wait seconds.
    Returns 6-digit code or None.
    """
    print("    Polling Gmail IMAP for verification code...")
    
    for attempt in range(max_wait // 5):
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(GMAIL_USER, GMAIL_APP_PASS)
            mail.select("INBOX")
            
            # Search for Xiaomi emails in last 10 minutes
            since = datetime.now().strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(SINCE "{since}" FROM "xiaomi")')
            
            if status == "OK" and messages[0]:
                msg_ids = messages[0].split()
                
                # Check newest first
                for msg_id in reversed(msg_ids[-3:]):
                    status, data = mail.fetch(msg_id, "(RFC822)")
                    if status == "OK":
                        msg = email_lib.message_from_bytes(data[0][1])
                        subject = msg.get("Subject", "")
                        date = msg.get("Date", "")
                        
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                ct = part.get_content_type()
                                if ct in ("text/plain", "text/html"):
                                    body += part.get_payload(decode=True).decode(errors="replace")
                        else:
                            body = msg.get_payload(decode=True).decode(errors="replace")
                        
                        # Extract 6-digit code
                        codes = re.findall(r'\b(\d{6})\b', body)
                        if codes:
                            code = codes[0]  # Take first 6-digit number
                            print(f"    ✅ Code found: {code}")
                            print(f"    Subject: {subject[:60]}")
                            mail.logout()
                            return code
            
            mail.logout()
            
        except Exception as e:
            if attempt % 5 == 0:  # Print error every 25 seconds
                print(f"    Poll attempt {attempt + 1}: {e}")
        
        if attempt < (max_wait // 5) - 1:
            time.sleep(5)
    
    print("    ❌ Code not found within timeout")
    return None


# ─── MAIN REGISTRATION ───────────────────────────────────────
async def register_account(page, account_num):
    """Register 1 Xiaomi Mimo account"""
    
    print(f"\n{'='*60}")
    print(f"  ACCOUNT #{account_num}")
    print(f"{'='*60}")
    
    # Generate email address based on provider setting
    email_addr, provider = generate_email()
    print(f"  Email: {email_addr} ({provider})")
    print(f"  Password: {PASSWORD}")
    
    # Step 1: Navigate to register page
    print("  [1/7] Navigating to Mimo login...")
    await page.goto("https://platform.xiaomimimo.com/login", timeout=30000)
    await page.wait_for_timeout(3000)
    
    # Step 2: Click Sign up
    print("  [2/7] Clicking Sign up...")
    try:
        await page.click("text=Sign up", timeout=10000)
        await page.wait_for_timeout(3000)
    except:
        # Might already be on register page
        current = page.url
        if "register" not in current:
            print(f"  ⚠️ Could not find Sign up button. URL: {current}")
            return None
    
    # Step 3: Fill form
    print("  [3/7] Filling form...")
    try:
        email_input = await page.wait_for_selector("input[name=email], input[type=email]", timeout=5000)
        await email_input.fill(email_addr)
        await page.fill("input[name=password]", PASSWORD)
        await page.fill("input[name=repassword]", PASSWORD)
        
        # Check agreement checkbox
        cb = await page.query_selector("input[type=checkbox]")
        if cb and not await cb.is_checked():
            await cb.check()
        await page.wait_for_timeout(500)
    except Exception as e:
        print(f"  ❌ Form fill error: {e}")
        return None
    
    # Step 4: Click Next
    print("  [4/7] Clicking Next...")
    try:
        await page.click("button:has-text('Next'), button:has-text('Register')", timeout=5000)
        await page.wait_for_timeout(5000)
    except Exception as e:
        print(f"  ❌ Next button error: {e}")
        return None
    
    # Step 5: Handle reCAPTCHA
    print("  [5/7] Handling reCAPTCHA...")
    captcha_solved = False
    
    for frame in page.frames:
        if "recaptcha" in frame.url and "anchor" in frame.url:
            try:
                checkbox = await frame.wait_for_selector("#recaptcha-anchor", timeout=5000)
                if checkbox:
                    await checkbox.click()
                    await page.wait_for_timeout(5000)
                    
                    # Check if passed (green checkmark)
                    classes = await frame.evaluate("() => document.getElementById('recaptcha-anchor').className")
                    if "recaptcha-checkbox-checked" in classes:
                        print("  [5/7] ✅ reCAPTCHA auto-passed!")
                        captcha_solved = True
                    else:
                        print("  [5/7] ⚠️ reCAPTCHA challenge appeared!")
                        print("  [5/7] SOLVE CAPTCHA IN BROWSER, then press Enter here...")
                        await asyncio.get_event_loop().run_in_executor(None, input)
                        captcha_solved = True
            except:
                pass
    
    if not captcha_solved:
        print("  [5/7] No reCAPTCHA found (might not be needed)")
    
    await page.wait_for_timeout(3000)
    
    # Step 6: Email verification code
    body_text = await page.inner_text("body")
    
    if any(kw in body_text.lower() for kw in ["code", "verification", "verify", "captcha"]):
        print("  [6/7] Email verification needed!")
        
        # Check if it's captcha error (first attempt is by design)
        if "captcha" in body_text.lower() or "CAPTCHA" in body_text:
            print("  [6/7] Captcha error (by design, sending email anyway)...")
            
            # Check for verification code input
            code_input = await page.query_selector("input[name=code], input[type=tel], input[placeholder*='code']")
            if code_input:
                # Auto-poll from Gmail
                code = poll_verification_code(max_wait=120)
                
                if not code:
                    print("  [6/7] ❌ Auto-poll failed. Check Gmail manually.")
                    code = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: input("  Enter verification code: ").strip()
                    )
                
                if code and len(code) == 6:
                    await code_input.fill(code)
                    await page.wait_for_timeout(500)
                    
                    btn = await page.query_selector("button:has-text('Verify'), button:has-text('Confirm'), button:has-text('Submit'), button[type=submit]")
                    if btn:
                        await btn.click()
                    else:
                        await page.keyboard.press("Enter")
                    
                    print(f"  [6/7] ✅ Code {code} submitted!")
                    await page.wait_for_timeout(5000)
                else:
                    print(f"  [6/7] ❌ Invalid code!")
                    return None
            else:
                # Maybe it's asking to send email first
                send_btn = await page.query_selector("button:has-text('Send'), button:has-text('Get code')")
                if send_btn:
                    await send_btn.click()
                    await page.wait_for_timeout(3000)
                    
                    # Now poll for code
                    code = poll_verification_code(max_wait=120)
                    if code:
                        code_input = await page.query_selector("input[name=code], input[type=tel]")
                        if code_input:
                            await code_input.fill(code)
                            btn = await page.query_selector("button[type=submit], button:has-text('Verify')")
                            if btn:
                                await btn.click()
                            await page.wait_for_timeout(5000)
                            print(f"  [6/7] ✅ Code {code} submitted!")
    
    # Step 7: Check result
    await page.wait_for_timeout(3000)
    current_url = page.url
    body_text = await page.inner_text("body")
    print(f"  [7/7] URL: {current_url[:100]}")
    
    # Success: redirected to Mimo platform
    if "platform.xiaomimimo.com" in current_url and "login" not in current_url and "register" not in current_url:
        print("  [7/7] ✅ Registration SUCCESS!")
        
        # Get cookies for session
        cookies = await page.context.cookies()
        session_token = None
        for c in cookies:
            if "token" in c["name"].lower() or "session" in c["name"].lower() or "api-platform" in c["name"].lower():
                session_token = c["value"]
                print(f"  [7/7] Cookie: {c['name']}={session_token[:30]}...")
        
        # Try to get API key
        print("  [7/7] Getting API key...")
        try:
            await page.goto("https://platform.xiaomimimo.com/console/apikey", timeout=30000)
            await page.wait_for_timeout(5000)
            
            body_text = await page.inner_text("body")
            
            # Look for API key on page
            api_match = re.search(r'(tp-[a-zA-Z0-9_-]{20,})', body_text)
            if api_match:
                api_key = api_match.group(1)
                print(f"  [7/7] ✅ API KEY: {api_key}")
            else:
                # Try creating new key
                create_btn = await page.query_selector("button:has-text('Create'), button:has-text('New'), button:has-text('Generate'), button:has-text('Create New Key')")
                if create_btn:
                    await create_btn.click()
                    await page.wait_for_timeout(5000)
                    
                    # Check dialog
                    confirm_btn = await page.query_selector("button:has-text('Confirm'), button:has-text('OK'), button:has-text('Yes')")
                    if confirm_btn:
                        await confirm_btn.click()
                        await page.wait_for_timeout(5000)
                    
                    body_text = await page.inner_text("body")
                    api_match = re.search(r'(tp-[a-zA-Z0-9_-]{20,})', body_text)
                    if api_match:
                        api_key = api_match.group(1)
                        print(f"  [7/7] ✅ API KEY: {api_key}")
                    else:
                        api_key = None
                        print(f"  [7/7] ⚠️ API key not found yet. Page: {body_text[:200]}")
                else:
                    api_key = None
                    print(f"  [7/7] ⚠️ No Create button. Page: {body_text[:200]}")
        except Exception as e:
            api_key = None
            print(f"  [7/7] ⚠️ API key extraction error: {e}")
        
        # Save result
        result = {"email": email_addr, "password": PASSWORD, "api_key": api_key, "provider": EMAIL_PROVIDER}
        with open(OUTPUT_DIR / "api_keys.txt", "a") as f:
            f.write(json.dumps(result) + "\n")
        
        return result
    
    elif "success" in body_text.lower():
        print("  [7/7] ✅ Registration completed (no platform redirect)")
        result = {"email": email_addr, "password": PASSWORD, "api_key": None, "provider": EMAIL_PROVIDER}
        with open(OUTPUT_DIR / "api_keys.txt", "a") as f:
            f.write(json.dumps(result) + "\n")
        return result
    
    else:
        print(f"  [7/7] ❌ Unknown state: {body_text[:150]}")
        # Save screenshot for debug
        ss = OUTPUT_DIR / f"debug_{account_num}.png"
        await page.screenshot(path=str(ss))
        print(f"  [7/7] Screenshot: {ss}")
        return None


# ─── MAIN ─────────────────────────────────────────────────────
async def main():
    from playwright.async_api import async_playwright
    
    print("="*60)
    print("  XIAOMI MIMO AUTO-REGISTRATION v4")
    print(f"  Email: {EMAIL_PROVIDER.upper()} + Gmail IMAP Polling")
    print("="*60)
    print(f"  Accounts: {COUNT}")
    print(f"  Gmail (polling): {GMAIL_USER}")
    print(f"  Output: {OUTPUT_DIR.absolute()}")
    print("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
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
                print(f"\n  ❌ FATAL ERROR: {e}")
                import traceback
                traceback.print_exc()
            finally:
                await page.close()
            
            # Delay between accounts (randomize)
            if i < COUNT:
                delay = random.randint(15, 30)
                print(f"\n  ⏳ Waiting {delay}s before next account...")
                await asyncio.sleep(delay)
        
        await browser.close()
    
    # Summary
    success = [r for r in results if r.get("api_key")]
    no_key = [r for r in results if not r.get("api_key")]
    
    print(f"\n{'='*60}")
    print(f"  FINAL RESULTS")
    print(f"{'='*60}")
    print(f"  Total: {COUNT}")
    print(f"  With API Key: {len(success)}")
    print(f"  Registered (no key): {len(no_key)}")
    
    if success:
        print(f"\n  API Keys:")
        for r in success:
            print(f"    {r['email']} | {r['api_key']}")
    
    if no_key:
        print(f"\n  Registered but no key (check manually):")
        for r in no_key:
            print(f"    {r['email']} | {r['password']}")
    
    print(f"\n  All results saved to: {OUTPUT_DIR / 'api_keys.txt'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
