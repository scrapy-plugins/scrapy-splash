# -*- coding: utf-8 -*-
"""
To handle "splash" Request meta key properly a custom DupeFilter must be set.
See https://github.com/scrapy/scrapy/issues/900 for more info.
"""
from __future__ import absolute_import
from copy import deepcopy

try:
    from scrapy.dupefilters import RFPDupeFilter
except ImportError:
    # scrapy < 1.0
    from scrapy.dupefilter import RFPDupeFilter

from scrapy.utils.url import canonicalize_url
from scrapy.utils.request import request_fingerprint

from .utils import dict_hash


def splash_request_fingerprint(request, include_headers=None):
    """ Request fingerprint which takes 'splash' meta key into account """

    fp = request_fingerprint(request, include_headers=include_headers)
    if 'splash' not in request.meta:
        return fp

    splash_options = deepcopy(request.meta['splash'])
    args = splash_options.setdefault('args', {})

    if 'url' in args:
        args['url'] = canonicalize_url(args['url'], keep_fragments=True)

    return dict_hash(splash_options, fp)


class SplashAwareDupeFilter(RFPDupeFilter):
    """
    DupeFilter that takes 'splash' meta key in account.
    It should be used with SplashMiddleware.
    """
    def request_fingerprint(self, request):
        return splash_request_fingerprint(request)
