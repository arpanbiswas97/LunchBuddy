import asyncio
import logging

from playwright.async_api import async_playwright

from .models import DietaryPreference
from .config import settings

logger = logging.getLogger(__name__)


class BrowserAutomator:
    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True, slow_mo=settings.action_delay)
        self.context = await self.browser.new_context()
        await self.context.clear_cookies()
        self.page = await self.context.new_page()

    async def navigate(self, url: str):
        await self.page.goto(url)

    async def fill_text_field(self, selector: str, value: str):
        await self.page.fill(selector, value)

    async def button_click(self, selector, timeout=30000):
        # Timeout is in milliseconds and default value is 30s
        await self.page.click(selector, timeout=timeout)

    async def is_element_with_text_present(
        self, selector: str, text: str, timeout: int = 5000
    ) -> bool:
        try:
            await self.page.wait_for_selector(
                f"{selector}:has-text('{text}')", timeout=timeout
            )
            return True
        except Exception:
            return False

    async def stop(self):
        await self.browser.close()
        await self.playwright.stop()

    async def run_all(
        self, ia_url: str, email: str, dietary_preference: DietaryPreference
    ):
        await self.start()
        logger.info("Browser started and Playwright initialized")

        await self.navigate(ia_url)
        logger.info(f"Navigated to URL: {ia_url}")

        try:
            # Check if Engagement Start screen appears, timeout is 3s
            await self.button_click("button:has-text('Get Started')", 3000)
            logger.info("Clicked 'Get Started' button")
        except Exception as e:
            # If it doesn't then just continue
            pass

        await self.fill_text_field(
            "#inpt.ushur-visualmenu-open-input.ushurapp-input.form-control", email
        )
        logger.info(f"Entered email: {email}")

        await self.button_click("button:has-text('Next')")
        logger.info("Clicked first 'Next' button after entering email")

        await self.button_click("span:has-text('Yes')")
        logger.info("Clicked 'Yes' confirmation")

        await self.button_click(f"span:has-text('{dietary_preference.value}')")
        logger.info(f"Selected dietary preference: {dietary_preference.value}")

        await self.button_click("button:has-text('Next')")
        logger.info("Clicked final 'Next' button to submit dietary preference")

        if await self.is_element_with_text_present("h2", "Thank you!"):
            logger.info("Successfully registered for lunch.")
        else:
            logger.warning("Could not confirm registration for lunch.")

        await self.stop()
        logger.info("Browser closed and session ended")
