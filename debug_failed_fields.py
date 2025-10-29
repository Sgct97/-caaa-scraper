#!/usr/bin/env python3
"""
Debug the 2 failed fields:
1. keywords_all (s_key_all)
2. posted_by (s_postedby)
"""

from playwright.sync_api import sync_playwright
from search_params import SearchParams

SEARCH_PAGE_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE_PATH = "auth.json"

def debug_field(description, search_params, page):
    """Debug a single field in detail"""
    
    print(f"\n{'='*60}")
    print(f"DEBUGGING: {description}")
    print(f"{'='*60}")
    print(f"Search params: {search_params}")
    print(f"Form data: {search_params.to_form_data()}")
    
    # Navigate
    print("\n→ Step 1: Loading search page...")
    page.goto(SEARCH_PAGE_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    
    form_data = search_params.to_form_data()
    
    # Check if fields exist on the page
    print("\n→ Step 2: Checking if fields exist on page...")
    for field_name in form_data.keys():
        input_exists = page.query_selector(f'input[name="{field_name}"]') is not None
        select_exists = page.query_selector(f'select[name="{field_name}"]') is not None
        
        if input_exists:
            print(f"   ✓ {field_name} exists as INPUT")
            # Check if visible
            is_visible = page.is_visible(f'input[name="{field_name}"]')
            is_enabled = page.is_enabled(f'input[name="{field_name}"]')
            print(f"      - Visible: {is_visible}, Enabled: {is_enabled}")
        elif select_exists:
            print(f"   ✓ {field_name} exists as SELECT")
        else:
            print(f"   ❌ {field_name} NOT FOUND on page!")
    
    # Fill each field
    print("\n→ Step 3: Filling fields...")
    for field_name, field_value in form_data.items():
        print(f"\n   Field: {field_name} = '{field_value}'")
        
        # Try multiple methods
        methods_tried = []
        success = False
        
        # Method 1: Regular fill
        try:
            selector = f'input[name="{field_name}"]'
            if page.query_selector(selector):
                page.fill(selector, str(field_value), timeout=3000, force=True)
                actual_value = page.input_value(selector)
                print(f"      Method 1 (fill): Value set to '{actual_value}'")
                if actual_value == str(field_value):
                    success = True
                methods_tried.append(f"fill: {actual_value}")
        except Exception as e:
            print(f"      Method 1 (fill): Failed - {e}")
            methods_tried.append(f"fill: FAILED")
        
        # Method 2: JavaScript direct set
        if not success:
            try:
                selector = f'input[name="{field_name}"]'
                page.evaluate(f"document.querySelector('{selector}').value = '{field_value}'")
                actual_value = page.input_value(selector)
                print(f"      Method 2 (JS): Value set to '{actual_value}'")
                if actual_value == str(field_value):
                    success = True
                methods_tried.append(f"JS: {actual_value}")
            except Exception as e:
                print(f"      Method 2 (JS): Failed - {e}")
                methods_tried.append(f"JS: FAILED")
        
        # Method 3: Type slowly
        if not success:
            try:
                selector = f'input[name="{field_name}"]'
                page.click(selector)
                page.keyboard.type(str(field_value), delay=100)
                actual_value = page.input_value(selector)
                print(f"      Method 3 (type): Value set to '{actual_value}'")
                if actual_value == str(field_value):
                    success = True
                methods_tried.append(f"type: {actual_value}")
            except Exception as e:
                print(f"      Method 3 (type): Failed - {e}")
                methods_tried.append(f"type: FAILED")
        
        if success:
            print(f"      ✓ SUCCESS")
        else:
            print(f"      ❌ ALL METHODS FAILED")
            print(f"      Methods tried: {methods_tried}")
    
    # Take screenshot before submit
    print("\n→ Step 4: Taking screenshot of filled form...")
    page.screenshot(path=f"debug_{description.replace(' ', '_')}_before.png", full_page=True)
    print(f"   ✓ Saved: debug_{description.replace(' ', '_')}_before.png")
    
    print("\n→ Press ENTER to submit the search...")
    input()
    
    # Submit
    print("\n→ Step 5: Submitting search...")
    page.click('#s_btn')
    page.wait_for_timeout(4000)
    
    # Take screenshot after submit
    page.screenshot(path=f"debug_{description.replace(' ', '_')}_after.png", full_page=True)
    print(f"   ✓ Saved: debug_{description.replace(' ', '_')}_after.png")
    
    # Analyze results
    print("\n→ Step 6: Analyzing results...")
    
    # Check URL
    current_url = page.url
    print(f"   Current URL: {current_url}")
    
    # Look for results
    try:
        page.wait_for_selector("table.table-striped tbody tr", timeout=3000)
        rows = page.query_selector_all("table.table-striped tbody tr")
        result_count = len([r for r in rows if not r.query_selector("b")])
        print(f"   ✓ Found {result_count} results in table")
    except:
        print(f"   ⚠️  No results table found")
    
    # Look for messages
    body_text = page.inner_text("body")
    
    if "messages found" in body_text.lower():
        import re
        match = re.search(r'(\d+,?\d*)\s+messages?\s+found', body_text, re.IGNORECASE)
        if match:
            print(f"   ℹ️  Page says: {match.group(0)}")
    
    if "no results" in body_text.lower() or "0 messages" in body_text.lower():
        print(f"   ℹ️  Search returned 0 results")
    
    # Look for errors
    error_elements = page.query_selector_all(".alert-error, .error, .alert-danger")
    if error_elements:
        for elem in error_elements:
            error_text = elem.inner_text()
            if error_text.strip():
                print(f"   ⚠️  Error found: {error_text}")
    
    print("\n→ Press ENTER to continue to next test...")
    input()


def main():
    with sync_playwright() as p:
        print("\n" + "="*60)
        print("DEBUGGING FAILED FIELDS")
        print("="*60)
        
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(storage_state=STORAGE_STATE_PATH)
        page = context.new_page()
        
        # Debug 1: keywords_all (s_key_all)
        debug_field(
            "keywords_all",
            SearchParams(keywords_all="workers compensation"),
            page
        )
        
        # Debug 2: posted_by (s_postedby)
        debug_field(
            "posted_by",
            SearchParams(posted_by="law"),
            page
        )
        
        print("\n" + "="*60)
        print("DEBUGGING COMPLETE")
        print("="*60)
        print("\nCheck the screenshots and output above to see what went wrong.")
        print("\nPress ENTER to close browser...")
        input()
        
        browser.close()

if __name__ == "__main__":
    main()

