import logging

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from .config import settings
from .models import DietaryPreference

logger = logging.getLogger(__name__)


class BrowserAutomator:
    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            slow_mo=settings.action_delay,
        )
        self.context = await self.browser.new_context()
        self.context.set_default_navigation_timeout(settings.timeout)
        self.context.set_default_timeout(settings.timeout)
        self.page = await self.context.new_page()

    async def navigate(self, url: str):
        await self.page.goto(url)

    async def fill_text_field(self, selector: str, value: str):
        await self.page.fill(selector, value)

    async def button_click(self, selector: str):
        await self.page.click(selector)

    async def is_element_with_text_present(self, selector: str, text: str) -> bool:
        try:
            await self.page.wait_for_selector(f"{selector}:has-text('{text}')")
            return True
        except PlaywrightTimeoutError:
            return False
        except Exception as e:
            logger.exception(
                f"Unexpected error while checking for element with text: {e}"
            )
            return False

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, "playwright"):
            await self.playwright.stop()

    async def fill_form(
        self, ia_url: str, email: str, dietary_preference: DietaryPreference
    ) -> bool:
        try:
            await self.start()
            logger.info("Browser started and Playwright initialized")

            await self.navigate(ia_url)
            logger.info(f"Navigated to URL: {ia_url}")

            # Attempt clicking "Get Started" with timeout
            try:
                await self.page.click("button:has-text('Get Started')", timeout=3000)
                logger.info("Clicked 'Get Started' button")
            except PlaywrightTimeoutError:
                logger.info("'Get Started' button not found, continuing...")

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

            success = await self.is_element_with_text_present("h2", "Thank you!")
            if success:
                logger.info("Successfully registered for lunch.")
            else:
                logger.warning("Could not confirm registration for lunch.")
                return False

            return True

        except Exception as e:
            logger.exception(f"Unexpected error during automation: {e}")
            return False

        finally:
            await self.stop()
            logger.info("Browser closed and session ended")
