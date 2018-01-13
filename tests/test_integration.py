# -*- coding: utf-8 -*-
import scrapy
from pytest_twisted import inlineCallbacks

from scrapy_splash import SplashRequest
from .utils import crawl_items, requires_splash, HtmlResource

DEFAULT_SCRIPT = """
function main(splash)
  splash:init_cookies(splash.args.cookies)
  assert(splash:go{
    splash.args.url,
    headers=splash.args.headers,
    http_method=splash.args.http_method,
    body=splash.args.body,
    })
  assert(splash:wait(0.5))

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
    extra_headers = {'X-MyHeader': 'my value'}


class ResponseSpider(scrapy.Spider):
    """ Make a request to URL, return Scrapy response """
    url = None

    def start_requests(self):
        yield SplashRequest(self.url)

    def parse(self, response):
        yield {'response': response}


class ReloadSpider(ResponseSpider):
    """ Make two requests to URL, store both responses.
    This spider activates both start_requests and parse methods,
    and checks that dupefilter takes fragment into account. """

    def parse(self, response):
        yield {'response': response}
        yield SplashRequest(self.url + '#foo')


class LuaScriptSpider(ResponseSpider):
    """ Make a request using a Lua script similar to the one from README """

    def start_requests(self):
        yield SplashRequest(self.url + "#foo", endpoint='execute',
                            args={'lua_source': DEFAULT_SCRIPT, 'foo': 'bar'})


@requires_splash
@inlineCallbacks
def test_basic(settings):
    items, url, crawler = yield crawl_items(ResponseSpider, HelloWorld,
                                            settings)
    assert len(items) == 1
    resp = items[0]['response']
    assert resp.url == url
    assert resp.css('body::text').get().strip() == "hello world!"


@requires_splash
@inlineCallbacks
def test_reload(settings):
    items, url, crawler = yield crawl_items(ReloadSpider, HelloWorld, settings)
    assert len(items) == 2
    assert crawler.stats.get_value('dupefilter/filtered') == 1
    resp = items[0]['response']
    assert resp.url == url
    assert resp.css('body::text').get().strip() == "hello world!"

    resp2 = items[1]['response']
    assert resp2.body == resp.body
    assert resp2 is not resp
    assert resp2.url == resp.url + "#foo"


@requires_splash
@inlineCallbacks
def test_basic_lua(settings):
    items, url, crawler = yield crawl_items(LuaScriptSpider, HelloWorld,
                                            settings)
    assert len(items) == 1
    resp = items[0]['response']
    assert resp.url == url + "/#foo"
    assert resp.css('body::text').get().strip() == "hello world!"
    assert resp.data['jsvalue'] == 3
    assert resp.headers['X-MyHeader'] == b'my value'
    assert resp.data['args']['foo'] == 'bar'
