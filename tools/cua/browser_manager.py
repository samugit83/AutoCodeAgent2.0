# browser_manager.py


from playwright.async_api import async_playwright

class BrowserManager:
    def __init__(self, command_timeout: int):
        self.command_timeout = command_timeout
        self.playwright = None
        self.browser = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        # You can set headless=True if you prefer a headless browser:
        self.browser = await self.playwright.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_browser()

    async def create_context(self):
        context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 960},
            device_scale_factor=1,
            bypass_csp=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/98.0.4758.102 Safari/537.36"
            )
        )
        # Override navigator properties
        await context.add_init_script("""
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
        """)
        return context

    async def create_page(self, context):
        page = await context.new_page()
        page.set_default_timeout(self.command_timeout)
        return page

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
