from playwright.async_api import async_playwright
from .models import DietaryPreference
import logging

logger = logging.getLogger(__name__)

class BrowserAutomator:
    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        await self.context.clear_cookies()
        self.page = await self.context.new_page()

    async def navigate(self, url: str):
        await self.page.goto(url)

    async def fill_text_field(self, selector: str, value: str):
        await self.page.fill(selector, value)

    async def button_click(self, selector):
        await self.page.click(selector)

    async def stop(self):
        await self.browser.close()
        await self.playwright.stop()

    async def run_all(self, ia_url: str, email: str, dietary_preference: DietaryPreference):
        await self.start()
        logger.info("Browser started and Playwright initialized")

        await self.navigate(ia_url)
        logger.info(f"Navigated to URL: {ia_url}")

        await self.button_click("button:has-text('Get Started')")
        logger.info("Clicked 'Get Started' button")

        await self.fill_text_field("#inpt.ushur-visualmenu-open-input.ushurapp-input.form-control", email)
        logger.info(f"Entered email: {email}")

        await self.button_click("button:has-text('Done')")
        logger.info("Clicked first 'Done' button after entering email")

        await self.button_click("span:has-text('yes')")
        logger.info("Clicked 'Yes' confirmation")

        await self.button_click(f"span:has-text('{dietary_preference.value}')")
        logger.info(f"Selected dietary preference: {dietary_preference.value}")

        await self.button_click("button:has-text('Done')")
        logger.info("Clicked final 'Done' button to submit dietary preference")

        await self.stop()
        logger.info("Browser closed and session ended")

