# -*- coding: utf-8 -*-
from __future__ import absolute_import
import copy
import json

import scrapy
from scrapy.core.engine import ExecutionEngine
from scrapy.utils.test import get_crawler
from scrapy.http import Response, TextResponse
try:
    from scrapy.utils.python import to_native_str
except ImportError:
    from scrapy.utils.python import str_to_unicode as to_native_str

import scrapyjs
from scrapyjs.middleware import SplashMiddleware, SlotPolicy
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

    # response is not changed
    response = Response("http://example.com", request=req)
    response2 = mw.process_response(req, response, None)
    assert response2 is response
    assert response2.url == "http://example.com"


def test_splash_request():
    mw = _get_mw()
    req = SplashRequest("http://example.com?foo=bar&url=1&wait=100")

    # check request preprocessing
    req2 = mw.process_request(req, None)
    assert req2 is not None
    assert req2 is not req
    assert req2.url == "http://127.0.0.1:8050/render.html"
    assert req2.headers == {b'Content-Type': [b'application/json']}
    assert req2.method == 'POST'
    assert isinstance(req2, SplashRequest)

    expected_body = {'url': req.url}
    assert json.loads(to_native_str(req2.body)) == expected_body

    # check response post-processing
    response = TextResponse("http://127.0.0.1:8050/render.html",
                            request=req2,
                            headers={b'Content-Type': b'text/html'},
                            body=b"<html><body>Hello</body></html>")
    response2 = mw.process_response(req2, response, None)
    assert isinstance(response2, scrapyjs.SplashTextResponse)
    assert response2 is not response
    assert response2.real_url == req2.url
    assert response2.url == req.url
    assert response2.body == b"<html><body>Hello</body></html>"
    assert response2.css("body").extract_first() == "<body>Hello</body>"

    # check .replace method
    response3 = response2.replace(status=404)
    assert response3.status == 404
    assert isinstance(response3, scrapyjs.SplashTextResponse)
    for attr in ['url', 'real_url', 'headers', 'body']:
        assert getattr(response3, attr) == getattr(response2, attr)


def test_splash_requst_parameters():
    mw = _get_mw()

    def cb():
        pass

    req = SplashRequest("http://example.com/#!start", cb, 'POST',
        body="foo=bar",
        splash_url="http://mysplash.example.com",
        slot_policy=SlotPolicy.SINGLE_SLOT,
        endpoint="execute",
        splash_headers={'X-My-Header': 'value'},
        args={
            "lua_source": "function main() end",
            "myarg": 3.0,
        }
    )
    req2 = mw.process_request(req, None)
    assert req2.meta['splash'] == {
        'endpoint': 'execute',
        'splash_url': "http://mysplash.example.com",
        'slot_policy': SlotPolicy.SINGLE_SLOT,
        'splash_headers': {'X-My-Header': 'value'},
        'args': {
            'url': "http://example.com/#!start",
            'http_method': 'POST',
            'body': 'foo=bar',
            'lua_source': 'function main() end',
            'myarg': 3.0,
        }
    }
    assert req2.callback == cb
    assert req2.headers == {
        b'Content-Type': [b'application/json'],
        b'X-My-Header': [b'value'],
    }

    # check response post-processing
    res = {
        'html': '<html><body>Hello</body></html>',
        'num_divs': 0.0,
    }
    res_body = json.dumps(res)
    response = TextResponse("http://mysplash.example.com/execute",
                            request=req2,
                            headers={b'Content-Type': b'application/json'},
                            body=res_body.encode('utf8'))
    response2 = mw.process_response(req2, response, None)
    assert isinstance(response2, scrapyjs.SplashJsonResponse)
    assert response2 is not response
    assert response2.real_url == req2.url
    assert response2.url == req.meta['splash']['args']['url']
    assert response2.data == res
    assert response2.body == res_body.encode('utf8')
    assert response2.text == response2.body_as_unicode() == res_body
    assert response2.encoding == 'utf8'


def test_splash_request_no_url():
    mw = _get_mw()
    lua_source = "function main(splash) return {result='ok'} end"
    req1 = SplashRequest(meta={'splash': {
        'args': {'lua_source': lua_source},
        'endpoint': 'execute',
    }})
    req = mw.process_request(req1, None)
    assert req.url == 'http://127.0.0.1:8050/execute'
    assert json.loads(to_native_str(req.body)) == {
        'url': 'about:blank',
        'lua_source': lua_source
    }


def test_post_request():
    mw = _get_mw()
    for body in [b'', b'foo=bar']:
        req1 = scrapy.Request("http://example.com",
                              method="POST",
                              body=body,
                              meta={'splash': {'endpoint': 'render.html'}})
        req = mw.process_request(req1, None)
        assert json.loads(to_native_str(req.body)) == {
            'url': 'http://example.com',
            'http_method': 'POST',
            'body': to_native_str(body),
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
    assert json.loads(to_native_str(req.body)) == {'url': req1.url}


def test_url_with_fragment():
    mw = _get_mw()
    url = "http://example.com#id1"
    req = scrapy.Request("http://example.com", meta={
        'splash': {'args': {'url': url}}
    })
    req = mw.process_request(req, None)
    assert json.loads(to_native_str(req.body)) == {'url': url}


def test_splash_request_url_with_fragment():
    mw = _get_mw()
    url = "http://example.com#id1"
    req = SplashRequest(url)
    req = mw.process_request(req, None)
    assert json.loads(to_native_str(req.body)) == {'url': url}


def test_float_wait_arg():
    mw = _get_mw()
    req1 = scrapy.Request("http://example.com", meta={
        'splash': {
            'endpoint': 'render.html',
            'args': {'wait': 0.5}
        }
    })
    req = mw.process_request(req1, None)
    assert json.loads(to_native_str(req.body)) == {'url': req1.url, 'wait': 0.5}


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
