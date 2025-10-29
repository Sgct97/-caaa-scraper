#!/usr/bin/env python3
"""
SUPER SLOW test of s_key_all field so we can watch it
"""

from playwright.sync_api import sync_playwright

SEARCH_PAGE_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE_PATH = "auth.json"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=2000)
        context = browser.new_context(storage_state=STORAGE_STATE_PATH)
        page = context.new_page()
        
        print("="*60)
        print("WATCHING s_key_all FIELD")
        print("="*60)
        
        print("\n→ Step 1: Loading search page...")
        page.goto(SEARCH_PAGE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        
        print("\n→ Step 2: Locating s_key_all field...")
        field = page.query_selector('input[name="s_key_all"]')
        
        if field:
            print("   ✓ Field found")
            print(f"   - Visible: {field.is_visible()}")
            print(f"   - Enabled: {field.is_enabled()}")
            
            # Get all attributes
            print("\n   Field attributes:")
            for attr in ['id', 'class', 'style', 'type', 'placeholder']:
                value = field.get_attribute(attr)
                if value:
                    print(f"     - {attr}: {value}")
            
            # Check parent elements
            print("\n   Checking parent visibility...")
            parent = page.evaluate("""
                (element) => {
                    let parent = element.parentElement;
                    let parents = [];
                    while (parent && parents.length < 5) {
                        parents.push({
                            tag: parent.tagName,
                            id: parent.id,
                            class: parent.className,
                            style: parent.getAttribute('style'),
                            display: window.getComputedStyle(parent).display,
                            visibility: window.getComputedStyle(parent).visibility
                        });
                        parent = parent.parentElement;
                    }
                    return parents;
                }
            """, field)
            
            for i, p_info in enumerate(parent):
                print(f"\n   Parent {i+1}: <{p_info['tag']}>")
                if p_info['id']:
                    print(f"     - id: {p_info['id']}")
                if p_info['class']:
                    print(f"     - class: {p_info['class']}")
                print(f"     - display: {p_info['display']}")
                print(f"     - visibility: {p_info['visibility']}")
        else:
            print("   ❌ Field NOT found!")
        
        print("\n→ Step 3: Scroll to field and highlight it...")
        page.evaluate("""
            (selector) => {
                const element = document.querySelector(selector);
                if (element) {
                    element.scrollIntoView({behavior: 'smooth', block: 'center'});
                    element.style.border = '5px solid red';
                    element.style.backgroundColor = 'yellow';
                }
            }
        """, 'input[name="s_key_all"]')
        
        print("   Look at the VNC window - do you see a yellow highlighted field?")
        print("\n→ Press ENTER to try filling it...")
        input()
        
        print("\n→ Step 4: Attempting to fill field with JavaScript...")
        page.evaluate("""
            document.querySelector('input[name="s_key_all"]').value = 'workers compensation';
        """)
        
        actual_value = page.input_value('input[name="s_key_all"]')
        print(f"   Value after JS: '{actual_value}'")
        
        print("\n→ Press ENTER to try clicking and typing...")
        input()
        
        print("\n→ Step 5: Clearing and trying click + type...")
        page.evaluate("""
            document.querySelector('input[name="s_key_all"]').value = '';
        """)
        
        # Try to click it
        try:
            page.click('input[name="s_key_all"]', force=True, timeout=5000)
            print("   ✓ Clicked field")
        except Exception as e:
            print(f"   ⚠️  Could not click: {e}")
        
        # Type
        try:
            page.keyboard.type("workers compensation", delay=200)
            actual_value = page.input_value('input[name="s_key_all"]')
            print(f"   Value after typing: '{actual_value}'")
        except Exception as e:
            print(f"   ⚠️  Could not type: {e}")
        
        print("\n→ Step 6: Check if value is actually in the field...")
        final_value = page.evaluate("""
            document.querySelector('input[name="s_key_all"]').value
        """)
        print(f"   Final value via JS: '{final_value}'")
        
        print("\n→ Taking screenshot...")
        page.screenshot(path="watch_key_all.png", full_page=True)
        print("   ✓ Saved: watch_key_all.png")
        
        print("\n→ Press ENTER to submit and see what happens...")
        input()
        
        print("\n→ Step 7: Submitting form...")
        page.click('#s_btn')
        page.wait_for_timeout(5000)
        
        # Check result
        current_url = page.url
        print(f"\n   Current URL: {current_url}")
        
        body_text = page.inner_text("body")
        
        if "Search using at least one criteria" in body_text:
            print("\n   ❌ Form validation error: Search using at least one criteria")
            print("   → This means the field value was NOT recognized by the form")
        elif "messages found" in body_text.lower():
            print("\n   ✓ Search worked! Results found.")
        else:
            print("\n   ⚠️  Unknown result")
        
        page.screenshot(path="watch_key_all_result.png", full_page=True)
        print("   ✓ Saved: watch_key_all_result.png")
        
        print("\n→ Press ENTER to close...")
        input()
        
        browser.close()

if __name__ == "__main__":
    main()

