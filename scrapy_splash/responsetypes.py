# -*- coding: utf-8 -*-
from __future__ import absolute_import

from scrapy.http import Response
from scrapy.responsetypes import ResponseTypes

import scrapy_splash


class SplashResponseTypes(ResponseTypes):
    CLASSES = {
        'text/html': 'scrapy_splash.response.SplashTextResponse',
        'application/atom+xml': 'scrapy_splash.response.SplashTextResponse',
        'application/rdf+xml': 'scrapy_splash.response.SplashTextResponse',
        'application/rss+xml': 'scrapy_splash.response.SplashTextResponse',
        'application/xhtml+xml': 'scrapy_splash.response.SplashTextResponse',
        'application/vnd.wap.xhtml+xml': 'scrapy_splash.response.SplashTextResponse',
        'application/xml': 'scrapy_splash.response.SplashTextResponse',
        'application/json': 'scrapy_splash.response.SplashJsonResponse',
        'application/x-json': 'scrapy_splash.response.SplashJsonResponse',
        'application/javascript': 'scrapy_splash.response.SplashTextResponse',
        'application/x-javascript': 'scrapy_splash.response.SplashTextResponse',
        'text/xml': 'scrapy_splash.response.SplashTextResponse',
        'text/*': 'scrapy_splash.response.SplashTextResponse',
    }

    def from_args(self, headers=None, url=None, filename=None, body=None):
        """Guess the most appropriate Response class based on
        the given arguments."""
        cls = super(SplashResponseTypes, self).from_args(
            headers=headers,
            url=url,
            filename=filename,
            body=body
        )
        if cls is Response:
            cls = scrapy_splash.SplashResponse
        return cls


responsetypes = SplashResponseTypes()
