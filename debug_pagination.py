#!/usr/bin/env python3
"""
Debug script to examine pagination structure on results page
"""

from playwright.sync_api import sync_playwright
import json

def debug_pagination():
    """Examine the pagination structure on a results page"""
    
    print("\n" + "="*60)
    print("CAAA Pagination Debugging")
    print("="*60 + "\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state="auth.json")
        page = context.new_page()
        
        # Navigate to search page
        print("→ Navigating to search page...")
        page.goto("https://www.caaa.org/?pg=search&bid=3305", timeout=60000)
        page.wait_for_timeout(2000)
        
        # Fill in a simple keyword search that will have many results
        print("→ Filling search form with 'medical'...")
        page.fill('input[name="s_text"]', 'medical')
        
        # Submit search
        print("→ Submitting search...")
        page.click('#s_btn')
        page.wait_for_timeout(5000)
        
        print(f"✓ Current URL: {page.url}\n")
        
        # Count results on first page
        rows = page.query_selector_all("table.table-striped tbody tr")
        message_count = 0
        for row in rows:
            if not row.query_selector("b"):  # Skip header rows
                cells = row.query_selector_all("td")
                if len(cells) >= 5:
                    message_count += 1
        
        print(f"✓ Found {message_count} messages on page 1\n")
        
        # Look for pagination elements with various selectors
        print("="*60)
        print("PAGINATION ELEMENT SEARCH")
        print("="*60 + "\n")
        
        # Try different pagination selectors
        selectors_to_try = [
            "#seachResultsPaginationBar",  # Current (typo)
            "#searchResultsPaginationBar",  # Corrected
            "[id*='pagination']",  # Any element with 'pagination' in ID
            "[class*='pagination']",  # Any element with 'pagination' in class
            ".pagination",  # Common class name
            "nav[role='navigation']",  # Semantic navigation
            "ul.pagination",  # Bootstrap style
        ]
        
        for selector in selectors_to_try:
            try:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"✓ Found {len(elements)} element(s) with selector: {selector}")
                    for i, elem in enumerate(elements):
                        if elem.is_visible():
                            print(f"  Element {i+1}: VISIBLE")
                            # Get HTML of pagination element
                            html = elem.inner_html()
                            print(f"  HTML preview: {html[:200]}...")
                        else:
                            print(f"  Element {i+1}: HIDDEN")
                else:
                    print(f"✗ No elements found with selector: {selector}")
            except Exception as e:
                print(f"✗ Error with selector {selector}: {e}")
        
        print("\n" + "="*60)
        print("LOOKING FOR PAGE LINKS")
        print("="*60 + "\n")
        
        # Look for links that might be pagination
        all_links = page.query_selector_all("a")
        pagination_candidates = []
        
        for link in all_links:
            try:
                text = link.inner_text().strip()
                href = link.get_attribute("href") or ""
                onclick = link.get_attribute("onclick") or ""
                title = link.get_attribute("title") or ""
                
                # Look for numeric page links, "Next", ">", etc.
                if (text.isdigit() or 
                    text.lower() in ['next', 'previous', 'prev', '>', '<', '>>', '<<'] or
                    'next' in title.lower() or 
                    'prev' in title.lower()):
                    
                    is_visible = link.is_visible()
                    pagination_candidates.append({
                        'text': text,
                        'href': href,
                        'onclick': onclick,
                        'title': title,
                        'visible': is_visible
                    })
            except Exception as e:
                pass  # Skip links that cause errors
        
        print(f"Found {len(pagination_candidates)} potential pagination links:\n")
        for i, candidate in enumerate(pagination_candidates[:20], 1):  # Show first 20
            print(f"{i}. Text: '{candidate['text']}' | Title: '{candidate['title']}' | Visible: {candidate['visible']}")
            if candidate['href']:
                print(f"   href: {candidate['href'][:100]}")
            if candidate['onclick']:
                print(f"   onclick: {candidate['onclick'][:100]}")
            print()
        
        # Save full page HTML for inspection
        print("="*60)
        print("SAVING DEBUG FILES")
        print("="*60 + "\n")
        
        page.screenshot(path="pagination_debug.png")
        print("✓ Screenshot saved: pagination_debug.png")
        
        html_content = page.content()
        with open("pagination_debug.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("✓ HTML saved: pagination_debug.html")
        
        # Save pagination data
        debug_data = {
            'url': page.url,
            'message_count_page1': message_count,
            'pagination_candidates': pagination_candidates
        }
        
        with open("pagination_debug.json", "w", encoding="utf-8") as f:
            json.dump(debug_data, f, indent=2)
        print("✓ Debug data saved: pagination_debug.json")
        
        print("\n" + "="*60)
        print("Now let's try clicking 'Next' or '2'...")
        print("="*60 + "\n")
        
        # Try to click page 2 or next
        clicked = False
        
        # Strategy 1: Try clicking visible link with text "2"
        for link in all_links:
            try:
                if link.inner_text().strip() == "2" and link.is_visible():
                    print("→ Trying to click link with text '2'...")
                    link.click()
                    clicked = True
                    break
            except:
                pass
        
        if clicked:
            page.wait_for_timeout(5000)
            print(f"✓ Clicked! New URL: {page.url}")
            
            # Count messages on page 2
            rows = page.query_selector_all("table.table-striped tbody tr")
            page2_count = 0
            for row in rows:
                if not row.query_selector("b"):
                    cells = row.query_selector_all("td")
                    if len(cells) >= 5:
                        page2_count += 1
            
            print(f"✓ Found {page2_count} messages on page 2")
        else:
            print("✗ Could not click to page 2")
        
        print("\n" + "="*60)
        print("DEBUGGING COMPLETE")
        print("="*60)
        
        browser.close()

if __name__ == "__main__":
    debug_pagination()

