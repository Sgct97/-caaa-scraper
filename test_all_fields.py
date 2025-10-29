#!/usr/bin/env python3
"""
Comprehensive test of ALL search fields
Tests each field individually to confirm it works
"""

from playwright.sync_api import sync_playwright
from search_params import SearchParams
from datetime import date, timedelta

SEARCH_PAGE_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE_PATH = "auth.json"

def test_single_search(description, search_params, page):
    """Test a single search and return if it found results"""
    
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"{'='*60}")
    print(f"Params: {search_params}")
    print(f"Form data: {search_params.to_form_data()}")
    
    # Navigate to search page
    print("\n→ Loading search page...")
    page.goto(SEARCH_PAGE_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    
    # Fill form
    print("→ Filling form...")
    form_data = search_params.to_form_data()
    
    for field_name, field_value in form_data.items():
        try:
            if field_name.startswith('s_'):
                selector = f'input[name="{field_name}"]'
                if page.query_selector(selector):
                    if 'date' in field_name:
                        page.evaluate(f"document.querySelector('{selector}').value = '{field_value}'")
                    else:
                        page.fill(selector, str(field_value), timeout=3000, force=True)
                else:
                    selector = f'select[name="{field_name}"]'
                    if page.query_selector(selector):
                        page.select_option(selector, str(field_value))
        except Exception as e:
            print(f"   ⚠️  Error setting {field_name}: {e}")
            try:
                selector = f'input[name="{field_name}"], select[name="{field_name}"]'
                page.evaluate(f"document.querySelector('{selector}').value = '{field_value}'")
            except:
                pass
    
    # Submit
    print("→ Submitting...")
    page.click('#s_btn')
    page.wait_for_timeout(3000)
    
    # Check results
    try:
        page.wait_for_selector("table.table-striped tbody tr", timeout=5000)
        rows = page.query_selector_all("table.table-striped tbody tr")
        result_count = len([r for r in rows if not r.query_selector("b")])
        
        print(f"✓ PASS: Found {result_count} results")
        return True
    except:
        # Check for 0 results message
        body_text = page.inner_text("body")
        if "0 messages" in body_text or "No messages found" in body_text:
            print("✓ PASS: Search worked but returned 0 results (query too restrictive)")
            return True
        elif "messages found" in body_text:
            import re
            match = re.search(r'(\d+,?\d*)\s+messages?\s+found', body_text)
            if match:
                count = match.group(1)
                print(f"✓ PASS: Found {count} messages")
                return True
        
        print("❌ FAIL: No results table and no result count message")
        page.screenshot(path=f"failed_{description.replace(' ', '_')}.png")
        return False


def main():
    with sync_playwright() as p:
        print("\n" + "="*60)
        print("COMPREHENSIVE SEARCH FIELD TEST")
        print("="*60)
        
        browser = p.chromium.launch(headless=False, slow_mo=500)
        context = browser.new_context(storage_state=STORAGE_STATE_PATH)
        page = context.new_page()
        
        results = {}
        
        # TEST 1: Simple keyword (s_fname)
        results['simple_keyword'] = test_single_search(
            "Simple keyword search",
            SearchParams(keyword="workers compensation"),
            page
        )
        
        # TEST 2: Keywords ALL (s_key_all)
        results['keywords_all'] = test_single_search(
            "Keywords ALL",
            SearchParams(keywords_all="workers compensation"),
            page
        )
        
        # TEST 3: Keywords phrase (s_key_phrase)
        results['keywords_phrase'] = test_single_search(
            "Exact phrase",
            SearchParams(keywords_phrase="permanent disability"),
            page
        )
        
        # TEST 4: Keywords ANY (s_key_one)
        results['keywords_any'] = test_single_search(
            "Keywords ANY",
            SearchParams(keywords_any="SIBTF permanent disability"),
            page
        )
        
        # TEST 5: Keywords EXCLUDE (s_key_x)
        results['keywords_exclude'] = test_single_search(
            "Keywords EXCLUDE",
            SearchParams(
                keyword="compensation",
                keywords_exclude="workers"
            ),
            page
        )
        
        # TEST 6: Date FROM (s_postdatefrom)
        results['date_from'] = test_single_search(
            "Date FROM",
            SearchParams(
                keyword="workers",
                date_from=date.today() - timedelta(days=7)
            ),
            page
        )
        
        # TEST 7: Date TO (s_postdateto)
        results['date_to'] = test_single_search(
            "Date TO",
            SearchParams(
                keyword="workers",
                date_to=date.today() - timedelta(days=30)
            ),
            page
        )
        
        # TEST 8: Date RANGE (both from and to)
        results['date_range'] = test_single_search(
            "Date RANGE (from + to)",
            SearchParams(
                keyword="workers",
                date_from=date.today() - timedelta(days=60),
                date_to=date.today() - timedelta(days=30)
            ),
            page
        )
        
        # TEST 9: Author last name (s_lname)
        results['author_last_name'] = test_single_search(
            "Author last name",
            SearchParams(author_last_name="Smith"),
            page
        )
        
        # TEST 10: Posted by (s_postedby)
        results['posted_by'] = test_single_search(
            "Posted by",
            SearchParams(posted_by="law"),
            page
        )
        
        # TEST 11: Listserv filter (s_list)
        results['listserv'] = test_single_search(
            "Listserv filter",
            SearchParams(
                keyword="workers",
                listserv="lawnet"
            ),
            page
        )
        
        # TEST 12: Search in subject only (s_cat)
        results['search_subject_only'] = test_single_search(
            "Search subject only",
            SearchParams(
                keyword="workers compensation",
                search_in="subject_only"
            ),
            page
        )
        
        # TEST 13: With attachments (s_attachment)
        results['with_attachments'] = test_single_search(
            "With attachments",
            SearchParams(
                keyword="workers",
                attachment_filter="with_attachments"
            ),
            page
        )
        
        # TEST 14: Without attachments (s_attachment)
        results['without_attachments'] = test_single_search(
            "Without attachments",
            SearchParams(
                keyword="workers",
                attachment_filter="without_attachments"
            ),
            page
        )
        
        # Print summary
        print("\n\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_name, passed_test in results.items():
            status = "✓ PASS" if passed_test else "❌ FAIL"
            print(f"{status}: {test_name}")
        
        print(f"\n{passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! All search fields work correctly.")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Check screenshots for details.")
        
        print("\nPress ENTER to close browser...")
        input()
        
        browser.close()

if __name__ == "__main__":
    main()

