# -*- coding: utf-8 -*-
from __future__ import absolute_import
import copy
import scrapy

# XXX: we can't implement SplashRequest without middleware support
# because there is no way to set Splash URL based on settings
# from inside SplashRequest.


class SplashRequest(scrapy.Request):
    default_splash_meta = {
        'args': {'wait': 0.5},
        'endpoint': 'render.html',
    }

    def __init__(self, url=None, *args, **kwargs):
        if url is None:
            url = 'about:blank'
        self._original_url = url
        meta = kwargs.pop('meta', {})
        if 'splash' not in meta:
            meta['splash'] = copy.deepcopy(self.default_splash_meta)
        super(SplashRequest, self).__init__(url, *args, meta=meta, **kwargs)

    def replace(self, *args, **kwargs):
        obj = super(SplashRequest, self).replace(*args, **kwargs)
        obj._original_url = self._original_url
        return obj

    def __str__(self):
        return "<%s %s %s>" % (self.method, self.url, self._original_url)

    __repr__ = __str__
