#!/usr/bin/env python3
"""
Test SearchParams with a real search on CAAA
This validates that our form data structure works correctly
"""

from playwright.sync_api import sync_playwright
from search_params import SearchParams
from datetime import date, timedelta

SEARCH_PAGE_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE_PATH = "auth.json"

def test_search(search_params: SearchParams):
    """Test a search with the given parameters"""
    
    print("="*60)
    print("Testing Search Parameters")
    print("="*60)
    print(f"\nSearch: {search_params}")
    print(f"\nForm data: {search_params.to_form_data()}")
    print()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=STORAGE_STATE_PATH)
        page = context.new_page()
        
        # Navigate to search page
        print("→ Navigating to search page...")
        page.goto(SEARCH_PAGE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        
        # Fill form using SearchParams
        print("→ Filling form with SearchParams.to_form_data()...")
        form_data = search_params.to_form_data()
        
        for field_name, field_value in form_data.items():
            print(f"   Setting {field_name} = '{field_value}'")
            
            try:
                # Handle text inputs
                if field_name.startswith('s_'):
                    selector = f'input[name="{field_name}"]'
                    if page.query_selector(selector):
                        # For date fields with calendar widgets, use JavaScript to set value directly
                        if 'date' in field_name:
                            page.evaluate(f"document.querySelector('{selector}').value = '{field_value}'")
                            print(f"      ✓ Set via JavaScript (date field)")
                        else:
                            # Use force and timeout for problematic fields
                            page.fill(selector, str(field_value), timeout=5000, force=True)
                            print(f"      ✓ Set via fill")
                    else:
                        # Try select dropdown
                        selector = f'select[name="{field_name}"]'
                        if page.query_selector(selector):
                            page.select_option(selector, str(field_value))
                            print(f"      ✓ Set via select")
            except Exception as e:
                print(f"      ⚠️  Could not set field: {e}")
                # Try JavaScript as fallback
                try:
                    selector = f'input[name="{field_name}"], select[name="{field_name}"]'
                    page.evaluate(f"document.querySelector('{selector}').value = '{field_value}'")
                    print(f"      ✓ Set via JavaScript fallback")
                except:
                    print(f"      ❌ Failed to set field, skipping")
        
        # Submit search
        print("\n→ Submitting search...")
        page.click('#s_btn')
        
        # Wait for results
        print("→ Waiting for results...")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except:
            page.wait_for_timeout(3000)
        
        # Check if we got results
        try:
            page.wait_for_selector("table.table-striped tbody tr", timeout=5000)
            
            # Count results
            rows = page.query_selector_all("table.table-striped tbody tr")
            # Subtract 1 for header row
            result_count = len([r for r in rows if not r.query_selector("b")])
            
            print(f"\n✓ SUCCESS! Found {result_count} results on first page")
            
            # Get pagination info
            pagination = page.query_selector("#seachResultsPaginationBar")
            if pagination:
                pagination_text = pagination.inner_text()
                if "Page" in pagination_text:
                    print(f"✓ Pagination: {pagination_text.split('Page')[1].strip().split()[0]}")
            
            # Show first few results
            print("\n📋 First 3 results:")
            for i, row in enumerate(rows[:4]):
                if row.query_selector("b"):
                    continue  # Skip header
                cells = row.query_selector_all("td")
                if len(cells) >= 5:
                    date = cells[0].inner_text().strip()
                    from_field = cells[1].inner_text().strip()
                    subject = cells[4].inner_text().strip()
                    print(f"  {i+1}. {date} - {subject[:50]}...")
            
        except Exception as e:
            print(f"\n⚠️  No results found or error: {e}")
            # Take screenshot for debugging
            page.screenshot(path="search_error.png")
            print("   Screenshot saved: search_error.png")
        
        print("\n→ Press ENTER to close browser...")
        input()
        
        browser.close()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("SEARCH PARAMS TEST SUITE")
    print("="*60 + "\n")
    
    # Test 1: Simple keyword search
    print("TEST 1: Simple keyword search")
    print("-" * 60)
    search1 = SearchParams(keyword="workers compensation")
    test_search(search1)
    
    print("\n\n")
    input("Press ENTER to run Test 2...")
    
    # Test 2: Advanced search with date range and exclusions
    print("TEST 2: Advanced search with filters")
    print("-" * 60)
    search2 = SearchParams(
        keywords_all="workers compensation",
        keywords_exclude="defense",
        listserv="lawnet",
        date_from=date.today() - timedelta(days=30)
    )
    test_search(search2)
    
    print("\n\n")
    input("Press ENTER to run Test 3...")
    
    # Test 3: Exact phrase search
    print("TEST 3: Exact phrase search")
    print("-" * 60)
    search3 = SearchParams(
        keywords_phrase="permanent disability",
        listserv="lawnet"
    )
    test_search(search3)
    
    print("\n\n✅ All tests complete!")

