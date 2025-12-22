#!/usr/bin/env python3
"""
Persistent Browser Session Manager
Keeps a browser instance running indefinitely to preserve cookies
"""

import time
import signal
import sys
from playwright.sync_api import sync_playwright, Browser, BrowserContext
from datetime import datetime

class PersistentBrowser:
    """Manages a long-running browser session"""
    
    def __init__(self, storage_state_path: str = "auth.json"):
        self.storage_state_path = storage_state_path
        self.playwright = None
        self.browser = None
        self.context = None
        self.running = False
    
    def start(self):
        """Start the persistent browser session"""
        print("="*60)
        print("PERSISTENT BROWSER SESSION")
        print("="*60)
        print(f"\nStarting at: {datetime.now()}")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            self.playwright = sync_playwright().start()
            
            # Launch browser in headless mode
            print("\n→ Launching browser (headless)...")
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            
            # Create context with saved cookies
            print(f"→ Loading cookies from: {self.storage_state_path}")
            self.context = self.browser.new_context(
                storage_state=self.storage_state_path
            )
            
            # Create a page and navigate to keep session alive
            page = self.context.new_page()
            print("→ Navigating to CAAA.org to establish session...")
            page.goto("https://www.caaa.org/", wait_until="domcontentloaded")
            
            print("\n✓ Persistent browser session started successfully!")
            print(f"✓ Cookies loaded from: {self.storage_state_path}")
            print("\nSession will remain active until stopped.")
            print("Cookies will NOT expire as long as this process runs.")
            print("\nTo stop: Press Ctrl+C or send SIGTERM")
            
            self.running = True
            
            # Keep alive loop
            self._keep_alive_loop()
            
        except KeyboardInterrupt:
            print("\n\n→ Received interrupt signal...")
            self._cleanup()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            self._cleanup()
            sys.exit(1)
    
    def _keep_alive_loop(self):
        """Keep the browser alive and periodically refresh the session"""
        page = self.context.pages[0]
        refresh_interval = 3600  # Refresh every hour
        restart_interval = 43200  # FULL RESTART every 12 hours to clear memory
        last_refresh = time.time()
        last_restart = time.time()
        
        while self.running:
            try:
                # Sleep for a bit
                time.sleep(60)  # Check every minute
                
                # Periodic FULL RESTART to clear memory leaks (every 12 hours)
                if time.time() - last_restart > restart_interval:
                    print(f"\n[{datetime.now()}] 🔄 FULL RESTART to clear memory...")
                    new_page = self._restart_context()
                    if new_page:
                        page = new_page  # Only update if successful
                        last_restart = time.time()
                        last_refresh = time.time()
                        print("  ✓ Browser context restarted, memory cleared")
                    else:
                        # Restart failed - try to recover a working page
                        print("  ⚠️ Restart failed, attempting recovery...")
                        try:
                            if self.context and self.context.pages:
                                page = self.context.pages[0]
                            else:
                                # Context broken, recreate from saved cookies
                                self.context = self.browser.new_context(
                                    storage_state=self.storage_state_path
                                )
                                page = self.context.new_page()
                                page.goto("https://www.caaa.org/", wait_until="domcontentloaded")
                            last_restart = time.time()
                            print("  ✓ Recovery successful")
                        except Exception as e:
                            print(f"  ❌ Recovery failed: {e}, will retry next cycle")
                    continue
                
                # Periodic refresh to keep session active
                if time.time() - last_refresh > refresh_interval:
                    print(f"\n[{datetime.now()}] Refreshing session...")
                    try:
                        page.goto("https://www.caaa.org/", wait_until="domcontentloaded")
                        print("  ✓ Session refreshed")
                    except Exception as e:
                        print(f"  ⚠️  Refresh warning: {e}")
                    
                    last_refresh = time.time()
                
            except Exception as e:
                print(f"\n⚠️  Keep-alive error: {e}")
                time.sleep(10)
    
    def _restart_context(self):
        """Restart browser context to clear memory - keeps cookies"""
        try:
            # Save cookies first
            if self.context:
                self.context.storage_state(path=self.storage_state_path)
                print("  → Cookies saved")
                
                # Close old context
                for page in self.context.pages:
                    page.close()
                self.context.close()
                print("  → Old context closed")
            
            # Create fresh context with saved cookies
            self.context = self.browser.new_context(
                storage_state=self.storage_state_path
            )
            
            # Create new page and navigate
            page = self.context.new_page()
            page.goto("https://www.caaa.org/", wait_until="domcontentloaded")
            print("  → New context created with fresh memory")
            
            return page
            
        except Exception as e:
            print(f"  ❌ Restart failed: {e}")
            return None
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n\n→ Received signal {signum}")
        self.running = False
        self._cleanup()
        sys.exit(0)
    
    def _cleanup(self):
        """Clean up resources"""
        print("\n→ Shutting down persistent browser...")
        
        if self.context:
            try:
                # Save current cookies before closing
                self.context.storage_state(path=self.storage_state_path)
                print(f"  ✓ Cookies saved to: {self.storage_state_path}")
            except:
                pass
            
            try:
                self.context.close()
            except:
                pass
        
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
        
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
        
        print("✓ Cleanup complete")
    
    def get_context(self) -> BrowserContext:
        """Get the browser context for use in other scripts"""
        return self.context


def main():
    """Run as standalone service"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Persistent Browser Session Manager')
    parser.add_argument(
        '--storage-state',
        default='auth.json',
        help='Path to cookies file (default: auth.json)'
    )
    
    args = parser.parse_args()
    
    manager = PersistentBrowser(storage_state_path=args.storage_state)
    manager.start()


if __name__ == "__main__":
    main()

