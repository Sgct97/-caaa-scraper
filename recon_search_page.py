#!/usr/bin/env python3
"""
Reconnaissance script to capture search page structure
"""

from playwright.sync_api import sync_playwright
import json
from pathlib import Path

LOGIN_URL = "https://www.caaa.org/?pg=login"
SEARCH_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE_PATH = "auth.json"

def recon_search_page():
    """Capture all relevant data from the search page"""
    
    print("\n" + "="*60)
    print("CAAA Search Page Reconnaissance")
    print("="*60 + "\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        
        # Load saved cookies
        context = browser.new_context(
            storage_state=STORAGE_STATE_PATH,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        )
        
        page = context.new_page()
        
        # Navigate to search page
        print(f"→ Navigating to: {SEARCH_URL}")
        page.goto(SEARCH_URL, wait_until="networkidle")
        
        print(f"✓ Current URL: {page.url}\n")
        
        # Capture page title
        title = page.title()
        print(f"Page Title: {title}\n")
        
        # Find all input fields
        print("="*60)
        print("INPUT FIELDS")
        print("="*60)
        
        inputs = page.locator('input').all()
        input_data = []
        
        for i, inp in enumerate(inputs):
            try:
                field_type = inp.get_attribute('type') or 'text'
                field_name = inp.get_attribute('name') or ''
                field_id = inp.get_attribute('id') or ''
                field_placeholder = inp.get_attribute('placeholder') or ''
                field_value = inp.get_attribute('value') or ''
                is_visible = inp.is_visible()
                
                if is_visible and field_type not in ['hidden', 'submit', 'button']:
                    print(f"\nInput {i+1}:")
                    print(f"  Type: {field_type}")
                    print(f"  Name: {field_name}")
                    print(f"  ID: {field_id}")
                    print(f"  Placeholder: {field_placeholder}")
                    print(f"  Default Value: {field_value}")
                    
                    input_data.append({
                        'type': field_type,
                        'name': field_name,
                        'id': field_id,
                        'placeholder': field_placeholder,
                        'default_value': field_value
                    })
            except Exception as e:
                pass
        
        # Find all select/dropdown fields
        print("\n" + "="*60)
        print("SELECT/DROPDOWN FIELDS")
        print("="*60)
        
        selects = page.locator('select').all()
        select_data = []
        
        for i, sel in enumerate(selects):
            try:
                field_name = sel.get_attribute('name') or ''
                field_id = sel.get_attribute('id') or ''
                is_visible = sel.is_visible()
                
                if is_visible:
                    # Get all options
                    options = sel.locator('option').all()
                    option_values = []
                    
                    for opt in options:
                        opt_text = opt.inner_text()
                        opt_value = opt.get_attribute('value') or ''
                        option_values.append({'text': opt_text, 'value': opt_value})
                    
                    print(f"\nSelect {i+1}:")
                    print(f"  Name: {field_name}")
                    print(f"  ID: {field_id}")
                    print(f"  Options ({len(option_values)}):")
                    for opt in option_values[:10]:  # Show first 10
                        print(f"    - {opt['text']} (value: {opt['value']})")
                    if len(option_values) > 10:
                        print(f"    ... and {len(option_values) - 10} more")
                    
                    select_data.append({
                        'name': field_name,
                        'id': field_id,
                        'options': option_values
                    })
            except Exception as e:
                pass
        
        # Find textareas
        print("\n" + "="*60)
        print("TEXTAREA FIELDS")
        print("="*60)
        
        textareas = page.locator('textarea').all()
        textarea_data = []
        
        for i, ta in enumerate(textareas):
            try:
                field_name = ta.get_attribute('name') or ''
                field_id = ta.get_attribute('id') or ''
                field_placeholder = ta.get_attribute('placeholder') or ''
                is_visible = ta.is_visible()
                
                if is_visible:
                    print(f"\nTextarea {i+1}:")
                    print(f"  Name: {field_name}")
                    print(f"  ID: {field_id}")
                    print(f"  Placeholder: {field_placeholder}")
                    
                    textarea_data.append({
                        'name': field_name,
                        'id': field_id,
                        'placeholder': field_placeholder
                    })
            except Exception as e:
                pass
        
        # Find submit buttons
        print("\n" + "="*60)
        print("SUBMIT BUTTONS")
        print("="*60)
        
        buttons = page.locator('button[type="submit"], input[type="submit"]').all()
        button_data = []
        
        for i, btn in enumerate(buttons):
            try:
                btn_text = btn.inner_text() if btn.inner_text() else btn.get_attribute('value') or ''
                btn_id = btn.get_attribute('id') or ''
                btn_name = btn.get_attribute('name') or ''
                is_visible = btn.is_visible()
                
                if is_visible:
                    print(f"\nButton {i+1}:")
                    print(f"  Text: {btn_text}")
                    print(f"  ID: {btn_id}")
                    print(f"  Name: {btn_name}")
                    
                    button_data.append({
                        'text': btn_text,
                        'id': btn_id,
                        'name': btn_name
                    })
            except Exception as e:
                pass
        
        # Capture form action
        print("\n" + "="*60)
        print("FORM INFORMATION")
        print("="*60)
        
        forms = page.locator('form').all()
        form_data = []
        
        for i, form in enumerate(forms):
            try:
                action = form.get_attribute('action') or ''
                method = form.get_attribute('method') or 'GET'
                form_id = form.get_attribute('id') or ''
                
                print(f"\nForm {i+1}:")
                print(f"  Action: {action}")
                print(f"  Method: {method}")
                print(f"  ID: {form_id}")
                
                form_data.append({
                    'action': action,
                    'method': method,
                    'id': form_id
                })
            except Exception as e:
                pass
        
        # Take screenshot
        print("\n" + "="*60)
        print("CAPTURING SCREENSHOT & HTML")
        print("="*60)
        
        page.screenshot(path="search_page_screenshot.png")
        print("✓ Screenshot saved: search_page_screenshot.png")
        
        # Save HTML
        html_content = page.content()
        with open("search_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("✓ HTML saved: search_page.html")
        
        # Save all data as JSON
        recon_data = {
            'url': page.url,
            'title': title,
            'inputs': input_data,
            'selects': select_data,
            'textareas': textarea_data,
            'buttons': button_data,
            'forms': form_data
        }
        
        with open("search_page_recon.json", "w", encoding="utf-8") as f:
            json.dump(recon_data, f, indent=2)
        print("✓ Recon data saved: search_page_recon.json")
        
        print("\n" + "="*60)
        print("RECONNAISSANCE COMPLETE")
        print("="*60)
        print("\nPress ENTER to close browser...")
        input()
        
        browser.close()


if __name__ == "__main__":
    recon_search_page()

