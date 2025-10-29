#!/usr/bin/env python3
"""
Check if there's an "Advanced Search" toggle we need to click
"""

from playwright.sync_api import sync_playwright

SEARCH_PAGE_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE_PATH = "auth.json"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context(storage_state=STORAGE_STATE_PATH)
        page = context.new_page()
        
        print("→ Loading search page...")
        page.goto(SEARCH_PAGE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        
        print("\n→ Looking for Advanced Search toggle/link...")
        
        # Look for common patterns
        possible_toggles = [
            "text='Advanced'",
            "text='Advanced Search'",
            "text='Show Advanced'",
            "text='More Options'",
            "text='More Search Options'",
            "a:has-text('Advanced')",
            "button:has-text('Advanced')",
            "div:has-text('Advanced')",
            "#advancedSearch",
            ".advanced-search",
            "[id*='advanced']",
            "[class*='advanced']"
        ]
        
        for selector in possible_toggles:
            try:
                element = page.query_selector(selector)
                if element:
                    text = element.inner_text() if element else ""
                    print(f"\n✓ Found: {selector}")
                    print(f"  Text: {text}")
                    print(f"  Visible: {element.is_visible()}")
                    
                    # Try clicking it
                    print(f"\n→ Trying to click it...")
                    element.click()
                    page.wait_for_timeout(1000)
                    
                    # Check if s_key_all is now visible
                    key_all_visible = page.is_visible('input[name="s_key_all"]')
                    print(f"  s_key_all visible after click: {key_all_visible}")
                    
                    break
            except:
                pass
        else:
            print("\n⚠️  No advanced search toggle found with common patterns")
        
        # Check all hidden fields
        print("\n→ Checking all hidden input fields...")
        hidden_inputs = page.query_selector_all('input[type="text"]:not([style*="display: none"])')
        
        for inp in hidden_inputs:
            name = inp.get_attribute("name")
            visible = inp.is_visible()
            if name and name.startswith('s_'):
                print(f"  {name}: Visible={visible}")
        
        # Take screenshot
        page.screenshot(path="advanced_search_check.png", full_page=True)
        print("\n✓ Screenshot saved: advanced_search_check.png")
        
        print("\n→ Press ENTER to close...")
        input()
        
        browser.close()

if __name__ == "__main__":
    main()

