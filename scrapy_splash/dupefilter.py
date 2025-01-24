# -*- coding: utf-8 -*-
"""
To handle "splash" Request meta key properly a custom DupeFilter must be set.
See https://github.com/scrapy/scrapy/issues/900 for more info.
"""
from __future__ import absolute_import
from copy import deepcopy
import hashlib
from weakref import WeakKeyDictionary
from warnings import warn

from scrapy.dupefilters import RFPDupeFilter

from scrapy.utils.python import to_bytes
from scrapy.utils.url import canonicalize_url

from .utils import dict_hash


_deprecated_fingerprint_cache = WeakKeyDictionary()


def _serialize_headers(
    headers, request
):
    for header in headers:
        if header in request.headers:
            yield header
            for value in request.headers.getlist(header):
                yield value


# From https://docs.scrapy.org/en/2.11/_modules/scrapy/utils/request.html
# Needs to be added here since it was deletedin Scrapy 2.12
def request_fingerprint(
    request,
    include_headers=None,
    keep_fragments=False,
):
    """
    Return the request fingerprint as an hexadecimal string.

    The request fingerprint is a hash that uniquely identifies the resource the
    request points to. For example, take the following two urls:

    http://www.example.com/query?id=111&cat=222
    http://www.example.com/query?cat=222&id=111

    Even though those are two different URLs both point to the same resource
    and are equivalent (i.e. they should return the same response).

    Another example are cookies used to store session ids. Suppose the
    following page is only accessible to authenticated users:

    http://www.example.com/members/offers.html

    Lots of sites use a cookie to store the session id, which adds a random
    component to the HTTP Request and thus should be ignored when calculating
    the fingerprint.

    For this reason, request headers are ignored by default when calculating
    the fingerprint. If you want to include specific headers use the
    include_headers argument, which is a list of Request headers to include.

    Also, servers usually ignore fragments in urls when handling requests,
    so they are also ignored by default when calculating the fingerprint.
    If you want to include them, set the keep_fragments argument to True
    (for instance when handling requests with a headless browser).
    """
    processed_include_headers = None
    if include_headers:
        processed_include_headers = tuple(
            to_bytes(h.lower()) for h in sorted(include_headers)
        )
    cache = _deprecated_fingerprint_cache.setdefault(request, {})
    cache_key = (processed_include_headers, keep_fragments)
    if cache_key not in cache:
        fp = hashlib.sha1()
        fp.update(to_bytes(request.method))
        fp.update(
            to_bytes(canonicalize_url(request.url, keep_fragments=keep_fragments))
        )
        fp.update(request.body or b"")
        if processed_include_headers:
            for part in _serialize_headers(processed_include_headers, request):
                fp.update(part)
        cache[cache_key] = fp.hexdigest()
    return cache[cache_key]


def splash_request_fingerprint(request, include_headers=None):
    """ Request fingerprint which takes 'splash' meta key into account """
    warn(
        (
            "scrapy_splash.splash_request_fingerprint is deprecated. Set "
            "the REQUEST_FINGERPRINTER_CLASS Scrapy setting to "
            "\"scrapy_splash.SplashRequestFingerprinter\" instead."
        ),
        DeprecationWarning,
        stacklevel=2,
    )

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

    def __init__(self):
        warn(
            (
                "SplashAwareDupeFilter is deprecated. Set "
                "the REQUEST_FINGERPRINTER_CLASS Scrapy setting to "
                "\"scrapy_splash.SplashRequestFingerprinter\" instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )

    def request_fingerprint(self, request):
        return splash_request_fingerprint(request)
