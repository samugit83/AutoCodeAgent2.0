import base64
from datetime import datetime

class ScreenshotManager:
    def __init__(self):
        self.screenshot_base64 = None
        self.scraped_page = None  

    async def capture(self, page):
            """
            Capture a screenshot from the given page and return its base64 encoding.
            """
            current_time = datetime.now().strftime("%H-%M-%S")
            screenshot_path = f"./tools/cua/screenshots/{current_time}.png"
            screenshot_bytes = await page.screenshot(path=screenshot_path, full_page=False) 
            self.screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            return self.screenshot_base64
          