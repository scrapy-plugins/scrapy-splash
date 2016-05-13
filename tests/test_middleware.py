# -*- coding: utf-8 -*-
from __future__ import absolute_import
import copy
import json
import base64

import scrapy
from scrapy.core.engine import ExecutionEngine
from scrapy.utils.test import get_crawler
from scrapy.http import Response, TextResponse
from scrapy.downloadermiddlewares.httpcache import HttpCacheMiddleware

import scrapy_splash
from scrapy_splash.utils import to_native_str
from scrapy_splash import (
    SplashRequest,
    SplashMiddleware,
    SlotPolicy,
    SplashCookiesMiddleware,
    SplashDeduplicateArgsMiddleware,
)


def _get_crawler(settings_dict):
    settings_dict = settings_dict.copy()
    settings_dict['DOWNLOAD_HANDLERS'] = {'s3': None}  # for faster test running
    crawler = get_crawler(settings_dict=settings_dict)
    if not hasattr(crawler, 'logformatter'):
        crawler.logformatter = None
    crawler.engine = ExecutionEngine(crawler, lambda _: None)
    # spider = crawler._create_spider("foo")
    return crawler


def _get_mw():
    crawler = _get_crawler({})
    return SplashMiddleware.from_crawler(crawler)


def _get_cookie_mw():
    return SplashCookiesMiddleware(debug=True)


def test_nosplash():
    mw = _get_mw()
    cookie_mw = _get_cookie_mw()
    req = scrapy.Request("http://example.com")
    old_meta = copy.deepcopy(req.meta)

    assert cookie_mw.process_request(req, None) is None
    assert mw.process_request(req, None) is None
    assert old_meta == req.meta

    # response is not changed
    response = Response("http://example.com", request=req)
    response2 = mw.process_response(req, response, None)
    response3 = cookie_mw.process_response(req, response, None)
    assert response2 is response
    assert response3 is response
    assert response3.url == "http://example.com"


def test_splash_request():
    mw = _get_mw()
    cookie_mw = _get_cookie_mw()

    req = SplashRequest("http://example.com?foo=bar&url=1&wait=100")
    assert repr(req) == "<GET http://example.com?foo=bar&url=1&wait=100>"

    # check request preprocessing
    req2 = cookie_mw.process_request(req, None) or req
    req2 = mw.process_request(req2, None) or req2
    assert req2 is not None
    assert req2 is not req
    assert req2.url == "http://127.0.0.1:8050/render.html"
    assert req2.headers == {b'Content-Type': [b'application/json']}
    assert req2.method == 'POST'
    assert isinstance(req2, SplashRequest)
    assert repr(req2) == "<GET http://example.com?foo=bar&url=1&wait=100 via http://127.0.0.1:8050/render.html>"

    expected_body = {'url': req.url}
    assert json.loads(to_native_str(req2.body)) == expected_body

    # check response post-processing
    response = TextResponse("http://127.0.0.1:8050/render.html",
                            # Scrapy doesn't pass request to constructor
                            # request=req2,
                            headers={b'Content-Type': b'text/html'},
                            body=b"<html><body>Hello</body></html>")
    response2 = mw.process_response(req2, response, None)
    response2 = cookie_mw.process_response(req2, response2, None)
    assert isinstance(response2, scrapy_splash.SplashTextResponse)
    assert response2 is not response
    assert response2.real_url == req2.url
    assert response2.url == req.url
    assert response2.body == b"<html><body>Hello</body></html>"
    assert response2.css("body").extract_first() == "<body>Hello</body>"
    assert response2.headers == {b'Content-Type': [b'text/html']}

    # check .replace method
    response3 = response2.replace(status=404)
    assert response3.status == 404
    assert isinstance(response3, scrapy_splash.SplashTextResponse)
    for attr in ['url', 'real_url', 'headers', 'body']:
        assert getattr(response3, attr) == getattr(response2, attr)


def test_dont_process_response():
    mw = _get_mw()
    req = SplashRequest("http://example.com/",
        endpoint="render.html",
        dont_process_response=True,
    )
    req2 = mw.process_request(req, None)
    resp = Response("http://example.com/")
    resp2 = mw.process_response(req2, resp, None)
    assert resp2.__class__ is Response
    assert resp2 is resp


def test_splash_request_parameters():
    mw = _get_mw()
    cookie_mw = _get_cookie_mw()

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
        },
        magic_response=False,
        headers={'X-My-Header': 'value'}
    )
    req2 = cookie_mw.process_request(req, None) or req
    req2 = mw.process_request(req2, None)
    assert req2.meta['splash'] == {
        'endpoint': 'execute',
        'splash_url': "http://mysplash.example.com",
        'slot_policy': SlotPolicy.SINGLE_SLOT,
        'splash_headers': {'X-My-Header': 'value'},
        'magic_response': False,
        'session_id': 'default',
        'http_status_from_error_code': True,
        'args': {
            'url': "http://example.com/#!start",
            'http_method': 'POST',
            'body': 'foo=bar',
            'cookies': [],
            'lua_source': 'function main() end',
            'myarg': 3.0,
            'headers': {
                'X-My-Header': 'value',
            }
        },
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
                            # Scrapy doesn't pass request to constructor
                            # request=req2,
                            headers={b'Content-Type': b'application/json'},
                            body=res_body.encode('utf8'))
    response2 = mw.process_response(req2, response, None)
    response2 = cookie_mw.process_response(req2, response2, None)
    assert isinstance(response2, scrapy_splash.SplashJsonResponse)
    assert response2 is not response
    assert response2.real_url == req2.url
    assert response2.url == req.meta['splash']['args']['url']
    assert response2.data == res
    assert response2.body == res_body.encode('utf8')
    assert response2.text == response2.body_as_unicode() == res_body
    assert response2.encoding == 'utf8'
    assert response2.headers == {b'Content-Type': [b'application/json']}
    assert response2.status == 200


def test_magic_response():
    mw = _get_mw()
    cookie_mw = _get_cookie_mw()

    req = SplashRequest('http://example.com/',
                        endpoint='execute',
                        args={'lua_source': 'function main() end'},
                        magic_response=True,
                        cookies=[{'name': 'foo', 'value': 'bar'}])
    req = cookie_mw.process_request(req, None) or req
    req = mw.process_request(req, None) or req

    resp_data = {
        'url': "http://exmaple.com/#id42",
        'html': '<html><body>Hello 404</body></html>',
        'http_status': 404,
        'headers': [
            {'name': 'Content-Type', 'value': "text/html"},
            {'name': 'X-My-Header', 'value': "foo"},
            {'name': 'Set-Cookie', 'value': "bar=baz"},
        ],
        'cookies': [
            {'name': 'foo', 'value': 'bar'},
            {'name': 'bar', 'value': 'baz', 'domain': '.example.com'},
            {'name': 'session', 'value': '12345', 'path': '/',
             'expires': '2055-07-24T19:20:30Z'},
        ],
    }
    resp = TextResponse("http://mysplash.example.com/execute",
                        headers={b'Content-Type': b'application/json'},
                        body=json.dumps(resp_data).encode('utf8'))
    resp2 = mw.process_response(req, resp, None)
    resp2 = cookie_mw.process_response(req, resp2, None)
    assert isinstance(resp2, scrapy_splash.SplashJsonResponse)
    assert resp2.data == resp_data
    assert resp2.body == b'<html><body>Hello 404</body></html>'
    assert resp2.text == '<html><body>Hello 404</body></html>'
    assert resp2.headers == {
        b'Content-Type': [b'text/html'],
        b'X-My-Header': [b'foo'],
        b'Set-Cookie': [b'bar=baz'],
    }
    assert resp2.status == 404
    assert resp2.url == "http://exmaple.com/#id42"
    assert len(resp2.cookiejar) == 3
    cookies = [c for c in resp2.cookiejar]
    assert {(c.name, c.value) for c in cookies} == {
        ('bar', 'baz'),
        ('foo', 'bar'),
        ('session', '12345')
    }

    # send second request using the same session and check the resulting cookies
    req = SplashRequest('http://example.com/foo',
                        endpoint='execute',
                        args={'lua_source': 'function main() end'},
                        magic_response=True,
                        cookies={'spam': 'ham'})
    req = cookie_mw.process_request(req, None) or req
    req = mw.process_request(req, None) or req

    resp_data = {
        'html': '<html><body>Hello</body></html>',
        'headers': [
            {'name': 'Content-Type', 'value': "text/html"},
            {'name': 'X-My-Header', 'value': "foo"},
            {'name': 'Set-Cookie', 'value': "bar=baz"},
        ],
        'cookies': [
            {'name': 'spam', 'value': 'ham'},
            {'name': 'egg', 'value': 'spam'},
            {'name': 'bar', 'value': 'baz', 'domain': '.example.com'},
           #{'name': 'foo', 'value': ''},  -- this won't be in response
            {'name': 'session', 'value': '12345', 'path': '/',
             'expires': '2056-07-24T19:20:30Z'},
        ],
    }
    resp = TextResponse("http://mysplash.example.com/execute",
                        headers={b'Content-Type': b'application/json'},
                        body=json.dumps(resp_data).encode('utf8'))
    resp2 = mw.process_response(req, resp, None)
    resp2 = cookie_mw.process_response(req, resp2, None)
    assert isinstance(resp2, scrapy_splash.SplashJsonResponse)
    assert resp2.data == resp_data
    cookies = [c for c in resp2.cookiejar]
    assert {c.name for c in cookies} == {'session', 'egg', 'bar', 'spam'}
    for c in cookies:
        if c.name == 'session':
            assert c.expires == 2731692030
        if c.name == 'spam':
            assert c.value == 'ham'


def test_cookies():
    mw = _get_mw()
    cookie_mw = _get_cookie_mw()

    def request_with_cookies(cookies):
        req = SplashRequest(
            'http://example.com/foo',
            endpoint='execute',
            args={'lua_source': 'function main() end'},
            magic_response=True,
            cookies=cookies)
        req = cookie_mw.process_request(req, None) or req
        req = mw.process_request(req, None) or req
        return req

    def response_with_cookies(req, cookies):
        resp_data = {
            'html': '<html><body>Hello</body></html>',
            'headers': [],
            'cookies': cookies,
        }
        resp = TextResponse(
            'http://mysplash.example.com/execute',
            headers={b'Content-Type': b'application/json'},
            body=json.dumps(resp_data).encode('utf8'))
        resp = mw.process_response(req, resp, None)
        resp = cookie_mw.process_response(req, resp, None)
        return resp

    # Concurent requests
    req1 = request_with_cookies({'spam': 'ham'})
    req2 = request_with_cookies({'bom': 'bam'})
    resp1 = response_with_cookies(req1, [
        {'name': 'spam', 'value': 'ham'},
        {'name': 'spam_x', 'value': 'ham_x'},
    ])
    resp2 = response_with_cookies(req2, [
        {'name': 'spam', 'value': 'ham'},  # because req2 was made after req1
        {'name': 'bom_x', 'value': 'bam_x'},
    ])
    assert resp1.cookiejar is resp2.cookiejar
    cookies = {c.name: c.value for c in resp1.cookiejar}
    assert cookies == {'spam': 'ham', 'spam_x': 'ham_x', 'bom_x': 'bam_x'}

    # Removing already removed
    req1 = request_with_cookies({'spam': 'ham'})
    req2 = request_with_cookies({'spam': 'ham', 'pom': 'pam'})
    resp2 = response_with_cookies(req2, [
        {'name': 'pom', 'value': 'pam'},
    ])
    resp1 = response_with_cookies(req1, [])
    assert resp1.cookiejar is resp2.cookiejar
    cookies = {c.name: c.value for c in resp1.cookiejar}
    assert cookies == {'pom': 'pam'}


def test_magic_response2():
    # check 'body' handling and another 'headers' format
    mw = _get_mw()
    req = SplashRequest('http://example.com/', magic_response=True,
                        headers={'foo': 'bar'}, dont_send_headers=True)
    req = mw.process_request(req, None)
    assert 'headers' not in req.meta['splash']['args']

    resp_data = {
        'body': base64.b64encode(b"binary data").decode('ascii'),
        'headers': {'Content-Type': 'text/plain'},
    }
    resp = TextResponse("http://mysplash.example.com/execute",
                        headers={b'Content-Type': b'application/json'},
                        body=json.dumps(resp_data).encode('utf8'))
    resp2 = mw.process_response(req, resp, None)
    assert resp2.data == resp_data
    assert resp2.body == b'binary data'
    assert resp2.headers == {b'Content-Type': [b'text/plain']}
    assert resp2.status == 200
    assert resp2.url == "http://example.com/"


def test_unicode_url():
    mw = _get_mw()
    req = SplashRequest(
        # note unicode URL
        u"http://example.com/", endpoint='execute')
    req2 = mw.process_request(req, None)
    res = {'html': '<html><body>Hello</body></html>'}
    res_body = json.dumps(res)
    response = TextResponse("http://mysplash.example.com/execute",
                            # Scrapy doesn't pass request to constructor
                            # request=req2,
                            headers={b'Content-Type': b'application/json'},
                            body=res_body.encode('utf8'))
    response2 = mw.process_response(req2, response, None)
    assert response2.url == "http://example.com/"


def test_magic_response_http_error():
    mw = _get_mw()
    req = SplashRequest('http://example.com/foo')
    req = mw.process_request(req, None)

    resp_data = {
        "info": {
            "error": "http404",
            "message": "Lua error: [string \"function main(splash)\r...\"]:3: http404",
            "line_number": 3,
            "type": "LUA_ERROR",
            "source": "[string \"function main(splash)\r...\"]"
        },
        "description": "Error happened while executing Lua script",
        "error": 400,
        "type": "ScriptError"
    }
    resp = TextResponse("http://mysplash.example.com/execute",
                        headers={b'Content-Type': b'application/json'},
                        body=json.dumps(resp_data).encode('utf8'))
    resp = mw.process_response(req, resp, None)
    assert resp.data == resp_data
    assert resp.status == 404
    assert resp.url == "http://example.com/foo"


def test_magic_response_caching(tmpdir):
    # prepare middlewares
    spider = scrapy.Spider(name='foo')
    crawler = _get_crawler({
        'HTTPCACHE_DIR': str(tmpdir.join('cache')),
        'HTTPCACHE_STORAGE': 'scrapy_splash.SplashAwareFSCacheStorage',
        'HTTPCACHE_ENABLED': True
    })
    cache_mw = HttpCacheMiddleware.from_crawler(crawler)
    mw = _get_mw()
    cookie_mw = _get_cookie_mw()

    def _get_req():
        return SplashRequest(
            url="http://example.com",
            endpoint='execute',
            magic_response=True,
            args={'lua_source': 'function main(splash) end'},
        )

    # Emulate Scrapy middleware chain.

    # first call
    req = _get_req()
    req = cookie_mw.process_request(req, spider) or req
    req = mw.process_request(req, spider)
    req = cache_mw.process_request(req, spider) or req
    assert isinstance(req, scrapy.Request)  # first call; the cache is empty

    resp_data = {
        'html': "<html><body>Hello</body></html>",
        'render_time': 0.5,
    }
    resp_body = json.dumps(resp_data).encode('utf8')
    resp = TextResponse("http://example.com",
                        headers={b'Content-Type': b'application/json'},
                        body=resp_body)

    resp2 = cache_mw.process_response(req, resp, spider)
    resp3 = mw.process_response(req, resp2, spider)
    resp3 = cookie_mw.process_response(req, resp3, spider)

    assert resp3.text == "<html><body>Hello</body></html>"
    assert resp3.css("body").extract_first() == "<body>Hello</body>"
    assert resp3.data['render_time'] == 0.5

    # second call
    req = _get_req()
    req = cookie_mw.process_request(req, spider) or req
    req = mw.process_request(req, spider)
    cached_resp = cache_mw.process_request(req, spider) or req

    # response should be from cache:
    assert cached_resp.__class__ is TextResponse
    assert cached_resp.body == resp_body
    resp2_1 = cache_mw.process_response(req, cached_resp, spider)
    resp3_1 = mw.process_response(req, resp2_1, spider)
    resp3_1 = cookie_mw.process_response(req, resp3_1, spider)

    assert isinstance(resp3_1, scrapy_splash.SplashJsonResponse)
    assert resp3_1.body == b"<html><body>Hello</body></html>"
    assert resp3_1.text == "<html><body>Hello</body></html>"
    assert resp3_1.css("body").extract_first() == "<body>Hello</body>"
    assert resp3_1.data['render_time'] == 0.5
    assert resp3_1.headers[b'Content-Type'] == b'text/html; charset=utf-8'


def test_cache_args():
    spider = scrapy.Spider(name='foo')
    mw = _get_mw()
    mw.crawler.spider = spider
    mw.spider_opened(spider)
    dedupe_mw = SplashDeduplicateArgsMiddleware()

    # ========= Send first request - it should use save_args:
    lua_source = 'function main(splash) end'
    req = SplashRequest('http://example.com/foo',
                        endpoint='execute',
                        args={'lua_source': lua_source},
                        cache_args=['lua_source'])

    assert req.meta['splash']['args']['lua_source'] == lua_source
    # <---- spider
    req, = list(dedupe_mw.process_start_requests([req], spider))
    # ----> scheduler
    assert req.meta['splash']['args']['lua_source'] != lua_source
    assert list(mw._argument_values.values()) == [lua_source]
    assert list(mw._argument_values.keys()) == [req.meta['splash']['args']['lua_source']]
    # <---- scheduler
    # process request before sending it to the downloader
    req = mw.process_request(req, spider) or req
    # -----> downloader
    assert req.meta['splash']['args']['lua_source'] == lua_source
    assert req.meta['splash']['args']['save_args'] == ['lua_source']
    assert 'load_args' not in req.meta['splash']['args']
    assert req.meta['splash']['_local_arg_fingerprints'] == {
        'lua_source': list(mw._argument_values.keys())[0]
    }
    # <---- downloader
    resp_body = b'{}'
    resp = TextResponse("http://example.com",
                        headers={
                            b'Content-Type': b'application/json',
                            b'X-Splash-Saved-Arguments': b'lua_source=ba001160ef96fe2a3f938fea9e6762e204a562b3'
                        },
                        body=resp_body)
    resp = mw.process_response(req, resp, None)

    # ============ Send second request - it should use load_args
    req2 = SplashRequest('http://example.com/bar',
                        endpoint='execute',
                        args={'lua_source': lua_source},
                        cache_args=['lua_source'])
    req2, item = list(dedupe_mw.process_spider_output(resp, [req2, {'key': 'value'}], spider))
    assert item == {'key': 'value'}
    # ----> scheduler
    assert req2.meta['splash']['args']['lua_source'] != lua_source
    # <---- scheduler
    # process request before sending it to the downloader
    req2 = mw.process_request(req2, spider) or req2
    # -----> downloader
    assert req2.meta['splash']['args']['load_args'] == {"lua_source": "ba001160ef96fe2a3f938fea9e6762e204a562b3"}
    assert "lua_source" not in req2.meta['splash']['args']
    assert "save_args" not in req2.meta['splash']['args']
    assert json.loads(req2.body.decode('utf8')) == {
        'load_args': {'lua_source': 'ba001160ef96fe2a3f938fea9e6762e204a562b3'},
        'url': 'http://example.com/bar'
    }
    # <---- downloader
    resp = TextResponse("http://example.com/bar",
                        headers={b'Content-Type': b'application/json'},
                        body=b'{}')
    resp = mw.process_response(req, resp, spider)

    # =========== Third request is dispatched to another server where
    # =========== arguments are expired:
    req3 = SplashRequest('http://example.com/baz',
                         endpoint='execute',
                         args={'lua_source': lua_source},
                         cache_args=['lua_source'])
    req3, = list(dedupe_mw.process_spider_output(resp, [req3], spider))
    # ----> scheduler
    assert req3.meta['splash']['args']['lua_source'] != lua_source
    # <---- scheduler
    req3 = mw.process_request(req3, spider) or req3
    # -----> downloader
    assert json.loads(req3.body.decode('utf8')) == {
        'load_args': {'lua_source': 'ba001160ef96fe2a3f938fea9e6762e204a562b3'},
        'url': 'http://example.com/baz'
    }
    # <---- downloader

    resp_body = json.dumps({
        "type": "ExpiredArguments",
        "description": "Arguments stored with ``save_args`` are expired",
        "info": {"expired": ["html"]},
        "error": 498
    })
    resp = TextResponse("127.0.0.1:8050",
                        headers={b'Content-Type': b'application/json'},
                        status=498,
                        body=resp_body.encode('utf8'))
    req4 = mw.process_response(req3, resp, spider)
    assert isinstance(req4, SplashRequest)

    # process this request again
    req4, = list(dedupe_mw.process_spider_output(resp, [req4], spider))
    req4 = mw.process_request(req4, spider) or req4

    # it should become save_args request after all middlewares
    assert json.loads(req4.body.decode('utf8')) == {
        'lua_source': 'function main(splash) end',
        'save_args': ['lua_source'],
        'url': 'http://example.com/baz'
    }
    assert mw._remote_keys == {}



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
        'slot_policy': scrapy_splash.SlotPolicy.SINGLE_SLOT
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
        'slot_policy': scrapy_splash.SlotPolicy.PER_DOMAIN
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
        'slot_policy': scrapy_splash.SlotPolicy.SCRAPY_DEFAULT
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
