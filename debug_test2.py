#!/usr/bin/env python3
"""
DEBUG: Test 2 - Advanced search with filters
Run SLOWLY so we can see what's happening
"""

from playwright.sync_api import sync_playwright
from search_params import SearchParams
from datetime import date, timedelta

SEARCH_PAGE_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE_PATH = "auth.json"

def debug_test2():
    """Debug Test 2 with slow execution and detailed logging"""
    
    # Create search params for Test 2
    search_params = SearchParams(
        keywords_all="workers compensation",
        keywords_exclude="defense",
        listserv="lawnet",
        date_from=date.today() - timedelta(days=30)
    )
    
    print("="*60)
    print("DEBUG TEST 2: Advanced Search")
    print("="*60)
    print(f"\nSearch Parameters:")
    print(f"  - keywords_all: 'workers compensation'")
    print(f"  - keywords_exclude: 'defense'")
    print(f"  - listserv: 'lawnet'")
    print(f"  - date_from: {search_params.date_from}")
    print(f"\nForm Data: {search_params.to_form_data()}")
    print()
    
    with sync_playwright() as p:
        # Launch with slow_mo for visibility
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context(storage_state=STORAGE_STATE_PATH)
        page = context.new_page()
        
        # Navigate
        print("→ Step 1: Navigating to search page...")
        page.goto(SEARCH_PAGE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        print("   ✓ Loaded")
        
        # Fill each field one by one with pauses
        form_data = search_params.to_form_data()
        
        print("\n→ Step 2: Filling form fields...")
        
        # Field 1: Date from
        if 's_postdatefrom' in form_data:
            print(f"\n   Field 1: s_postdatefrom = '{form_data['s_postdatefrom']}'")
            try:
                page.evaluate(f"document.querySelector('input[name=\"s_postdatefrom\"]').value = '{form_data['s_postdatefrom']}'")
                print("      ✓ Set via JavaScript")
                page.wait_for_timeout(1000)
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        # Field 2: Keywords ALL
        if 's_key_all' in form_data:
            print(f"\n   Field 2: s_key_all = '{form_data['s_key_all']}'")
            try:
                page.fill('input[name="s_key_all"]', form_data['s_key_all'], timeout=5000)
                print("      ✓ Set via fill")
                page.wait_for_timeout(1000)
            except Exception as e:
                print(f"      ⚠️  Fill failed: {e}")
                print("      Trying JavaScript...")
                try:
                    page.evaluate(f"document.querySelector('input[name=\"s_key_all\"]').value = '{form_data['s_key_all']}'")
                    print("      ✓ Set via JavaScript")
                except Exception as e2:
                    print(f"      ❌ JS also failed: {e2}")
        
        # Field 3: Keywords EXCLUDE
        if 's_key_x' in form_data:
            print(f"\n   Field 3: s_key_x = '{form_data['s_key_x']}'")
            try:
                page.fill('input[name="s_key_x"]', form_data['s_key_x'], timeout=5000)
                print("      ✓ Set via fill")
                page.wait_for_timeout(1000)
            except Exception as e:
                print(f"      ⚠️  Fill failed: {e}")
                print("      Trying JavaScript...")
                try:
                    page.evaluate(f"document.querySelector('input[name=\"s_key_x\"]').value = '{form_data['s_key_x']}'")
                    print("      ✓ Set via JavaScript")
                except Exception as e2:
                    print(f"      ❌ JS also failed: {e2}")
        
        # Field 4: Listserv
        if 's_list' in form_data:
            print(f"\n   Field 4: s_list = '{form_data['s_list']}'")
            try:
                page.select_option('select[name="s_list"]', form_data['s_list'])
                print("      ✓ Set via select")
                page.wait_for_timeout(1000)
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        # Take screenshot of filled form BEFORE submitting
        print("\n→ Step 3: Taking screenshot of filled form...")
        page.screenshot(path="test2_before_submit.png", full_page=True)
        print("   ✓ Screenshot saved: test2_before_submit.png")
        
        print("\n→ Step 4: Form is filled. Check the VNC window!")
        print("   Press ENTER to submit the search...")
        input()
        
        # Submit
        print("\n→ Step 5: Submitting search...")
        page.click('#s_btn')
        print("   ✓ Clicked search button")
        
        # Wait and watch what happens
        print("\n→ Step 6: Waiting for response...")
        page.wait_for_timeout(5000)
        
        # Take screenshot after submit
        page.screenshot(path="test2_after_submit.png", full_page=True)
        print("   ✓ Screenshot saved: test2_after_submit.png")
        
        # Check for results
        print("\n→ Step 7: Checking for results...")
        
        # Look for error messages
        error_selectors = [
            ".alert-error",
            ".error",
            "div:has-text('No results')",
            "div:has-text('0 messages')"
        ]
        
        for selector in error_selectors:
            element = page.query_selector(selector)
            if element:
                print(f"   ⚠️  Found error/message: {element.inner_text()[:100]}")
        
        # Look for results table
        try:
            page.wait_for_selector("table.table-striped tbody tr", timeout=3000)
            rows = page.query_selector_all("table.table-striped tbody tr")
            result_count = len([r for r in rows if not r.query_selector("b")])
            print(f"\n   ✓ Found {result_count} results!")
            
            # Show first few
            print("\n   First 3 results:")
            for i, row in enumerate(rows[:4]):
                if row.query_selector("b"):
                    continue
                cells = row.query_selector_all("td")
                if len(cells) >= 5:
                    subject = cells[4].inner_text().strip()
                    print(f"     {i+1}. {subject[:60]}...")
        except:
            print("\n   ⚠️  No results table found")
            
            # Check current URL
            current_url = page.url
            print(f"\n   Current URL: {current_url}")
            
            # Get page text content
            body_text = page.inner_text("body")
            if "0 messages" in body_text or "No results" in body_text:
                print("\n   ℹ️  Search returned 0 results (too restrictive)")
            elif "messages found" in body_text:
                # Find the count
                import re
                match = re.search(r'(\d+,?\d*)\s+messages?\s+found', body_text)
                if match:
                    print(f"\n   ℹ️  Found: {match.group(1)} messages")
        
        print("\n\n→ Press ENTER to close browser...")
        input()
        
        browser.close()

if __name__ == "__main__":
    debug_test2()

