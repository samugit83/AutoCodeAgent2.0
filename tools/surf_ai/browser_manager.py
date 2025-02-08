from playwright.sync_api import sync_playwright

class BrowserManager:
    def __init__(self, command_timeout: int):
        self.command_timeout = command_timeout
        self.playwright = None
        self.browser = None

    def __enter__(self):
        # Start Playwright and launch the browser.
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Close the browser if it was created.
        if self.browser:
            try:
                self.browser.close()
            except Exception as e:
                # Optionally log or handle the exception.
                pass
        # Stop the Playwright instance.
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception as e:
                # Optionally log or handle the exception.
                pass

    def create_context(self):
        # Create a new browser context with the desired settings.
        context = self.browser.new_context(
            viewport={'width': 1280, 'height': 960},
            device_scale_factor=1,
            bypass_csp=True, 
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/98.0.4758.102 Safari/537.36"
            )
        )
        # Add an initialization script to modify navigator properties.
        context.add_init_script("""
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
            Object.defineProperty(navigator, 'vendor', {get: () => 'Google Inc.'});
        """)
        return context

    def create_page(self, context):
        # Create a new page in the provided context.
        page = context.new_page()
        page.set_default_timeout(self.command_timeout)
        return page
