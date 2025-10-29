#!/usr/bin/env python3
"""
Reconnaissance script to perform a test search and capture results page structure
"""

from playwright.sync_api import sync_playwright
import json
import time

SEARCH_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE_PATH = "auth.json"

def recon_results_page():
    """Fill search form, submit, and capture results page structure"""
    
    print("\n" + "="*60)
    print("CAAA Results Page Reconnaissance")
    print("="*60 + "\n")
    
    # Get search term from user
    search_name = input("Enter a name to search for (first or last): ").strip()
    if not search_name:
        search_name = "Smith"  # Default test
        print(f"Using default search: {search_name}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        
        context = browser.new_context(
            storage_state=STORAGE_STATE_PATH,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        )
        
        page = context.new_page()
        
        # Navigate to search page
        print(f"\n→ Navigating to search page...")
        page.goto(SEARCH_URL, wait_until="networkidle")
        time.sleep(1)
        
        # Fill in the search form (just last name for simplicity)
        print(f"→ Filling search form with: {search_name}")
        page.fill('#s_lname', search_name)
        
        # Take screenshot of filled form
        page.screenshot(path="search_form_filled.png")
        print("✓ Screenshot of filled form: search_form_filled.png")
        
        # Submit the form
        print("→ Submitting search...")
        page.click('#s_btn')
        
        # Wait for results to load
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        results_url = page.url
        print(f"✓ Results URL: {results_url}\n")
        
        # Capture results page
        print("="*60)
        print("RESULTS PAGE STRUCTURE")
        print("="*60)
        
        # Check if there are results or "no results" message
        page_text = page.inner_text('body')
        
        if 'no results' in page_text.lower() or 'not found' in page_text.lower():
            print("\n⚠️  No results found. Try a different search term.")
            print("   Capturing page anyway for structure...\n")
        
        # Look for result items (common patterns)
        print("\n→ Looking for result patterns...\n")
        
        # Try to find result containers
        result_patterns = [
            'div.result',
            'div.search-result',
            'tr',  # Table rows
            'li',  # List items
            'article',
            '[class*="result"]',
            '[class*="item"]',
            '[class*="post"]',
            '[class*="message"]',
        ]
        
        found_results = []
        for pattern in result_patterns:
            try:
                elements = page.locator(pattern).all()
                if len(elements) > 0:
                    print(f"Found {len(elements)} elements matching: {pattern}")
                    found_results.append({
                        'selector': pattern,
                        'count': len(elements)
                    })
            except:
                pass
        
        # Look for pagination
        print("\n" + "="*60)
        print("PAGINATION")
        print("="*60 + "\n")
        
        pagination_patterns = [
            'a[href*="page"]',
            'a[href*="pg="]',
            'button:has-text("Next")',
            'a:has-text("Next")',
            'a:has-text(">")',
            '[class*="pag"]',
            '[class*="next"]',
            '[class*="prev"]',
        ]
        
        pagination_found = []
        for pattern in pagination_patterns:
            try:
                elements = page.locator(pattern).all()
                if len(elements) > 0:
                    print(f"Found pagination: {pattern} ({len(elements)} elements)")
                    for i, elem in enumerate(elements[:5]):  # Show first 5
                        try:
                            text = elem.inner_text() or elem.get_attribute('href') or ''
                            print(f"  - {text}")
                        except:
                            pass
                    pagination_found.append({
                        'selector': pattern,
                        'count': len(elements)
                    })
            except:
                pass
        
        # Look for links to individual posts
        print("\n" + "="*60)
        print("POST LINKS")
        print("="*60 + "\n")
        
        all_links = page.locator('a[href*="pg="]').all()
        post_links = []
        
        print(f"Found {len(all_links)} links with 'pg=' in href")
        print("Sample links (first 10):")
        
        for i, link in enumerate(all_links[:10]):
            try:
                href = link.get_attribute('href') or ''
                text = link.inner_text()[:50] or '(no text)'
                print(f"  {i+1}. {text} -> {href}")
                post_links.append({
                    'text': text,
                    'href': href
                })
            except:
                pass
        
        # Capture tables (common for result lists)
        print("\n" + "="*60)
        print("TABLES")
        print("="*60 + "\n")
        
        tables = page.locator('table').all()
        table_data = []
        
        for i, table in enumerate(tables):
            try:
                rows = table.locator('tr').all()
                headers = table.locator('th').all()
                
                header_texts = []
                for h in headers:
                    try:
                        header_texts.append(h.inner_text())
                    except:
                        pass
                
                print(f"Table {i+1}:")
                print(f"  Rows: {len(rows)}")
                print(f"  Headers: {header_texts}")
                
                table_data.append({
                    'index': i,
                    'row_count': len(rows),
                    'headers': header_texts
                })
            except:
                pass
        
        # Take screenshot of results
        print("\n" + "="*60)
        print("CAPTURING RESULTS PAGE")
        print("="*60 + "\n")
        
        page.screenshot(path="results_page_screenshot.png", full_page=True)
        print("✓ Screenshot: results_page_screenshot.png")
        
        # Save HTML
        html_content = page.content()
        with open("results_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("✓ HTML: results_page.html")
        
        # Save recon data
        recon_data = {
            'search_term': search_name,
            'results_url': results_url,
            'result_patterns': found_results,
            'pagination': pagination_found,
            'post_links': post_links,
            'tables': table_data
        }
        
        with open("results_page_recon.json", "w", encoding="utf-8") as f:
            json.dump(recon_data, f, indent=2)
        print("✓ Recon data: results_page_recon.json")
        
        print("\n" + "="*60)
        print("RESULTS RECONNAISSANCE COMPLETE")
        print("="*60)
        print("\nReview the screenshot and HTML to see the actual structure.")
        print("Press ENTER to close browser...")
        input()
        
        browser.close()


if __name__ == "__main__":
    recon_results_page()

