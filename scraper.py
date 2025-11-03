#!/usr/bin/env python3
"""
CAAA Scraper - Main scraping logic
Handles search execution, pagination, and message extraction
"""

from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Callable
from datetime import datetime
import time
import re

from search_params import SearchParams


class CAAAScraper:
    """Main scraper class for CAAA listserv"""
    
    def __init__(self, storage_state_path: str = "auth.json"):
        self.storage_state_path = storage_state_path
        self.search_url = "https://www.caaa.org/?pg=search&bid=3305"
    
    def scrape(self, 
               search_params: SearchParams,
               progress_callback: Optional[Callable[[str, int, int], None]] = None) -> List[Dict]:
        """
        Main scrape method - executes search and fetches messages
        
        Args:
            search_params: SearchParams object with search criteria
            progress_callback: Optional callback function(status, current, total)
        
        Returns:
            List of message dictionaries
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(storage_state=self.storage_state_path)
            page = context.new_page()
            
            try:
                # Step 1: Execute search
                if progress_callback:
                    progress_callback("Executing search...", 0, search_params.max_messages)
                
                self._execute_search(page, search_params)
                
                # Step 2: Extract message IDs from results pages
                if progress_callback:
                    progress_callback("Extracting message IDs...", 0, search_params.max_messages)
                
                message_ids = self._extract_message_ids(
                    page, 
                    max_pages=search_params.max_pages,
                    max_messages=search_params.max_messages,
                    progress_callback=progress_callback
                )
                
                print(f"\n✓ Found {len(message_ids)} messages")
                
                # Step 3: Fetch full content for each message
                messages = []
                for i, msg_id in enumerate(message_ids):
                    if progress_callback:
                        progress_callback(
                            f"Fetching message content...",
                            i + 1,
                            len(message_ids)
                        )
                    
                    try:
                        message_data = self._fetch_message_content(page, msg_id)
                        if message_data:
                            messages.append(message_data)
                    except Exception as e:
                        print(f"  ⚠️  Failed to fetch message {msg_id['message_id']}: {e}")
                        continue
                
                print(f"\n✓ Successfully fetched {len(messages)} messages")
                return messages
                
            finally:
                browser.close()
    
    def _execute_search(self, page: Page, search_params: SearchParams):
        """Execute search with given parameters"""
        print(f"\n→ Navigating to search page...")
        page.goto(self.search_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        
        print(f"→ Filling search form...")
        print(f"   Parameters: {search_params}")
        
        form_data = search_params.to_form_data()
        
        # Fill form fields
        for field_name, field_value in form_data.items():
            if not field_name.startswith('s_'):
                continue
            
            try:
                selector = f'input[name="{field_name}"]'
                
                if page.query_selector(selector):
                    if 'date' in field_name:
                        # Date fields: use JavaScript
                        page.evaluate(f"document.querySelector('{selector}').value = '{field_value}'")
                    else:
                        # Find visible field (handles duplicate field names)
                        all_matches = page.query_selector_all(selector)
                        for field in all_matches:
                            if field.is_visible():
                                field.fill(str(field_value), timeout=3000, force=True)
                                break
                else:
                    # Try select dropdown
                    selector = f'select[name="{field_name}"]'
                    if page.query_selector(selector):
                        page.select_option(selector, str(field_value))
            except Exception as e:
                print(f"   ⚠️  Could not set {field_name}: {e}")
        
        # Submit search
        print(f"→ Submitting search...")
        try:
            # Try clicking the search button
            page.click('#s_btn', timeout=10000)
        except Exception as e:
            print(f"  ⚠️  Could not click #s_btn: {e}")
            # Try alternative selector
            try:
                page.click('input[name="s_btn"]', timeout=5000)
            except:
                print(f"  ⚠️  Trying to find any submit button...")
                page.click('button[type="submit"], input[type="submit"]', timeout=5000)
        
        # Wait for results (AJAX loads results dynamically)
        print(f"→ Waiting for results to load...")
        try:
            # Wait for the loading icon to appear, then disappear (indicates AJAX is complete)
            page.wait_for_selector('#bk_content', timeout=5000)
            page.wait_for_timeout(2000)  # Let AJAX start
            
            # Wait for results table or "no results" message (up to 30 seconds for slow searches)
            page.wait_for_selector("table.table-striped tbody tr, .resultMsgExposition, .s_rnfne", timeout=30000)
            page.wait_for_timeout(2000)  # Let content fully render
            
        except Exception as e:
            print(f"  ⚠️  Timeout waiting for results: {e}")
            page.wait_for_timeout(5000)  # Fallback wait
        
        print(f"✓ Search submitted")
    
    def _extract_message_ids(self, 
                             page: Page,
                             max_pages: int = 10,
                             max_messages: int = 100,
                             progress_callback: Optional[Callable] = None) -> List[Dict]:
        """
        Extract message IDs from paginated results
        
        Returns:
            List of dicts with: message_id, date, from, subject, list, position, page
        """
        message_ids = []
        current_page = 1
        
        while current_page <= max_pages and len(message_ids) < max_messages:
            print(f"\n→ Extracting from page {current_page}...")
            
            # Wait for results table
            try:
                page.wait_for_selector("table.table-striped tbody tr", timeout=10000)
            except:
                print(f"  ⚠️  No results table found on page {current_page}")
                break
            
            # Extract message data from this page
            rows = page.query_selector_all("table.table-striped tbody tr")
            page_messages = []
            
            for row in rows:
                # Skip header row
                if row.query_selector("b"):
                    continue
                
                cells = row.query_selector_all("td")
                if len(cells) < 5:
                    continue
                
                # Extract data
                date_str = cells[0].inner_text().strip()
                from_field = cells[1].inner_text().strip()
                list_name = cells[2].inner_text().strip()
                has_attachment = bool(cells[3].inner_text().strip())
                
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
                    
                    if message_id:
                        page_messages.append({
                            'message_id': message_id,
                            'date': date_str,
                            'from': from_field,
                            'subject': subject,
                            'list': list_name,
                            'has_attachment': has_attachment,
                            'position': len(message_ids) + len(page_messages) + 1,
                            'page': current_page
                        })
            
            print(f"  ✓ Found {len(page_messages)} messages on page {current_page}")
            message_ids.extend(page_messages)
            
            # Check if we have enough
            if len(message_ids) >= max_messages:
                print(f"  → Reached max_messages limit ({max_messages})")
                break
            
            # Try to go to next page
            if current_page < max_pages:
                next_page_found = self._go_to_next_page(page, current_page)
                if not next_page_found:
                    print(f"  → No more pages available")
                    break
                
                current_page += 1
                page.wait_for_timeout(2000)
            else:
                break
        
        # Trim to max_messages
        return message_ids[:max_messages]
    
    def _go_to_next_page(self, page: Page, current_page: int) -> bool:
        """
        Navigate to next page of results
        
        Returns:
            True if next page exists and was navigated to, False otherwise
        """
        try:
            # Look for pagination
            pagination = page.query_selector("#seachResultsPaginationBar")
            if not pagination:
                return False
            
            # Look for next page link (page number or "next" button)
            next_page_num = current_page + 1
            
            # Try clicking the page number
            next_link = pagination.query_selector(f"a:has-text('{next_page_num}')")
            if next_link:
                next_link.click()
                page.wait_for_timeout(2000)
                return True
            
            # Try clicking ">" (next) button
            next_button = pagination.query_selector("a[title='Next Page']")
            if next_button:
                next_button.click()
                page.wait_for_timeout(2000)
                return True
            
            return False
            
        except Exception as e:
            print(f"  ⚠️  Error navigating to next page: {e}")
            return False
    
    def _fetch_message_content(self, page: Page, message_info: Dict) -> Optional[Dict]:
        """
        Fetch full content for a single message
        
        Args:
            message_info: Dict with message_id and metadata
        
        Returns:
            Dict with full message data or None if failed
        """
        message_id = message_info['message_id']
        
        try:
            # Click the message link to load content
            # Navigate back to results first (if not on results page)
            if "#s_lyris_messagewindow" not in page.url:
                # We might need to re-execute search or store results URL
                pass
            
            # Use JavaScript to load message
            page.evaluate(f"b_loadmsgjson({message_id},'','responsive');")
            page.wait_for_timeout(2000)
            
            # Wait for message content
            page.wait_for_selector("#s_lyris_messagewindow", timeout=5000)
            
            # Extract clean content
            message_container = page.query_selector("#s_lyris_messagewindow")
            if not message_container:
                return None
            
            html_content = message_container.inner_html()
            clean_data = self._extract_clean_message_text(html_content)
            
            # Combine with metadata
            return {
                'caaa_message_id': message_id,
                'post_date': self._parse_date(message_info['date']),
                'from_name': clean_data.get('from', message_info['from']),
                'from_email': self._extract_email(clean_data.get('from', '')),
                'listserv': message_info['list'],
                'subject': clean_data.get('subject', message_info['subject']),
                'body': clean_data.get('body', ''),
                'has_attachment': message_info['has_attachment'],
                'position': message_info['position'],
                'page': message_info['page']
            }
            
        except Exception as e:
            print(f"    Error fetching message {message_id}: {e}")
            return None
    
    def _extract_clean_message_text(self, html_content: str) -> Dict[str, str]:
        """Extract clean text from message HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract header info
        from_field = ""
        date_field = ""
        subject_field = ""
        
        header_spans = soup.find_all('span', limit=3)
        for span in header_spans:
            text = span.get_text()
            if text.startswith('From:'):
                from_field = text.replace('From:', '').strip()
            elif text.startswith('Date:'):
                date_field = text.replace('Date:', '').strip()
            elif text.startswith('Subject:'):
                subject_field = text.replace('Subject:', '').strip()
        
        # Find main message body (first div with dir="ltr" not inside blockquote)
        main_body = ""
        for div in soup.find_all('div', {'dir': 'ltr'}):
            if not div.find_parent('blockquote'):
                text_parts = []
                for child in div.children:
                    if child.name == 'blockquote':
                        break
                    if hasattr(child, 'get_text'):
                        text_parts.append(child.get_text().strip())
                    elif isinstance(child, str):
                        text_parts.append(child.strip())
                
                main_body = ' '.join([t for t in text_parts if t])
                if main_body:
                    break
        
        return {
            'from': from_field,
            'date': date_field,
            'subject': subject_field,
            'body': main_body.strip()
        }
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to YYYY-MM-DD format"""
        try:
            # Handle format: 10/29/25
            parts = date_str.split('/')
            if len(parts) == 3:
                month, day, year = parts
                year = f"20{year}" if len(year) == 2 else year
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except:
            pass
        return None
    
    def _extract_email(self, from_str: str) -> Optional[str]:
        """Extract email from 'Name <email>' format"""
        match = re.search(r'<([^>]+)>', from_str)
        if match:
            return match.group(1)
        return None


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    from search_params import SearchParams
    
    # Example search
    search = SearchParams(
        keyword="workers compensation",
        max_pages=2,
        max_messages=20
    )
    
    scraper = CAAAScraper()
    
    def progress(status, current, total):
        print(f"  [{current}/{total}] {status}")
    
    results = scraper.scrape(search, progress_callback=progress)
    
    print(f"\n✓ Scraped {len(results)} messages")
    for msg in results[:3]:
        print(f"\n{msg['subject']}")
        print(f"  From: {msg['from_name']}")
        print(f"  Body: {msg['body'][:100]}...")

