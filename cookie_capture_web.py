#!/usr/bin/env python3
"""
Web-based Cookie capture script for CAAA login
Logs everything to a file for debugging
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

# Setup logging FIRST - both file and console
LOG_FILE = '/srv/caaa_scraper/cookie_capture.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('cookie_capture')

# Log startup
logger.info('='*60)
logger.info('COOKIE CAPTURE STARTED')
logger.info(f'Working directory: {os.getcwd()}')
logger.info(f'Script path: {os.path.abspath(__file__)}')
logger.info(f'DISPLAY env: {os.environ.get("DISPLAY", "NOT SET")}')
logger.info('='*60)

# Change to script directory
os.chdir('/srv/caaa_scraper')
logger.info(f'Changed to directory: {os.getcwd()}')

from playwright.sync_api import sync_playwright
from cryptography.fernet import Fernet

# Configuration
LOGIN_URL = 'https://www.caaa.org/?pg=login'
STORAGE_STATE_PATH = '/srv/caaa_scraper/auth.json'
ENCRYPTED_STATE_PATH = '/srv/caaa_scraper/auth.json.enc'
KEY_PATH = '/srv/caaa_scraper/.auth_key'
STATUS_FILE = '/srv/caaa_scraper/cookie_status.json'

def update_status(status, message, details=None):
    """Update status file for web interface to read"""
    data = {
        'status': status,
        'message': message,
        'details': details,
        'timestamp': datetime.now().isoformat()
    }
    with open(STATUS_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f'STATUS: {status} - {message}')

def generate_or_load_key():
    logger.info(f'Loading/generating encryption key from: {KEY_PATH}')
    if Path(KEY_PATH).exists():
        with open(KEY_PATH, 'rb') as f:
            key = f.read()
        logger.info('Loaded existing encryption key')
        return key
    else:
        key = Fernet.generate_key()
        with open(KEY_PATH, 'wb') as f:
            f.write(key)
        os.chmod(KEY_PATH, 0o600)
        logger.info('Generated NEW encryption key')
        return key

def encrypt_storage_state(key):
    logger.info(f'Encrypting storage state: {STORAGE_STATE_PATH} -> {ENCRYPTED_STATE_PATH}')
    cipher = Fernet(key)
    with open(STORAGE_STATE_PATH, 'rb') as f:
        plaintext = f.read()
    logger.info(f'Read {len(plaintext)} bytes from plaintext auth.json')
    
    encrypted = cipher.encrypt(plaintext)
    
    with open(ENCRYPTED_STATE_PATH, 'wb') as f:
        f.write(encrypted)
    logger.info(f'Wrote {len(encrypted)} bytes to encrypted file')
    
    # Backup instead of delete
    backup_path = f'{STORAGE_STATE_PATH}.backup'
    os.rename(STORAGE_STATE_PATH, backup_path)
    logger.info(f'Moved plaintext to backup: {backup_path}')

def launch_browser_for_login():
    """Launch browser and wait for login completion signal"""
    update_status('launching', 'Launching browser for login...')
    
    try:
        with sync_playwright() as p:
            logger.info('Starting Chromium browser (headless=False)')
            browser = p.chromium.launch(
                headless=False,
                slow_mo=100,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )
            logger.info('Browser launched successfully')
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/Los_Angeles',
            )
            logger.info('Browser context created')
            
            page = context.new_page()
            logger.info(f'Navigating to: {LOGIN_URL}')
            page.goto(LOGIN_URL, wait_until='domcontentloaded', timeout=30000)
            logger.info(f'Page loaded. Current URL: {page.url}')
            
            update_status('waiting_login', 'Browser open - waiting for user to log in', {
                'url': page.url,
                'instruction': 'Log in via VNC, then click Complete Login button'
            })
            
            # Poll for completion signal file
            SIGNAL_FILE = '/srv/caaa_scraper/login_complete.signal'
            logger.info(f'Waiting for completion signal: {SIGNAL_FILE}')
            
            timeout = 600  # 10 minutes max
            start = time.time()
            while time.time() - start < timeout:
                if os.path.exists(SIGNAL_FILE):
                    logger.info('Completion signal received!')
                    os.remove(SIGNAL_FILE)
                    break
                time.sleep(2)  # Check every 2 seconds
            else:
                logger.error('TIMEOUT waiting for login completion')
                update_status('error', 'Timeout waiting for login', {'timeout_seconds': timeout})
                browser.close()
                return False
            
            # User says they're logged in - capture cookies
            time.sleep(2)  # Give page time to settle
            current_url = page.url
            logger.info(f'After login signal - Current URL: {current_url}')
            
            # Take screenshot for debugging
            screenshot_path = '/srv/caaa_scraper/login_screenshot.png'
            try:
                page.screenshot(path=screenshot_path)
                logger.info(f'Screenshot saved to: {screenshot_path}')
            except Exception as e:
                logger.warning(f'Could not save screenshot: {e}')
            
            # Save storage state
            logger.info(f'Saving storage state to: {STORAGE_STATE_PATH}')
            context.storage_state(path=STORAGE_STATE_PATH)
            
            # Verify what was saved
            with open(STORAGE_STATE_PATH, 'r') as f:
                state = json.load(f)
            cookie_count = len(state.get('cookies', []))
            origin_count = len(state.get('origins', []))
            logger.info(f'Captured {cookie_count} cookies, {origin_count} origins')
            
            # Log cookie details (names only, not values)
            for cookie in state.get('cookies', []):
                logger.info(f'  Cookie: {cookie.get("name")} domain={cookie.get("domain")} expires={cookie.get("expires", "session")}')
            
            # Validate auth cookies exist
            cookie_names = [c.get('name') for c in state.get('cookies', [])]
            has_mcidme = 'mcidme' in cookie_names
            auth_valid = has_mcidme
            
            browser.close()
            logger.info('Browser closed')
            
            if not auth_valid:
                logger.warning('WARNING: mcidme auth cookie NOT found - login may have failed!')
                update_status('warning', 'Auth cookie missing - login may not have succeeded', {
                    'url': current_url,
                    'missing_cookie': 'mcidme',
                    'cookie_count': cookie_count,
                    'screenshot': screenshot_path
                })
                return False  # Don't proceed with restart if auth failed
            
            if cookie_count == 0:
                logger.warning('WARNING: No cookies captured!')
                update_status('warning', 'Login captured but 0 cookies found', {'url': current_url})
                return False
            
            update_status('captured', f'Captured {cookie_count} cookies', {
                'cookie_count': cookie_count,
                'url': current_url
            })
            return True
            
    except Exception as e:
        logger.exception(f'Browser error: {e}')
        update_status('error', f'Browser error: {str(e)}')
        return False

def restart_persistent_browser():
    """Restart the persistent browser service"""
    import subprocess
    
    logger.info('Restarting persistent browser service...')
    update_status('restarting', 'Restarting browser service with new cookies')
    
    try:
        # First decrypt the cookies so persistent browser can use them
        logger.info('Decrypting cookies for persistent browser...')
        key = generate_or_load_key()
        
        if Path(ENCRYPTED_STATE_PATH).exists():
            cipher = Fernet(key)
            with open(ENCRYPTED_STATE_PATH, 'rb') as f:
                encrypted = f.read()
            plaintext = cipher.decrypt(encrypted)
            with open(STORAGE_STATE_PATH, 'wb') as f:
                f.write(plaintext)
            logger.info(f'Decrypted cookies to: {STORAGE_STATE_PATH}')
        
        # Restart service
        result = subprocess.run(['systemctl', 'restart', 'caaa-browser'], 
                               capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f'Service start failed: {result.stderr}')
            update_status('error', f'Service start failed: {result.stderr}')
            return False
        
        logger.info('Persistent browser service started')
        
        # Wait a moment and check status
        time.sleep(3)
        result = subprocess.run(['systemctl', 'is-active', 'caaa-browser'],
                               capture_output=True, text=True)
        service_status = result.stdout.strip()
        logger.info(f'Service status: {service_status}')
        
        if service_status == 'active':
            update_status('complete', 'Cookie refresh complete - service running', {
                'service_status': service_status
            })
            return True
        else:
            update_status('warning', f'Service not active: {service_status}')
            return False
            
    except Exception as e:
        logger.exception(f'Service restart error: {e}')
        update_status('error', f'Service restart failed: {str(e)}')
        return False

def main():
    logger.info('Starting cookie capture flow')
    update_status('starting', 'Cookie capture process starting')
    
    # Step 1: Launch browser for login
    if not launch_browser_for_login():
        logger.error('Browser login failed')
        return
    
    # Step 2: Encrypt cookies
    logger.info('Encrypting captured cookies')
    update_status('encrypting', 'Encrypting cookies for secure storage')
    try:
        key = generate_or_load_key()
        encrypt_storage_state(key)
        logger.info('Cookies encrypted successfully')
    except Exception as e:
        logger.exception(f'Encryption failed: {e}')
        update_status('error', f'Encryption failed: {str(e)}')
        return
    
    # Step 3: Restart persistent browser
    restart_persistent_browser()
    
    logger.info('='*60)
    logger.info('COOKIE CAPTURE COMPLETED')
    logger.info('='*60)

if __name__ == '__main__':
    main()
