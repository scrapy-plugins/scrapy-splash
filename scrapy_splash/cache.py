# -*- coding: utf-8 -*-
"""
To handle "splash" Request meta key correctly when HTTP cache is enabled
Scrapy needs a custom caching backed.

See https://github.com/scrapy/scrapy/issues/900 for more info.
"""
from __future__ import absolute_import
import os
from warnings import warn

from scrapy.extensions.httpcache import FilesystemCacheStorage

from .dupefilter import splash_request_fingerprint


class SplashAwareFSCacheStorage(FilesystemCacheStorage):
    def __init__(self, settings):
        warn(
            (
                "scrapy-splash.SplashAwareFSCacheStorage is deprecated. Set "
                "the REQUEST_FINGERPRINTER_CLASS Scrapy setting to "
                "\"scrapy_splash.SplashRequestFingerprinter\" instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(settings)

    def _get_request_path(self, spider, request):
        key = splash_request_fingerprint(request)
        return os.path.join(self.cachedir, spider.name, key[0:2], key)
