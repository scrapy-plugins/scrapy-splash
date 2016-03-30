# -*- coding: utf-8 -*-
from __future__ import absolute_import

from scrapy.http import Headers
from scrapyjs.utils import headers_to_scrapy, cookies_to_header_values


def test_headers_to_scrapy():
    assert headers_to_scrapy(None) == Headers()
    assert headers_to_scrapy({}) == Headers()
    assert headers_to_scrapy([]) == Headers()

    html_headers = Headers({'Content-Type': 'text/html'})

    assert headers_to_scrapy({'Content-Type': 'text/html'}) == html_headers
    assert headers_to_scrapy([('Content-Type', 'text/html')]) == html_headers
    assert headers_to_scrapy([{'name': 'Content-Type', 'value': 'text/html'}]) == html_headers


def test_cookies_to_header_values():
    assert cookies_to_header_values(None) == []
    assert cookies_to_header_values([]) == []
    assert cookies_to_header_values(["foo=bar", "x=y"]) == ["foo=bar", "x=y"]
    assert cookies_to_header_values([{
        "name": "TestCookie",
        "value": "Cookie Value",
        "path": "/",
        "domain": "www.janodvarko.cz",
        "expires": "2009-07-24T19:20:30.123+02:00",
        "httpOnly": False,
    }]) == ['TestCookie="Cookie Value"; Domain=www.janodvarko.cz; expires=2009-07-24T19:20:30.123+02:00; Path=/']
