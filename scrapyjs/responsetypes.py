# -*- coding: utf-8 -*-
from __future__ import absolute_import

from scrapy.http import Response
from scrapy.responsetypes import ResponseTypes

import scrapyjs


class SplashResponseTypes(ResponseTypes):
    CLASSES = {
        'text/html': 'scrapyjs.response.SplashTextResponse',
        'application/atom+xml': 'scrapyjs.response.SplashTextResponse',
        'application/rdf+xml': 'scrapyjs.response.SplashTextResponse',
        'application/rss+xml': 'scrapyjs.response.SplashTextResponse',
        'application/xhtml+xml': 'scrapyjs.response.SplashTextResponse',
        'application/vnd.wap.xhtml+xml': 'scrapyjs.response.SplashTextResponse',
        'application/xml': 'scrapyjs.response.SplashTextResponse',
        'application/json': 'scrapyjs.response.SplashJsonResponse',
        'application/x-json': 'scrapyjs.response.SplashJsonResponse',
        'application/javascript': 'scrapyjs.response.SplashTextResponse',
        'application/x-javascript': 'scrapyjs.response.SplashTextResponse',
        'text/xml': 'scrapyjs.response.SplashTextResponse',
        'text/*': 'scrapyjs.response.SplashTextResponse',
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
            cls = scrapyjs.SplashResponse
        return cls


responsetypes = SplashResponseTypes()
