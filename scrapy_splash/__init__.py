# -*- coding: utf-8 -*-
from __future__ import absolute_import

from .middleware import (
    SplashMiddleware,
    SplashCookiesMiddleware,
    SplashDeduplicateArgsMiddleware,
    SlotPolicy,
)
from .dupefilter import SplashAwareDupeFilter, splash_request_fingerprint
from .cache import SplashAwareFSCacheStorage
from .response import SplashResponse, SplashTextResponse, SplashJsonResponse
from .request import SplashRequest, SplashFormRequest
