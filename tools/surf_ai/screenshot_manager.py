import base64
from datetime import datetime

class ScreenshotManager: 
    def __init__(self, truncation_length: int): 
        self.truncation_length = truncation_length
        self.screenshot_url = None
        self.screenshot_base64 = None  
        self.scraped_page = None

    async def capture(self, page, task_name):
        await self._take_screenshot(page, task_name) 
        await self._scrape_content(page)

    async def _take_screenshot(self, page, task_name):
        current_time = datetime.now().strftime("%H-%M-%S")
        screenshot_path = f"./tools/surf_ai/screenshots/{current_time}_{task_name}.png"
        await page.screenshot(path=screenshot_path, full_page=False) 
        self.screenshot_url = screenshot_path 
        
        with open(screenshot_path, "rb") as image_file:
            self.screenshot_base64 = base64.b64encode(image_file.read()).decode('utf-8')

    async def _scrape_content(self, page):
        try:
            elements_html = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('*[data-highlight-number]'));
            }''')
             
            scraped_content = f"<!-- Visible Interactive Elements ({len(elements_html)}) -->\n" + '\n'.join(elements_html)
            self.scraped_page = scraped_content[:self.truncation_length]
        except Exception as e:
            self.scraped_page = "CONTENT_UNAVAILABLE"
