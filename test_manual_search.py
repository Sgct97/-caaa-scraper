#!/usr/bin/env python3
"""
Quick test to verify we can:
1. Load the search page
2. See the search form (confirms we're logged in)
3. Submit a simple search
4. Get results
"""

from playwright.sync_api import sync_playwright
import time

def test_search():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Show browser
        context = browser.new_context(storage_state="auth.json")
        page = context.new_page()
        
        try:
            print("1. Loading search page...")
            page.goto("https://www.caaa.org/?pg=search&bid=3305", timeout=60000)
            page.wait_for_timeout(3000)
            
            print("2. Checking if logged in...")
            # Check for search button
            if page.locator("#s_btn").count() > 0:
                print("   ✓ Logged in! Search form visible.")
            else:
                print("   ✗ NOT logged in - no search button found")
                page.screenshot(path="not_logged_in.png")
                input("Press Enter to close...")
                return
            
            print("3. Searching for 'medical' in Any Keywords field...")
            # Fill the "any keywords" field
            page.fill('input[name="s_key_one"]', 'medical')
            page.wait_for_timeout(1000)
            
            print("4. Submitting search...")
            page.click("#s_btn")
            page.wait_for_timeout(5000)
            
            print("5. Checking for results...")
            # Take screenshot
            page.screenshot(path="search_results.png")
            
            # Check what we got
            if page.locator("table.table-striped tbody tr").count() > 0:
                count = page.locator("table.table-striped tbody tr").count()
                print(f"   ✓ Found {count} result rows!")
            elif page.locator(".s_rnfne").count() > 0:
                print("   ⚠️  'No results' message found")
            else:
                print("   ⚠️  Unknown result page state")
                print(f"   Page title: {page.title()}")
                print(f"   URL: {page.url}")
            
            print("\nScreenshot saved as 'search_results.png'")
            input("Press Enter to close browser...")
            
        finally:
            browser.close()

if __name__ == "__main__":
    test_search()

