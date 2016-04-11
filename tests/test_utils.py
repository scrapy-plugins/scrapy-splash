# -*- coding: utf-8 -*-
from __future__ import absolute_import

from scrapy.http import Headers
from scrapy_splash.utils import headers_to_scrapy


def test_headers_to_scrapy():
    assert headers_to_scrapy(None) == Headers()
    assert headers_to_scrapy({}) == Headers()
    assert headers_to_scrapy([]) == Headers()

    html_headers = Headers({'Content-Type': 'text/html'})

    assert headers_to_scrapy({'Content-Type': 'text/html'}) == html_headers
    assert headers_to_scrapy([('Content-Type', 'text/html')]) == html_headers
    assert headers_to_scrapy([{'name': 'Content-Type', 'value': 'text/html'}]) == html_headers
