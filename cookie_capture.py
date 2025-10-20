#!/usr/bin/env python3
"""
Cookie capture script for CAAA login
Captures authenticated session via Playwright and encrypts the storage state
"""

import os
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from cryptography.fernet import Fernet

# Configuration
LOGIN_URL = "https://www.caaa.org/?pg=login"
STORAGE_STATE_PATH = "auth.json"
ENCRYPTED_STATE_PATH = "auth.json.enc"
KEY_PATH = ".auth_key"

# Create keys directory if it doesn't exist
Path(".").mkdir(exist_ok=True)


def generate_or_load_key():
    """Generate a new encryption key or load existing one"""
    if Path(KEY_PATH).exists():
        with open(KEY_PATH, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as f:
            f.write(key)
        os.chmod(KEY_PATH, 0o600)  # Read/write for owner only
        print(f"✓ Generated new encryption key: {KEY_PATH}")
        return key


def encrypt_storage_state(key):
    """Encrypt the auth.json file"""
    cipher = Fernet(key)
    with open(STORAGE_STATE_PATH, "rb") as f:
        plaintext = f.read()
    
    encrypted = cipher.encrypt(plaintext)
    
    with open(ENCRYPTED_STATE_PATH, "wb") as f:
        f.write(encrypted)
    
    # Delete plaintext
    os.remove(STORAGE_STATE_PATH)
    print(f"✓ Encrypted storage state saved to: {ENCRYPTED_STATE_PATH}")
    print(f"✓ Deleted plaintext: {STORAGE_STATE_PATH}")


def decrypt_storage_state(key):
    """Decrypt auth.json.enc to auth.json for use"""
    if not Path(ENCRYPTED_STATE_PATH).exists():
        raise FileNotFoundError(f"Encrypted state not found: {ENCRYPTED_STATE_PATH}")
    
    cipher = Fernet(key)
    with open(ENCRYPTED_STATE_PATH, "rb") as f:
        encrypted = f.read()
    
    plaintext = cipher.decrypt(encrypted)
    
    with open(STORAGE_STATE_PATH, "wb") as f:
        f.write(plaintext)
    
    print(f"✓ Decrypted storage state to: {STORAGE_STATE_PATH}")


def capture_cookies():
    """
    Interactive cookie capture - client logs in manually while we watch
    """
    print("\n" + "="*60)
    print("CAAA Cookie Capture - Interactive Mode")
    print("="*60)
    print("\nInstructions:")
    print("1. A browser window will open to the CAAA login page")
    print("2. CLIENT: Please log in with your credentials")
    print("3. CLIENT: Complete any MFA/CAPTCHA if prompted")
    print("4. CLIENT: Wait until you see your dashboard/member portal")
    print("5. DEV: Press ENTER in this terminal once login is complete")
    print("\nStarting browser in 3 seconds...\n")
    
    import time
    time.sleep(3)
    
    with sync_playwright() as p:
        # Launch visible browser for manual login
        browser = p.chromium.launch(
            headless=False,
            slow_mo=100,  # Slightly slower for human interaction
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )
        
        # Create context with realistic settings
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/Los_Angeles',
            # Add proxy here if needed:
            # proxy={'server': 'http://proxy-url:port', 'username': 'user', 'password': 'pass'}
        )
        
        page = context.new_page()
        
        # Navigate to login
        print(f"→ Navigating to: {LOGIN_URL}")
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        
        # Wait for user to complete login
        input("\n⏸  Press ENTER after you've successfully logged in and see your dashboard...\n")
        
        # Give page a moment to settle
        time.sleep(2)
        
        # Verify we're logged in by checking URL changed or specific element exists
        current_url = page.url
        print(f"✓ Current URL: {current_url}")
        
        if current_url == LOGIN_URL:
            print("⚠  WARNING: Still on login page. Login may have failed.")
            confirm = input("Continue anyway? (y/n): ")
            if confirm.lower() != 'y':
                browser.close()
                return False
        
        # Save storage state (cookies + localStorage)
        context.storage_state(path=STORAGE_STATE_PATH)
        print(f"✓ Saved storage state to: {STORAGE_STATE_PATH}")
        
        # Show captured cookies summary
        with open(STORAGE_STATE_PATH, 'r') as f:
            state = json.load(f)
            cookie_count = len(state.get('cookies', []))
            print(f"✓ Captured {cookie_count} cookies")
        
        browser.close()
        return True


def verify_cookies():
    """
    Test that captured cookies work by loading the site again
    """
    print("\n" + "="*60)
    print("Verifying Captured Cookies")
    print("="*60 + "\n")
    
    if not Path(STORAGE_STATE_PATH).exists():
        print("✗ No storage state found. Run capture first.")
        return False
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        
        # Load the saved storage state
        context = browser.new_context(
            storage_state=STORAGE_STATE_PATH,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/Los_Angeles',
        )
        
        page = context.new_page()
        
        # Navigate to a protected page (not login page)
        # Adjust this URL to a page that should show authenticated content
        test_url = "https://www.caaa.org/"
        print(f"→ Testing cookies by visiting: {test_url}")
        page.goto(test_url, wait_until="domcontentloaded")
        
        import time
        time.sleep(3)
        
        current_url = page.url
        print(f"✓ Current URL: {current_url}")
        
        # Check if we got redirected back to login
        if "login" in current_url.lower():
            print("✗ FAILED: Redirected to login. Cookies may be invalid.")
            browser.close()
            return False
        
        print("✓ SUCCESS: Cookies appear valid (no redirect to login)")
        input("\nCheck the browser window - do you see authenticated content? Press ENTER to close...")
        
        browser.close()
        return True


def main():
    """Main flow: capture → verify → encrypt"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "decrypt":
            # Decrypt for use (e.g., by scraper)
            key = generate_or_load_key()
            decrypt_storage_state(key)
            print("✓ Ready for use")
            return
        
        elif command == "verify":
            # Just verify existing cookies
            if not Path(STORAGE_STATE_PATH).exists():
                print("✗ No auth.json found. Checking for encrypted version...")
                if Path(ENCRYPTED_STATE_PATH).exists():
                    key = generate_or_load_key()
                    decrypt_storage_state(key)
            verify_cookies()
            return
    
    # Default: full capture flow
    print("\n🔐 CAAA Cookie Capture Tool")
    print("This tool will help you securely capture login cookies\n")
    
    # Step 1: Capture
    success = capture_cookies()
    if not success:
        print("\n✗ Cookie capture failed or cancelled")
        return
    
    # Step 2: Verify
    print("\n→ Now verifying the captured cookies...")
    import time
    time.sleep(2)
    
    verified = verify_cookies()
    if not verified:
        print("\n⚠  Verification failed. You may need to capture again.")
        return
    
    # Step 3: Encrypt
    print("\n→ Encrypting storage state for secure storage...")
    key = generate_or_load_key()
    encrypt_storage_state(key)
    
    print("\n" + "="*60)
    print("✓ COMPLETE - Cookie Capture Successful")
    print("="*60)
    print(f"\nSecure files created:")
    print(f"  • {ENCRYPTED_STATE_PATH} (encrypted cookies)")
    print(f"  • {KEY_PATH} (encryption key - keep secret!)")
    print(f"\n⚠  IMPORTANT: Add these to .gitignore:")
    print(f"  {ENCRYPTED_STATE_PATH}")
    print(f"  {KEY_PATH}")
    print(f"  {STORAGE_STATE_PATH}")
    print("\nTo use cookies in your scraper:")
    print(f"  1. Run: python cookie_capture.py decrypt")
    print(f"  2. Load storage_state='{STORAGE_STATE_PATH}' in Playwright")


if __name__ == "__main__":
    main()

