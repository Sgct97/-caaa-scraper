#!/usr/bin/env python3
"""
Extract clean message content from a CAAA listserv message
This script demonstrates fetching a single message and extracting clean text
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json

SEARCH_PAGE_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE_PATH = "auth.json"

def extract_clean_message_text(html_content):
    """Extract clean text from message HTML, removing formatting and nested replies"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract header info
    from_field = ""
    date_field = ""
    subject_field = ""
    
    # Look for From, Date, Subject in the first span elements
    header_spans = soup.find_all('span', limit=3)
    for span in header_spans:
        text = span.get_text()
        if text.startswith('From:'):
            from_field = text.replace('From:', '').strip()
        elif text.startswith('Date:'):
            date_field = text.replace('Date:', '').strip()
        elif text.startswith('Subject:'):
            subject_field = text.replace('Subject:', '').strip()
    
    # Find the main message body (first div with dir="ltr" that's not inside a blockquote)
    main_body = ""
    for div in soup.find_all('div', {'dir': 'ltr'}):
        # Check if this div is NOT inside a blockquote (which would be a reply)
        if not div.find_parent('blockquote'):
            # Get text but stop at first blockquote (which is the reply thread)
            text_parts = []
            for child in div.children:
                if child.name == 'blockquote':
                    break  # Stop at replies
                if hasattr(child, 'get_text'):
                    text_parts.append(child.get_text().strip())
                elif isinstance(child, str):
                    text_parts.append(child.strip())
            
            main_body = ' '.join([t for t in text_parts if t])
            if main_body:  # Use the first non-empty body we find
                break
    
    return {
        'from': from_field,
        'date': date_field,
        'subject': subject_field,
        'body': main_body.strip(),
        'body_length': len(main_body.strip())
    }

def main():
    with sync_playwright() as p:
        print("============================================================")
        print("Extracting Clean Message Content")
        print("============================================================")
        
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=STORAGE_STATE_PATH)
        page = context.new_page()
        
        # Navigate and search
        print("→ Running search...")
        page.goto(SEARCH_PAGE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        page.fill('input[name="s_fname"]', "workers compensation")
        page.click('#s_btn')
        
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except:
            page.wait_for_timeout(3000)
        
        page.wait_for_selector("table.table-striped tbody tr", timeout=10000)
        
        # Click first result
        print("→ Clicking first result...")
        first_link = page.query_selector("table.table-striped tbody tr td a[href*='b_loadmsgjson']")
        
        if first_link:
            first_link.click()
            page.wait_for_timeout(3000)
            
            # Get message content
            message_container = page.query_selector("#s_lyris_messagewindow")
            
            if message_container:
                html_content = message_container.inner_html()
                
                # Extract clean text
                print("\n→ Extracting clean message content...")
                clean_data = extract_clean_message_text(html_content)
                
                print("\n" + "="*60)
                print("📧 EXTRACTED MESSAGE")
                print("="*60)
                print(f"From: {clean_data['from']}")
                print(f"Date: {clean_data['date']}")
                print(f"Subject: {clean_data['subject']}")
                print(f"\nBody ({clean_data['body_length']} characters):")
                print("-" * 60)
                print(clean_data['body'])
                print("="*60)
                
                # Save to JSON
                with open("extracted_message.json", "w", encoding="utf-8") as f:
                    json.dump(clean_data, f, indent=2, ensure_ascii=False)
                
                print("\n✓ Saved to: extracted_message.json")
                
                # This is the text we would feed to OpenAI
                print("\n💡 This clean text would be sent to OpenAI for analysis:")
                print(f"   - Character count: {clean_data['body_length']}")
                print(f"   - Word count: ~{len(clean_data['body'].split())}")
            else:
                print("❌ Could not find message container")
        else:
            print("❌ No results found")
        
        print("\nPress ENTER to close...")
        input()
        
        browser.close()

if __name__ == "__main__":
    main()

