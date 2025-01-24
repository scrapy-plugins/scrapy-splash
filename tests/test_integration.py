# -*- coding: utf-8 -*-
import pytest
import scrapy
from pkg_resources import parse_version
from pytest_twisted import inlineCallbacks
from w3lib.url import canonicalize_url
from w3lib.http import basic_auth_header

from scrapy_splash import SplashRequest
from .utils import crawl_items, requires_splash
from .resources import (
    HelloWorld,
    Http400Resource,
    ManyCookies,
    HelloWorldProtected,
    HelloWorldDisallowByRobots,
    HelloWorldDisallowAuth,
)


DEFAULT_SCRIPT = """
function main(splash)
  splash:init_cookies(splash.args.cookies)
  splash:go{
    splash.args.url,
    headers=splash.args.headers,
    http_method=splash.args.http_method,
    body=splash.args.body,
  }
  local wait = 0.01
  if splash.args.wait ~= nil then
    wait = splash.args.wait
  end
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


class ResponseSpider(scrapy.Spider):
    """ Make a request to URL, return Scrapy response """
    custom_settings = {
        'HTTPERROR_ALLOW_ALL': True,
        'ROBOTSTXT_OBEY': True,
    }
    url = None

    def start_requests(self):
        yield SplashRequest(self.url)

    def parse(self, response):
        yield {'response': response}


class LuaSpider(ResponseSpider):
    """ Make a request to URL using default Lua script """
    headers = None
    splash_headers = None

    def start_requests(self):
        yield SplashRequest(self.url,
                            endpoint='execute',
                            args={'lua_source': DEFAULT_SCRIPT},
                            headers=self.headers,
                            splash_headers=self.splash_headers)


class ScrapyAuthSpider(LuaSpider):
    """ Spider with incorrect (old, insecure) auth method """
    http_user = 'user'
    http_pass = 'userpass'
    http_auth_domain = None


class NonSplashSpider(ResponseSpider):
    """ Spider which uses HTTP auth and doesn't use Splash """
    http_user = 'user'
    http_pass = 'userpass'
    http_auth_domain = None

    def start_requests(self):
        yield scrapy.Request(self.url)


def assert_single_response(items):
    assert len(items) == 1
    return items[0]['response']


@requires_splash
@inlineCallbacks
def test_basic(settings):
    items, url, crawler = yield crawl_items(ResponseSpider, HelloWorld,
                                            settings)
    resp = assert_single_response(items)
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
    resp = assert_single_response(items)
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
        def start_requests(self):
            yield SplashRequest(self.url, endpoint='execute',
                                args={'lua_source': DEFAULT_SCRIPT, 'wait': 'bar'})

    items, url, crawler = yield crawl_items(BadRequestSpider, HelloWorld,
                                            settings)
    resp = assert_single_response(items)
    assert resp.status == 400
    assert resp.splash_response_status == 400

    items, url, crawler = yield crawl_items(LuaSpider, Http400Resource,
                                            settings)
    resp = assert_single_response(items)
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


@requires_splash
@inlineCallbacks
def test_access_http_auth(settings):
    # website is protected
    items, url, crawler = yield crawl_items(LuaSpider, HelloWorldProtected,
                                            settings)
    response = assert_single_response(items)
    assert response.status == 401
    assert response.splash_response_status == 200

    # header can be used to access it
    AUTH_HEADERS = {'Authorization': basic_auth_header('user', 'userpass')}
    kwargs = {'headers': AUTH_HEADERS}
    items, url, crawler = yield crawl_items(LuaSpider, HelloWorldProtected,
                                            settings, kwargs)
    response = assert_single_response(items)
    assert 'hello' in response.text
    assert response.status == 200
    assert response.splash_response_status == 200


@requires_splash
@inlineCallbacks
def test_protected_splash_no_auth(settings_auth):
    items, url, crawler = yield crawl_items(LuaSpider, HelloWorld,
                                            settings_auth)
    response = assert_single_response(items)
    assert 'Unauthorized' in response.text
    assert 'hello' not in response.text
    assert response.status == 401
    assert response.splash_response_status == 401


@requires_splash
@inlineCallbacks
def test_protected_splash_manual_headers_auth(settings_auth):
    AUTH_HEADERS = {'Authorization': basic_auth_header('user', 'userpass')}
    kwargs = {'splash_headers': AUTH_HEADERS}

    # auth via splash_headers should work
    items, url, crawler = yield crawl_items(LuaSpider, HelloWorld,
                                            settings_auth, kwargs)
    response = assert_single_response(items)
    assert 'hello' in response.text
    assert response.status == 200
    assert response.splash_response_status == 200

    # but only for Splash, not for a remote website
    items, url, crawler = yield crawl_items(LuaSpider, HelloWorldProtected,
                                            settings_auth, kwargs)
    response = assert_single_response(items)
    assert 'hello' not in response.text
    assert response.status == 401
    assert response.splash_response_status == 200


@requires_splash
@inlineCallbacks
def test_protected_splash_settings_auth(settings_auth):
    settings_auth['SPLASH_USER'] = 'user'
    settings_auth['SPLASH_PASS'] = 'userpass'

    # settings works
    items, url, crawler = yield crawl_items(LuaSpider, HelloWorld,
                                            settings_auth)
    response = assert_single_response(items)
    assert 'Unauthorized' not in response.text
    assert 'hello' in response.text
    assert response.status == 200
    assert response.splash_response_status == 200

    # they can be overridden via splash_headers
    bad_auth = {'splash_headers': {'Authorization': 'foo'}}
    items, url, crawler = yield crawl_items(LuaSpider, HelloWorld,
                                            settings_auth, bad_auth)
    response = assert_single_response(items)
    assert response.status == 401
    assert response.splash_response_status == 401

    # auth error on remote website
    items, url, crawler = yield crawl_items(LuaSpider, HelloWorldProtected,
                                            settings_auth)
    response = assert_single_response(items)
    assert response.status == 401
    assert response.splash_response_status == 200

    # auth both for Splash and for the remote website
    REMOTE_AUTH = {'Authorization': basic_auth_header('user', 'userpass')}
    remote_auth_kwargs = {'headers': REMOTE_AUTH}
    items, url, crawler = yield crawl_items(LuaSpider, HelloWorldProtected,
                                            settings_auth, remote_auth_kwargs)
    response = assert_single_response(items)
    assert response.status == 200
    assert response.splash_response_status == 200
    assert 'hello' in response.text

    # enable remote auth, but not splash auth - request should fail
    del settings_auth['SPLASH_USER']
    del settings_auth['SPLASH_PASS']
    items, url, crawler = yield crawl_items(LuaSpider,
                                            HelloWorldProtected,
                                            settings_auth, remote_auth_kwargs)
    response = assert_single_response(items)
    assert response.status == 401
    assert response.splash_response_status == 401


@requires_splash
@inlineCallbacks
def test_protected_splash_httpauth_middleware(settings_auth):
    # httpauth middleware should enable auth for Splash, for backwards
    # compatibility reasons
    items, url, crawler = yield crawl_items(ScrapyAuthSpider, HelloWorld,
                                            settings_auth)
    response = assert_single_response(items)
    assert 'Unauthorized' not in response.text
    assert 'hello' in response.text
    assert response.status == 200
    assert response.splash_response_status == 200

    # but not for a remote website
    items, url, crawler = yield crawl_items(ScrapyAuthSpider,
                                            HelloWorldProtected,
                                            settings_auth)
    response = assert_single_response(items)
    assert 'hello' not in response.text
    assert response.status == 401
    assert response.splash_response_status == 200

    # headers shouldn't be sent to robots.txt file
    items, url, crawler = yield crawl_items(ScrapyAuthSpider,
                                            HelloWorldDisallowAuth,
                                            settings_auth)
    response = assert_single_response(items)
    assert 'hello' in response.text
    assert response.status == 200
    assert response.splash_response_status == 200

    # httpauth shouldn't be disabled for non-Splash requests
    items, url, crawler = yield crawl_items(NonSplashSpider,
                                            HelloWorldProtected,
                                            settings_auth)
    response = assert_single_response(items)
    assert 'hello' in response.text
    assert response.status == 200
    assert not hasattr(response, 'splash_response_status')


@pytest.mark.xfail(
    parse_version(scrapy.__version__) < parse_version("1.1"),
    reason="https://github.com/scrapy/scrapy/issues/1471",
    strict=True,
    run=True,
)
@requires_splash
@inlineCallbacks
def test_robotstxt_can_work(settings_auth):

    def assert_robots_disabled(items):
        response = assert_single_response(items)
        assert response.status == response.splash_response_status == 200
        assert b'hello' in response.body

    def assert_robots_enabled(items, crawler):
        assert len(items) == 0
        assert crawler.stats.get_value('downloader/exception_type_count/scrapy.exceptions.IgnoreRequest') == 1

    def _crawl_items(spider, resource):
        return crawl_items(
            spider,
            resource,
            settings_auth,
            url_path='/',  # https://github.com/scrapy/protego/issues/17
        )

    # when old auth method is used, robots.txt should be disabled
    items, url, crawler = yield _crawl_items(ScrapyAuthSpider,
                                             HelloWorldDisallowByRobots)
    assert_robots_disabled(items)

    # but robots.txt should still work for non-Splash requests
    items, url, crawler = yield _crawl_items(NonSplashSpider,
                                             HelloWorldDisallowByRobots)
    assert_robots_enabled(items, crawler)

    # robots.txt should work when a proper auth method is used
    settings_auth['SPLASH_USER'] = 'user'
    settings_auth['SPLASH_PASS'] = 'userpass'
    items, url, crawler = yield _crawl_items(LuaSpider,
                                             HelloWorldDisallowByRobots)
    assert_robots_enabled(items, crawler)

    # disable robotstxt middleware - robots middleware shouldn't work
    class DontObeyRobotsSpider(LuaSpider):
        custom_settings = {
            'HTTPERROR_ALLOW_ALL': True,
            'ROBOTSTXT_OBEY': False,
        }
    items, url, crawler = yield _crawl_items(DontObeyRobotsSpider,
                                             HelloWorldDisallowByRobots)
    assert_robots_disabled(items)

    # disable robotstxt middleware via request meta
    class MetaDontObeyRobotsSpider(ResponseSpider):
        def start_requests(self):
            yield SplashRequest(self.url,
                                endpoint='execute',
                                meta={'dont_obey_robotstxt': True},
                                args={'lua_source': DEFAULT_SCRIPT})

    items, url, crawler = yield _crawl_items(MetaDontObeyRobotsSpider,
                                             HelloWorldDisallowByRobots)
    assert_robots_disabled(items)
