# -*- coding: utf-8 -*-
from __future__ import absolute_import
import copy
import json

import scrapy
from scrapy.core.engine import ExecutionEngine
from scrapy.utils.test import get_crawler

import scrapyjs
from scrapyjs.middleware import SplashMiddleware
from scrapyjs.request import SplashRequest


def _get_mw():
    crawler = get_crawler(settings_dict={
        'DOWNLOAD_HANDLERS': {'s3': None},  # for faster test running
    })
    if not hasattr(crawler, 'logformatter'):
        crawler.logformatter = None
    crawler.engine = ExecutionEngine(crawler, lambda _: None)
    # spider = crawler._create_spider("foo")
    return SplashMiddleware.from_crawler(crawler)


def test_nosplash():
    mw = _get_mw()
    req = scrapy.Request("http://example.com")
    old_meta = copy.deepcopy(req.meta)
    assert mw.process_request(req, None) is None
    assert old_meta == req.meta


def test_splash_request():
    mw = _get_mw()
    req = SplashRequest("http://example.com?foo=bar&url=1&wait=100")

    req2 = mw.process_request(req, None)
    assert req2 is not None
    assert req2 is not req
    assert req2.url == "http://127.0.0.1:8050/render.html"
    assert req2.headers == {'Content-Type': ['application/json']}
    assert req2.method == 'POST'

    expected_body = {'url': req.url}
    expected_body.update(SplashRequest.default_splash_meta['args'])
    assert json.loads(req2.body) == expected_body


def test_splash_request_no_url():
    mw = _get_mw()
    lua_source = "function main(splash) return {result='ok'} end"
    req1 = SplashRequest(meta={'splash': {
        'args': {'lua_source': lua_source},
        'endpoint': 'execute',
    }})
    req = mw.process_request(req1, None)
    assert req.url == 'http://127.0.0.1:8050/execute'
    assert json.loads(req.body) == {
        'url': 'about:blank',
        'lua_source': lua_source
    }


def test_override_splash_url():
    mw = _get_mw()
    req1 = scrapy.Request("http://example.com", meta={
        'splash': {
            'endpoint': 'render.png',
            'splash_url': 'http://splash.example.com'
        }
    })
    req = mw.process_request(req1, None)
    assert req.url == 'http://splash.example.com/render.png'
    assert json.loads(req.body) == {'url': req1.url}


def test_slot_policy_single_slot():
    mw = _get_mw()
    meta = {'splash': {
        'slot_policy': scrapyjs.SlotPolicy.SINGLE_SLOT
    }}

    req1 = scrapy.Request("http://example.com/path?key=value", meta=meta)
    req1 = mw.process_request(req1, None)

    req2 = scrapy.Request("http://fooexample.com/path?key=value", meta=meta)
    req2 = mw.process_request(req2, None)

    assert req1.meta.get('download_slot')
    assert req1.meta['download_slot'] == req2.meta['download_slot']


def test_slot_policy_per_domain():
    mw = _get_mw()
    meta = {'splash': {
        'slot_policy': scrapyjs.SlotPolicy.PER_DOMAIN
    }}

    req1 = scrapy.Request("http://example.com/path?key=value", meta=meta)
    req1 = mw.process_request(req1, None)

    req2 = scrapy.Request("http://example.com/path2", meta=meta)
    req2 = mw.process_request(req2, None)

    req3 = scrapy.Request("http://fooexample.com/path?key=value", meta=meta)
    req3 = mw.process_request(req3, None)

    assert req1.meta.get('download_slot')
    assert req3.meta.get('download_slot')

    assert req1.meta['download_slot'] == req2.meta['download_slot']
    assert req1.meta['download_slot'] != req3.meta['download_slot']


def test_slot_policy_scrapy_default():
    mw = _get_mw()
    req = scrapy.Request("http://example.com", meta = {'splash': {
        'slot_policy': scrapyjs.SlotPolicy.SCRAPY_DEFAULT
    }})
    req = mw.process_request(req, None)
    assert 'download_slot' not in req.meta


def test_adjust_timeout():
    mw = _get_mw()
    req1 = scrapy.Request("http://example.com", meta = {
        'splash': {'args': {'timeout': 60, 'html': 1}},

        # download_timeout is always present,
        # it is set by DownloadTimeoutMiddleware
        'download_timeout': 30,
    })
    req1 = mw.process_request(req1, None)
    assert req1.meta['download_timeout'] > 60

    req2 = scrapy.Request("http://example.com", meta = {
        'splash': {'args': {'html': 1}},
        'download_timeout': 30,
    })
    req2 = mw.process_request(req2, None)
    assert req2.meta['download_timeout'] == 30
