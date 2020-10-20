import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import uuid

import faust
from typing import List

from util_core.util.urls_util import url_host, url_base
from webextractor.selenium_wrapper.main import FirefoxDriverWrapper
from webextractor.selenium_wrapper.elements import WebElementWrapper, LinkWebElementWrapper
from webextractor.selenium_wrapper.preloading import (
    get_rect_multiple, get_multiple_outer__chunk,
    get_xpaths_multiple, get_computed_css_multiple
)
from webextractor.selenium_wrapper.preloading import get_parent_paths_multiple as _get_parent_paths_multiple
from webextractor.pipeline_new.util import resize_driver, get_screenshot_data


thread_pool = ThreadPoolExecutor(max_workers=8)

app = faust.App(
    'webextractor-pipeline',
    broker='kafka://localhost:9092',
    value_serializer='raw',
    topic_partitions=1,
)


# topic = app.topic("slow-process", value_type=int)


class PageRequest(faust.Record, serializer='json'):
    task_uid: str
    page_url: str


class ElemBatch(faust.Record, serializer='raw'):
    pipeline_uid: str
    driver: FirefoxDriverWrapper
    link_elems: LinkWebElementWrapper


class DataBatch(faust.Record, serializer='raw'):  # or json?
    pipeline_uid: str
    elem_ids: List[str]
    outer_htmls: List[str] = None
    ancestor_paths: List[str] = None


page_request_topic = app.topic('page_requests', value_type=PageRequest)


def _launch_selenium(page_url):
    driver = FirefoxDriverWrapper()
    driver.get(page_url)
    return driver


def get_parent_paths_multiple(driver, driver_elems):
    ancestor_paths = _get_parent_paths_multiple(driver, driver_elems, wrap=True)
    for path in ancestor_paths:
        for elem_dict in path:
            elem = elem_dict['elem']
            elem_dict['elem'] = elem.create_pickleable_attrdict(
                ['id', 'tag_class_str', 'attrs']
            )
    return ancestor_paths


@app.agent(page_request_topic)
async def launch_selenium(page_requests):
    async for page_req in page_requests:  # page_requests.group_by(PageRequest.task_uid):
        driver = await app.loop.run_in_executor(
            thread_pool, _launch_selenium, page_req
        )
        await asyncio.sleep(1)
        link_elems = await app.loop.run_in_executor(
            thread_pool, driver.find_elements_by_xpath, '//a'
        )
        context = {
            'page_url': page_req.page_url,
            'page_url_host': url_host(page_req.page_url),
            'page_host_base': url_base(page_req.page_url),
            'pipeline_session_uid': uuid.uuid4().hex
        }
        driver_record = ElemBatch(
            pipeline_uid=uuid.uuid4().hex,
            driver=driver,
            context=context,
            link_elems=link_elems
        )
        get_outer_html_and_ancestors.send(driver_record)
        resize_browser.send(driver_record)


@app.agent()
async def get_outer_html_and_ancestors(drivers):
    async for driver_record in drivers.group_by(ElemBatch.pipeline_uid):
        elem_ids = [e.id for e in driver_record.link_elems]
        outer_htmls = await app.loop.run_in_executor(
            thread_pool, get_multiple_outer__chunk,
            driver_record.driver, driver_record.link_elems
        )
        ancestor_paths = await app.loop.run_in_executor(
            thread_pool, get_parent_paths_multiple,
            driver_record.driver, driver_record.link_elems
        )
        batch = DataBatch(
            pipeline_uid=driver_record.pipeline_uid,
            elem_ids=elem_ids,
            outer_htmls=outer_htmls,
            ancestor_paths=ancestor_paths
        )
        import pdb; pdb.set_trace()
        print()


@app.agent()
async def resize_browser(drivers):
    async for driver_record in drivers.group_by(ElemBatch.pipeline_uid):
        await app.loop.run_in_executor(
            thread_pool, resize_driver,
            driver_record.driver, 0.6
        )
        await asyncio.sleep(0.5)
        link_elems = await app.loop.run_in_executor(
            thread_pool, driver_record.driver.find_elements_by_xpath, '//a'
        )
        link_elem_ids = [e.id for e in link_elems]
        new_elems = [e for e in link_elems if e.id not in link_elem_ids]
        if new_elems:
            new_driver_record = ElemBatch(
                pipeline_uid=driver_record.pipeline_uid,
                driver=driver_record.driver,
                context=driver_record.context,
                link_elems=new_elems
            )
            get_outer_html_and_ancestors.send(new_driver_record)

        # todo: send event notifying that resize is complete and whether or not to expect a second batch?


'''
resize_task.wait()
context['page_height'] = driver.get_page_height()

new_elems = [
    e for e in driver.find_elements_by_xpath('//a')
    if e.id not in coll.elem_ids
]
if new_elems:
    t1_a = process(
        process_ctx, new_elems, get_multiple_outer__chunk, 'outerHTML'
    )
    t2_a = process(
        process_ctx, new_elems, get_parent_paths_multiple, 'ancestor_path'
    )
    process_tasks.extend(t1_a + t2_a)
    coll.add_elems(new_elems)

'''

# if __name__ == "__main__":
#    app.main()
