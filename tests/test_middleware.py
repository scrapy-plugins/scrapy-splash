# -*- coding: utf-8 -*-
from __future__ import absolute_import
import copy
import json
from twisted.trial import unittest

import scrapy
from scrapy.utils.test import get_crawler
from scrapy.utils.httpobj import urlparse_cached

import scrapyjs
from scrapyjs.middleware import SplashMiddleware
from scrapyjs.request import SplashRequest


class MockedSlot(object):

    def __init__(self, delay=0.0):
        self.delay = delay


class MockedDownloader(object):

    def __init__(self):
        self.slots = {}

    def _get_slot_key(self, request, spider):
        if 'download_slot' in request.meta:
            return request.meta['download_slot']

        key = urlparse_cached(request).hostname or ''
        return key


class MockedEngine(object):
    downloader = MockedDownloader()


class MiddlewareTest(unittest.TestCase):

    def setUp(self):
        self.crawler = get_crawler(settings_dict={
            'DOWNLOAD_HANDLERS': {'s3': None},  # for faster test running
        })
        if not hasattr(self.crawler, 'logformatter'):
            self.crawler.logformatter = None
        self.crawler.engine = MockedEngine()
        self.mw = SplashMiddleware.from_crawler(self.crawler)

    def test_nosplash(self):
        req = scrapy.Request("http://example.com")
        old_meta = copy.deepcopy(req.meta)
        assert self.mw.process_request(req, None) is None
        assert old_meta == req.meta

    def test_splash_request(self):
        req = SplashRequest("http://example.com?foo=bar&url=1&wait=100")

        req2 = self.mw.process_request(req, None)
        assert req2 is not None
        assert req2 is not req
        assert req2.url == "http://127.0.0.1:8050/render.html"
        assert req2.headers == {'Content-Type': ['application/json']}
        assert req2.method == 'POST'

        expected_body = {'url': req.url}
        expected_body.update(SplashRequest.default_splash_meta['args'])
        assert json.loads(req2.body) == expected_body

    def test_splash_request_no_url(self):
        lua_source = "function main(splash) return {result='ok'} end"
        req1 = SplashRequest(meta={'splash': {
            'args': {'lua_source': lua_source},
            'endpoint': 'execute',
        }})
        req = self.mw.process_request(req1, None)
        assert req.url == 'http://127.0.0.1:8050/execute'
        assert json.loads(req.body) == {
            'url': 'about:blank',
            'lua_source': lua_source
        }

    def test_override_splash_url(self):
        req1 = scrapy.Request("http://example.com", meta={
            'splash': {
                'endpoint': 'render.png',
                'splash_url': 'http://splash.example.com'
            }
        })
        req = self.mw.process_request(req1, None)
        assert req.url == 'http://splash.example.com/render.png'
        assert json.loads(req.body) == {'url': req1.url}

    def test_float_wait_arg(self):
        req1 = scrapy.Request("http://example.com", meta={
            'splash': {
                'endpoint': 'render.html',
                'args': {'wait': 0.5}
            }
        })
        req = self.mw.process_request(req1, None)
        assert json.loads(req.body) == {'url': req1.url, 'wait': 0.5}

    def test_slot_policy_single_slot(self):
        meta = {'splash': {
            'slot_policy': scrapyjs.SlotPolicy.SINGLE_SLOT
        }}

        req1 = scrapy.Request("http://example.com/path?key=value", meta=meta)
        req1 = self.mw.process_request(req1, None)

        req2 = scrapy.Request("http://fooexample.com/path?key=value", meta=meta)
        req2 = self.mw.process_request(req2, None)

        assert req1.meta.get('download_slot')
        assert req1.meta['download_slot'] == req2.meta['download_slot']

    def test_slot_policy_per_domain(self):
        meta = {'splash': {
            'slot_policy': scrapyjs.SlotPolicy.PER_DOMAIN
        }}

        req1 = scrapy.Request("http://example.com/path?key=value", meta=meta)
        req1 = self.mw.process_request(req1, None)

        req2 = scrapy.Request("http://example.com/path2", meta=meta)
        req2 = self.mw.process_request(req2, None)

        req3 = scrapy.Request("http://fooexample.com/path?key=value", meta=meta)
        req3 = self.mw.process_request(req3, None)

        assert req1.meta.get('download_slot')
        assert req3.meta.get('download_slot')

        assert req1.meta['download_slot'] == req2.meta['download_slot']
        assert req1.meta['download_slot'] != req3.meta['download_slot']

    def test_slot_policy_scrapy_default(self):
        req = scrapy.Request("http://example.com", meta = {'splash': {
            'slot_policy': scrapyjs.SlotPolicy.SCRAPY_DEFAULT
        }})
        req = self.mw.process_request(req, None)
        assert 'download_slot' not in req.meta

    def test_adjust_timeout(self):
        req1 = scrapy.Request("http://example.com", meta = {
            'splash': {'args': {'timeout': 60, 'html': 1}},

            # download_timeout is always present,
            # it is set by DownloadTimeoutMiddleware
            'download_timeout': 30,
        })
        req1 = self.mw.process_request(req1, None)
        assert req1.meta['download_timeout'] > 60

        req2 = scrapy.Request("http://example.com", meta = {
            'splash': {'args': {'html': 1}},
            'download_timeout': 30,
        })
        req2 = self.mw.process_request(req2, None)
        assert req2.meta['download_timeout'] == 30

    def test_spider_attribute(self):
        req_url = "http://scrapy.org"
        req1 = scrapy.Request(req_url)

        spider = self.crawler._create_spider("foo")
        spider.splash = {"args": {"images": 0}}

        req1 = self.mw.process_request(req1, spider)
        self.assertIn("_splash_processed", req1.meta)
        self.assertIn("render.json", req1.url)
        self.assertIn("url", json.loads(req1.body))
        self.assertEqual(json.loads(req1.body).get("url"), req_url)
        self.assertIn("images", json.loads(req1.body))

        # spider attribute blank middleware disabled
        spider.splash = {}
        req2 = self.mw.process_request(req1, spider)
        self.assertIsNone(req2)
