# -*- coding: utf-8 -*-
import os
import pytest
from pytest_twisted import inlineCallbacks
from twisted.internet.defer import returnValue
from twisted.web.resource import Resource
from scrapy.crawler import Crawler

from scrapy_splash.utils import to_bytes
from tests.mockserver import MockServer


requires_splash = pytest.mark.skipif(
    not os.environ.get('SPLASH_URL', ''),
    reason="set SPLASH_URL environment variable to run integrational tests"
)


class HtmlResource(Resource):
    isLeaf = True
    content_type = 'text/html'
    html = ''
    extra_headers = {}
    status_code = 200

    def render_GET(self, request):
        request.setHeader(b'content-type', to_bytes(self.content_type))
        for name, value in self.extra_headers.items():
            request.setHeader(to_bytes(name), to_bytes(value))
        request.setResponseCode(self.status_code)
        return to_bytes(self.html)


@inlineCallbacks
def crawl_items(spider_cls, resource_cls, settings, spider_kwargs=None):
    """ Use spider_cls to crawl resource_cls. URL of the resource is passed
    to the spider as ``url`` argument.
    Return ``(items, resource_url, crawler)`` tuple.
    """
    spider_kwargs = {} if spider_kwargs is None else spider_kwargs
    crawler = make_crawler(spider_cls, settings)
    with MockServer(resource_cls) as s:
        root_url = s.root_url
        yield crawler.crawl(url=root_url, **spider_kwargs)
    result = crawler.spider.collected_items, s.root_url, crawler
    returnValue(result)


def make_crawler(spider_cls, settings):
    if not getattr(spider_cls, 'name', None):
        class Spider(spider_cls):
            name = 'test_spider'
        Spider.__name__ = spider_cls.__name__
        Spider.__module__ = spider_cls.__module__
        spider_cls = Spider
    return Crawler(spider_cls, settings)


class CollectorPipeline:
    def process_item(self, item, spider):
        if not hasattr(spider, 'collected_items'):
            spider.collected_items = []
        spider.collected_items.append(item)
        return item
