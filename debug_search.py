#!/usr/bin/env python3
"""
Debug script to see exactly what happens during search
"""

from playwright.sync_api import sync_playwright
from search_params import SearchParams

SEARCH_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE = "auth.json"

# Create search params - just simple keyword
search_params = SearchParams(
    keyword="workers compensation",
    max_messages=5,
    max_pages=1
)

print("\n" + "="*60)
print("DEBUG: Search Form Submission")
print("="*60)
print(f"Search params: {search_params}")
print(f"Form data: {search_params.to_form_data()}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(storage_state=STORAGE_STATE)
    page = context.new_page()
    
    # Navigate to search page
    print("\n→ Navigating to search page...")
    page.goto(SEARCH_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    
    # Fill form
    print("\n→ Filling form with keyword: 'workers compensation'")
    page.fill('input[name="s_fname"]', "workers compensation")
    page.wait_for_timeout(1000)
    
    # Take screenshot before submit
    page.screenshot(path="debug_before_submit.png")
    print("✓ Screenshot saved: debug_before_submit.png")
    
    # Submit
    print("\n→ Clicking submit button...")
    page.click('#s_btn')
    page.wait_for_timeout(3000)
    
    # Take screenshot after submit
    page.screenshot(path="debug_after_submit.png")
    print("✓ Screenshot saved: debug_after_submit.png")
    
    # Check for results table
    print("\n→ Checking for results...")
    results_table = page.query_selector("table.table-striped tbody")
    
    if results_table:
        rows = results_table.query_selector_all("tr")
        print(f"✓ Found results table with {len(rows)} rows")
        
        # Show first result
        if len(rows) > 0:
            first_row = rows[0]
            cells = first_row.query_selector_all("td")
            print(f"\nFirst result:")
            for i, cell in enumerate(cells):
                print(f"  Column {i}: {cell.inner_text()[:50]}")
    else:
        print("❌ No results table found")
        
        # Check if there's an error message
        error = page.query_selector(".alert-danger, .error")
        if error:
            print(f"⚠️  Error message: {error.inner_text()}")
        
        # Save HTML for debugging
        html = page.content()
        with open("debug_results_page.html", "w") as f:
            f.write(html)
        print("✓ Saved HTML: debug_results_page.html")
    
    browser.close()

print("\n✓ Debug complete")

