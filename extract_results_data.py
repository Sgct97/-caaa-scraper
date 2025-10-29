#!/usr/bin/env python3
"""
Extract structured data from CAAA search results page
This script parses the results table and extracts:
- Date, From, Subject, Message ID for each result
- Pagination information
- Total results count
"""

from playwright.sync_api import sync_playwright
import json
from datetime import datetime

SEARCH_PAGE_URL = "https://www.caaa.org/?pg=search&bid=3305"
STORAGE_STATE_PATH = "auth.json"

def extract_results_data(page):
    """Extract all data from the current results page"""
    
    print("→ Extracting results from current page...")
    
    # Wait for results table to load
    try:
        page.wait_for_selector("table.table-striped tbody tr", timeout=10000)
    except:
        print("⚠️  No results table found")
        return None
    
    # Extract total count
    total_count = "Unknown"
    try:
        count_elem = page.query_selector(".s_rnfne")
        if count_elem:
            total_count = count_elem.inner_text().strip()
    except:
        pass
    
    # Extract pagination info
    pagination_info = {}
    try:
        pagination = page.query_selector("#seachResultsPaginationBar")
        if pagination:
            pagination_text = pagination.inner_text()
            if "Page" in pagination_text:
                pagination_info["text"] = pagination_text.split("\n")[-1].strip()
    except:
        pass
    
    # Extract all result rows
    results = []
    rows = page.query_selector_all("table.table-striped tbody tr")
    
    for i, row in enumerate(rows):
        # Skip header row (has <b> tags)
        if row.query_selector("b"):
            continue
        
        cells = row.query_selector_all("td")
        if len(cells) < 5:
            continue
        
        # Extract data from each cell
        date = cells[0].inner_text().strip()
        from_field = cells[1].inner_text().strip()
        list_name = cells[2].inner_text().strip()
        has_attachment = cells[3].inner_text().strip()
        
        # Extract subject and message ID
        subject_cell = cells[4]
        subject_link = subject_cell.query_selector("a")
        
        if subject_link:
            subject = subject_link.inner_text().strip()
            onclick = subject_link.get_attribute("href") or ""
            
            # Extract message ID from javascript:b_loadmsgjson(21777803,'','responsive')
            message_id = None
            if "b_loadmsgjson" in onclick:
                try:
                    message_id = onclick.split("(")[1].split(",")[0].strip()
                except:
                    pass
            
            result = {
                "row_index": i,
                "date": date,
                "from": from_field,
                "list": list_name,
                "has_attachment": bool(has_attachment),
                "subject": subject,
                "message_id": message_id,
                "onclick_full": onclick
            }
            
            results.append(result)
    
    return {
        "extracted_at": datetime.now().isoformat(),
        "total_count": total_count,
        "pagination": pagination_info,
        "results_on_page": len(results),
        "results": results
    }


def main():
    with sync_playwright() as p:
        print("============================================================")
        print("Extracting CAAA Results Data")
        print("============================================================")
        
        # Launch browser
        browser = p.chromium.launch(headless=False)
        
        # Load saved cookies
        context = browser.new_context(storage_state=STORAGE_STATE_PATH)
        page = context.new_page()
        
        # Go to search page
        print(f"→ Navigating to search page...")
        page.goto(SEARCH_PAGE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        
        # Fill in a test search (you can modify this)
        print("→ Filling search form...")
        search_term = "workers compensation"
        page.fill('input[name="s_fname"]', search_term)
        
        # Submit search
        print("→ Submitting search...")
        page.click('#s_btn')
        
        # Wait for results
        print("→ Waiting for results...")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except:
            page.wait_for_timeout(3000)
        
        # Extract data
        data = extract_results_data(page)
        
        if data:
            # Save to JSON
            output_file = "results_data.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"\n✓ Extracted {data['results_on_page']} results")
            print(f"✓ Total found: {data['total_count']}")
            print(f"✓ Pagination: {data['pagination'].get('text', 'N/A')}")
            print(f"✓ Data saved to: {output_file}")
            
            # Show first few results
            print("\n📋 Sample results:")
            for result in data['results'][:3]:
                print(f"  • {result['date']} - {result['subject'][:50]}...")
                print(f"    Message ID: {result['message_id']}")
        else:
            print("❌ No results found")
        
        print("\nPress ENTER to close browser...")
        input()
        
        browser.close()

if __name__ == "__main__":
    main()

