# -*- coding: utf-8 -*-
from __future__ import absolute_import
import scrapy

from scrapyjs import SlotPolicy

# XXX: we can't implement SplashRequest without middleware support
# because there is no way to set Splash URL based on settings
# from inside SplashRequest.


class SplashRequest(scrapy.Request):
    """
    scrapy.Request subclass which instructs Scrapy to render
    the page using Splash.

    It requires SplashMiddleware to work.
    """
    def __init__(self,
                 url=None,
                 callback=None,
                 method='GET',
                 endpoint='render.html',
                 args=None,
                 splash_url=None,
                 slot_policy=SlotPolicy.PER_DOMAIN,
                 splash_headers=None,
                 dont_process_response=False,
                 magic_response=True,
                 **kwargs):

        if url is None:
            url = 'about:blank'

        meta = kwargs.pop('meta', {})
        splash_meta = meta.setdefault('splash', {})
        splash_meta.setdefault('endpoint', endpoint)
        splash_meta.setdefault('slot_policy', slot_policy)
        if splash_url is not None:
            splash_meta['splash_url'] = splash_url
        if splash_headers is not None:
            splash_meta['splash_headers'] = splash_headers
        if dont_process_response:
            splash_meta['dont_process_response'] = True
        else:
            splash_meta.setdefault('magic_response', magic_response)

        _args = {'url': url}  # put URL to args in order to preserve #fragment
        _args.update(args or {})
        _args.update(splash_meta.get('args', {}))
        splash_meta['args'] = _args

        super(SplashRequest, self).__init__(url, callback, method, meta=meta,
                                            **kwargs)

    @property
    def _original_url(self):
        return self.meta.get('splash', {}).get('args', {}).get('url')

    @property
    def _original_method(self):
        return self.meta.get('splash', {}).get('args', {}).get('http_method', 'GET')

    def __str__(self):
        return "<%s %s via %s>" % (self._original_method, self._original_url, self.url)

    __repr__ = __str__
