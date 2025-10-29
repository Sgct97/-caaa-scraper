#!/usr/bin/env python3
"""
Show ALL form fields on the search page
"""

from playwright.sync_api import sync_playwright

SEARCH_PAGE_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE_PATH = "auth.json"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=STORAGE_STATE_PATH)
        page = context.new_page()
        
        print("="*60)
        print("ALL FORM FIELDS ON SEARCH PAGE")
        print("="*60)
        
        page.goto(SEARCH_PAGE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        
        # Get all input fields
        print("\n📋 ALL INPUT FIELDS:")
        print("-" * 60)
        
        inputs = page.query_selector_all('input[type="text"], input:not([type])')
        for i, inp in enumerate(inputs):
            name = inp.get_attribute("name") or "(no name)"
            id_attr = inp.get_attribute("id") or "(no id)"
            visible = inp.is_visible()
            placeholder = inp.get_attribute("placeholder") or ""
            
            print(f"\nInput {i+1}:")
            print(f"  name: {name}")
            print(f"  id: {id_attr}")
            print(f"  visible: {visible}")
            if placeholder:
                print(f"  placeholder: {placeholder}")
        
        # Get all select/dropdowns
        print("\n\n📋 ALL SELECT/DROPDOWN FIELDS:")
        print("-" * 60)
        
        selects = page.query_selector_all('select')
        for i, sel in enumerate(selects):
            name = sel.get_attribute("name") or "(no name)"
            id_attr = sel.get_attribute("id") or "(no id)"
            visible = sel.is_visible()
            
            print(f"\nSelect {i+1}:")
            print(f"  name: {name}")
            print(f"  id: {id_attr}")
            print(f"  visible: {visible}")
        
        # Get all textareas
        print("\n\n📋 ALL TEXTAREA FIELDS:")
        print("-" * 60)
        
        textareas = page.query_selector_all('textarea')
        for i, ta in enumerate(textareas):
            name = ta.get_attribute("name") or "(no name)"
            id_attr = ta.get_attribute("id") or "(no id)"
            visible = ta.is_visible()
            
            print(f"\nTextarea {i+1}:")
            print(f"  name: {name}")
            print(f"  id: {id_attr}")
            print(f"  visible: {visible}")
        
        # Look specifically for the keyword fields
        print("\n\n🔍 LOOKING FOR KEYWORD FIELDS:")
        print("-" * 60)
        
        keyword_fields = ['s_fname', 's_key_all', 's_key_phrase', 's_key_one', 's_key_x']
        
        for field_name in keyword_fields:
            exists = page.query_selector(f'input[name="{field_name}"]') is not None
            if exists:
                visible = page.is_visible(f'input[name="{field_name}"]')
                print(f"  {field_name}: EXISTS, visible={visible}")
            else:
                print(f"  {field_name}: NOT FOUND")
        
        print("\n\n→ Press ENTER to close...")
        input()
        
        browser.close()

if __name__ == "__main__":
    main()

