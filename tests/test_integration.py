# -*- coding: utf-8 -*-
import scrapy
from pytest_twisted import inlineCallbacks
from twisted.web.resource import Resource
from w3lib.url import canonicalize_url

from scrapy_splash import SplashRequest
from .utils import crawl_items, requires_splash, HtmlResource

DEFAULT_SCRIPT = """
function main(splash)
  splash:init_cookies(splash.args.cookies)
  splash:go{
    splash.args.url,
    headers=splash.args.headers,
    http_method=splash.args.http_method,
    body=splash.args.body,
  }
  local wait = tonumber(splash.args.wait or 0.5)  
  assert(splash:wait(wait))

  local entries = splash:history()
  local last_response = entries[#entries].response
  return {
    url = splash:url(),
    headers = last_response.headers,
    http_status = last_response.status,
    cookies = splash:get_cookies(),
    html = splash:html(),
    args = splash.args,
    jsvalue = splash:evaljs("1+2"),
  }
end
"""


class HelloWorld(HtmlResource):
    html = """
    <html><body><script>document.write('hello world!');</script></body></html>
    """
    extra_headers = {'X-MyHeader': 'my value', 'Set-Cookie': 'sessionid=ABCD'}


class Http400Resource(HtmlResource):
    status_code = 400
    html = "Website returns HTTP 400 error"



class ManyCookies(Resource, object):
    class SetMyCookie(HtmlResource):
        html = "hello!"
        extra_headers = {'Set-Cookie': 'login=1'}

    def __init__(self):
        super(ManyCookies, self).__init__()
        self.putChild(b'', HelloWorld())
        self.putChild(b'login', self.SetMyCookie())



class ResponseSpider(scrapy.Spider):
    """ Make a request to URL, return Scrapy response """
    url = None

    def start_requests(self):
        yield SplashRequest(self.url)

    def parse(self, response):
        yield {'response': response}


@requires_splash
@inlineCallbacks
def test_basic(settings):
    items, url, crawler = yield crawl_items(ResponseSpider, HelloWorld,
                                            settings)
    assert len(items) == 1
    resp = items[0]['response']
    assert resp.url == url
    assert resp.css('body::text').extract_first().strip() == "hello world!"


@requires_splash
@inlineCallbacks
def test_reload(settings):

    class ReloadSpider(ResponseSpider):
        """ Make two requests to URL, store both responses.
        This spider activates both start_requests and parse methods,
        and checks that dupefilter takes fragment into account. """

        def parse(self, response):
            yield {'response': response}
            yield SplashRequest(self.url + '#foo')

    items, url, crawler = yield crawl_items(ReloadSpider, HelloWorld, settings)
    assert len(items) == 2
    assert crawler.stats.get_value('dupefilter/filtered') == 1
    resp = items[0]['response']
    assert resp.url == url
    assert resp.css('body::text').extract_first().strip() == "hello world!"
    assert resp.status == resp.splash_response_status == 200
    assert resp.headers == resp.splash_response_headers
    assert resp.splash_response_headers['Content-Type'] == b"text/html; charset=utf-8"

    resp2 = items[1]['response']
    assert resp2.body == resp.body
    assert resp2 is not resp
    assert resp2.url == resp.url + "#foo"


@requires_splash
@inlineCallbacks
def test_basic_lua(settings):

    class LuaScriptSpider(ResponseSpider):
        """ Make a request using a Lua script similar to the one from README
        """
        def start_requests(self):
            yield SplashRequest(self.url + "#foo", endpoint='execute',
                            args={'lua_source': DEFAULT_SCRIPT, 'foo': 'bar'})


    items, url, crawler = yield crawl_items(LuaScriptSpider, HelloWorld,
                                            settings)
    assert len(items) == 1
    resp = items[0]['response']
    assert resp.url == url + "/#foo"
    assert resp.status == resp.splash_response_status == 200
    assert resp.css('body::text').extract_first().strip() == "hello world!"
    assert resp.data['jsvalue'] == 3
    assert resp.headers['X-MyHeader'] == b'my value'
    assert resp.headers['Content-Type'] == b'text/html'
    assert resp.splash_response_headers['Content-Type'] == b'application/json'
    assert resp.data['args']['foo'] == 'bar'


@requires_splash
@inlineCallbacks
def test_bad_request(settings):
    class BadRequestSpider(ResponseSpider):
        custom_settings = {'HTTPERROR_ALLOW_ALL': True}

        def start_requests(self):
            yield SplashRequest(self.url, endpoint='execute',
                                args={'lua_source': DEFAULT_SCRIPT, 'wait': 'bar'})

    class GoodRequestSpider(ResponseSpider):
        custom_settings = {'HTTPERROR_ALLOW_ALL': True}

        def start_requests(self):
            yield SplashRequest(self.url, endpoint='execute',
                                args={'lua_source': DEFAULT_SCRIPT})


    items, url, crawler = yield crawl_items(BadRequestSpider, HelloWorld,
                                            settings)
    resp = items[0]['response']
    assert resp.status == 400
    assert resp.splash_response_status == 400

    items, url, crawler = yield crawl_items(GoodRequestSpider, Http400Resource,
                                            settings)
    resp = items[0]['response']
    assert resp.status == 400
    assert resp.splash_response_status == 200


@requires_splash
@inlineCallbacks
def test_cache_args(settings):

    class CacheArgsSpider(ResponseSpider):
        def _request(self, url):
            return SplashRequest(url, endpoint='execute',
                                 args={'lua_source': DEFAULT_SCRIPT, 'x': 'yy'},
                                 cache_args=['lua_source'])

        def start_requests(self):
            yield self._request(self.url)

        def parse(self, response):
            yield {'response': response}
            yield self._request(self.url + "#foo")


    items, url, crawler = yield crawl_items(CacheArgsSpider, HelloWorld,
                                            settings)
    assert len(items) == 2
    resp = items[0]['response']
    assert b"function main(splash)" in resp.request.body
    assert b"yy" in resp.request.body
    print(resp.body, resp.request.body)

    resp = items[1]['response']
    assert b"function main(splash)" not in resp.request.body
    assert b"yy" in resp.request.body
    print(resp.body, resp.request.body)


@requires_splash
@inlineCallbacks
def test_cookies(settings):

    # 64K for headers is over Twisted limit,
    # so if these headers are sent to Splash request would fail.
    BOMB = 'x' * 64000

    class LuaScriptSpider(ResponseSpider):
        """ Cookies must be sent to website, not to Splash """
        custom_settings = {
            'SPLASH_COOKIES_DEBUG': True,
            'COOKIES_DEBUG': True,
        }

        def start_requests(self):
            # cookies set without Splash should be still
            # sent to a remote website. FIXME: this is not the case.
            yield scrapy.Request(self.url + "/login", self.parse,
                                 cookies={'x-set-scrapy': '1'})

        def parse(self, response):
            yield SplashRequest(self.url + "#egg", self.parse_1,
                                endpoint='execute',
                                args={'lua_source': DEFAULT_SCRIPT},
                                cookies={'x-set-splash': '1'})

        def parse_1(self, response):
            yield {'response': response}
            yield SplashRequest(self.url + "#foo", self.parse_2,
                                endpoint='execute',
                                args={'lua_source': DEFAULT_SCRIPT})

        def parse_2(self, response):
            yield {'response': response}
            yield scrapy.Request(self.url, self.parse_3)

        def parse_3(self, response):
            # Splash (Twisted) drops requests with huge http headers,
            # but this one should work, as cookies are not sent
            # to Splash itself.
            yield {'response': response}
            yield SplashRequest(self.url + "#bar", self.parse_4,
                                endpoint='execute',
                                args={'lua_source': DEFAULT_SCRIPT},
                                cookies={'bomb': BOMB})

        def parse_4(self, response):
            yield {'response': response}


    def _cookie_dict(har_cookies):
        return {c['name']: c['value'] for c in har_cookies}

    items, url, crawler = yield crawl_items(LuaScriptSpider, ManyCookies,
                                            settings)
    assert len(items) == 4

    # cookie should be sent to remote website, not to Splash
    resp = items[0]['response']
    splash_request_headers = resp.request.headers
    cookies = resp.data['args']['cookies']
    print(splash_request_headers)
    print(cookies)
    assert _cookie_dict(cookies) == {
        # 'login': '1',   # FIXME
        'x-set-splash': '1'
    }
    assert splash_request_headers.get(b'Cookie') is None

    # new cookie should be also sent to remote website, not to Splash
    resp2 = items[1]['response']
    splash_request_headers = resp2.request.headers
    headers = resp2.data['args']['headers']
    cookies = resp2.data['args']['cookies']
    assert canonicalize_url(headers['Referer']) == canonicalize_url(url)
    assert _cookie_dict(cookies) == {
        # 'login': '1',
        'x-set-splash': '1',
        'sessionid': 'ABCD'
    }
    print(splash_request_headers)
    print(headers)
    print(cookies)
    assert splash_request_headers.get(b'Cookie') is None

    # TODO/FIXME: Cookies fetched when working with Splash should be picked up
    # by Scrapy
    resp3 = items[2]['response']
    splash_request_headers = resp3.request.headers
    cookie_header = splash_request_headers.get(b'Cookie')
    assert b'x-set-scrapy=1' in cookie_header
    assert b'login=1' in cookie_header
    assert b'x-set-splash=1' in cookie_header
    # assert b'sessionid=ABCD' in cookie_header  # FIXME

    # cookie bomb shouldn't cause problems
    resp4 = items[3]['response']
    splash_request_headers = resp4.request.headers
    cookies = resp4.data['args']['cookies']
    assert _cookie_dict(cookies) == {
        # 'login': '1',
        'x-set-splash': '1',
        'sessionid': 'ABCD',
        'bomb': BOMB,
    }
    assert splash_request_headers.get(b'Cookie') is None
