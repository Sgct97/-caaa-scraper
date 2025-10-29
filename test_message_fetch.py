#!/usr/bin/env python3
"""
Test fetching full message content by clicking a result
This will help us understand how to extract the actual message text
"""

from playwright.sync_api import sync_playwright
import json
from datetime import datetime

SEARCH_PAGE_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE_PATH = "auth.json"

def main():
    with sync_playwright() as p:
        print("============================================================")
        print("Testing Message Content Fetch")
        print("============================================================")
        
        # Launch browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=STORAGE_STATE_PATH)
        page = context.new_page()
        
        # Go to search page
        print(f"→ Navigating to search page...")
        page.goto(SEARCH_PAGE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        
        # Fill search
        print("→ Filling search form...")
        page.fill('input[name="s_fname"]', "workers compensation")
        
        # Submit search
        print("→ Submitting search...")
        page.click('#s_btn')
        
        # Wait for results
        print("→ Waiting for results...")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except:
            page.wait_for_timeout(3000)
        
        # Wait for results table
        page.wait_for_selector("table.table-striped tbody tr", timeout=10000)
        
        # Click the first result link
        print("→ Clicking first result to load message...")
        first_link = page.query_selector("table.table-striped tbody tr td a[href*='b_loadmsgjson']")
        
        if first_link:
            subject = first_link.inner_text()
            print(f"   Subject: {subject}")
            
            # Click and wait for content to load
            first_link.click()
            page.wait_for_timeout(3000)
            
            # Look for the message content container
            # Common patterns: div with message content, iframe, or specific div IDs
            print("\n→ Looking for message content...")
            
            # Take a screenshot to see what appeared
            page.screenshot(path="message_content_screenshot.png", full_page=True)
            print("✓ Screenshot saved: message_content_screenshot.png")
            
            # Try to find common message content containers
            possible_selectors = [
                "#s_lyris_messagewindow",
                ".s_dtl",
                "div[id*='message']",
                "div[class*='message']",
                "iframe"
            ]
            
            found_content = False
            for selector in possible_selectors:
                element = page.query_selector(selector)
                if element:
                    print(f"\n✓ Found content in: {selector}")
                    content = element.inner_text() if selector != "iframe" else "[IFRAME CONTENT]"
                    print(f"   Preview: {content[:200]}...")
                    found_content = True
                    
                    # Save full HTML
                    html = element.inner_html() if selector != "iframe" else element.get_attribute("src")
                    with open("message_content.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    print("✓ Full content saved: message_content.html")
                    break
            
            if not found_content:
                print("\n⚠️  Could not automatically locate message content")
                print("   Saving full page HTML for manual inspection...")
                html = page.content()
                with open("full_page_after_click.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print("✓ Saved: full_page_after_click.html")
        else:
            print("❌ No results found")
        
        print("\n→ Press ENTER to close browser...")
        input()
        
        browser.close()

if __name__ == "__main__":
    main()

