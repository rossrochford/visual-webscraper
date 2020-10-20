import asyncio
import time

import aiohttp

from aioselenium import Remote, Keys
from selenium import webdriver


def _create_new_driver_connection():
    driver = webdriver.Firefox()
    # we need to keep these in memory to the session doesn't get closed
    executor_url = driver.command_executor._url
    return driver, executor_url


'''
def connect_to_selenium_session(session_id, executor_url):
    from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver

    # Save the original function, so we can revert our patch
    org_command_execute = RemoteWebDriver.execute

    def new_command_execute(self, command, params=None):
        if command == "newSession":
            # Mock the response
            return {'success': 0, 'value': None, 'sessionId': session_id}
        else:
            return org_command_execute(self, command, params)

    # Patch the function before creating the driver object
    RemoteWebDriver.execute = new_command_execute

    new_driver = webdriver.Remote(
        command_executor=executor_url, desired_capabilities={}
    )
    new_driver.session_id = session_id

    # Replace the patched function with original function
    RemoteWebDriver.execute = org_command_execute

    return new_driver
'''


async def scraper():
    capabilities = {
        "browserName": "firefox",
    }

    # command_executor = os.getenv('SELENIUM_CLUSTER')
    driver_obj, command_executor = _create_new_driver_connection()

    async with aiohttp.ClientSession() as session:
        remote = await Remote.create(
            command_executor, capabilities, session, reconnect=driver_obj.session_id
        )
        async with remote as driver:
            await driver.set_window_size(1920, 1080)
            await driver.get("http://www.youtube.com")
            print('Loaded:',await driver.get_title())
            #element = await driver.find_element_by_xpath('//input[@id="search"]')
            #await element.send_keys(search, Keys.ENTER)
            #video_titles = await driver.find_elements_by_xpath('//a[@id="video-title"]')
            link_elems = await driver.find_elements_by_xpath('//a')
            for e in link_elems[:5]:
                txt = await e.text()
                outer = await e.get_attribute('outerHTML')
                print(txt[:80])
                print(outer[:100])


#async def main(search_fields):
#    await asyncio.gather(*[scraper(search) for search in search_fields])


if __name__ == "__main__":

    #search_fields = ["Soccer", "Guatemala"]##, "Guitar", "Computer", "Van Gogh"]
    #asyncio.run(main(search_fields))

    asyncio.run(scraper())
