# -*- coding: utf-8 -*-
from __future__ import absolute_import

from .middleware import SplashMiddleware, SlotPolicy
from .dupefilter import SplashAwareDupeFilter, splash_request_fingerprint
from .cache import SplashAwareFSCacheStorage
