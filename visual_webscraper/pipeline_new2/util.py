from attrdict import AttrDict
import os

from PIL import Image
import trio

from webextractor.selenium_wrapper.js_scripts import PRELOAD_JS, PAGE_HEIGHT_JS


WINDOW_WIDTH = 1300

QUANTIZED_NUM_COLOURS = os.environ.get('PNG_QUANT_NUM_COLOURS', 16)
PNG_QUANT_PATH = os.environ.get('PNG_QUANT_PATH', '/usr/local/bin/pngquant')  # https://pngquant.org/


async def get_page_height(driver):
    val = await driver.execute_script2(PAGE_HEIGHT_JS)
    return int(round(val))


async def scroll_to(driver, position):
    await driver.execute_script2("window.scrollTo(0, %s);" % position)


async def resize_driver(driver, initial_delay=None):

    if initial_delay:
        await trio.sleep(initial_delay)

    page_height = await get_page_height(driver)
    resize_count = 0
    while True:
        pos = await get_page_height(driver) - 600
        await scroll_to(driver, pos)
        await trio.sleep(0.7)
        new_page_height = await get_page_height(driver)
        if new_page_height == page_height or resize_count > 7:
            page_height = new_page_height
            break
        resize_count += 1
        print('--- EXPANDING PAGE_HEIGHT ---')

    await scroll_to(driver, 0)
    await trio.sleep(0.1)

    window_height = page_height + 120

    await driver.set_window_size2(WINDOW_WIDTH, window_height)
    await trio.sleep(0.25)  # need to do it twice sometimes
    await driver.set_window_size2(WINDOW_WIDTH, window_height)


def create_pickleable_dict(elem, attrs):
    attr_dict = {}
    for attr in attrs:
        attr_dict[attr] = getattr(elem, attr)
    return attr_dict


def create_pickleable_attrdict(elem, attrs):
    return AttrDict(create_pickleable_dict(elem, attrs))


async def quantize_image(screenshot_path, num_colours=QUANTIZED_NUM_COLOURS):

    path, ext = os.path.splitext(screenshot_path)
    new_image_path = path + '-or8.png'

    if not os.path.exists(new_image_path):
        await trio.run_process(
            [PNG_QUANT_PATH, str(num_colours), '--nofs', screenshot_path]
        )

    return new_image_path


async def get_screenshot_data(driver, initial_delay=None):

    def get_image_height(filepath):
        ss_img = Image.open(filepath)
        height = ss_img.height
        ss_img.close()
        return height

    if initial_delay:
        trio.sleep(initial_delay)

    print('todo: replace driver.get_full_document_screenshot() with driver.save_full_page_screenshot() (officially supported in selenium 4, which will be released soon)')
    screenshot_fp = await driver.get_full_document_screenshot()
    screenshotQ_fp = await quantize_image(screenshot_fp)

    # height = get_image_height(screenshot_fp)
    height = await trio.to_thread.run_sync(
        get_image_height, screenshot_fp
    )

    return {
        'screenshot_fp': screenshot_fp,
        'screenshotQ_fp': screenshotQ_fp,
        'screenshot_height': height
    }


