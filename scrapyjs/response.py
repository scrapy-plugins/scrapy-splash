# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import base64

from scrapy.http import Response, TextResponse
from scrapy import Selector


class _RealUrlMixin(object):
    """ This mixin fixes response.url and adds response.real_url """
    def __init__(self, url, *args, **kwargs):
        real_url = kwargs.pop('real_url', None)
        if real_url is not None:
            self.real_url = real_url
        else:
            self.real_url = None
            request = kwargs['request']
            splash_options = request.meta.get("_splash_processed")
            if splash_options:
                splash_args = splash_options.get('args', {})
                _url = splash_args.get('url', None)
                if _url is not None:
                    self.real_url = url
                    url = _url
        super(_RealUrlMixin, self).__init__(url, *args, **kwargs)

    def replace(self, *args, **kwargs):
        """Create a new Response with the same attributes except for those
        given new values.
        """
        for x in ['url', 'status', 'headers', 'body', 'request', 'flags',
                  'real_url']:
            kwargs.setdefault(x, getattr(self, x))
        cls = kwargs.pop('cls', self.__class__)
        return cls(*args, **kwargs)


class SplashResponse(_RealUrlMixin, Response):
    """
    This Response subclass sets response.url to the URL of a remote website
    instead of an URL of Splash server. "Real" response URL is still available
    as ``response.real_url``.
    """


class SplashTextResponse(_RealUrlMixin, TextResponse):
    """
    This TextResponse subclass sets response.url to the URL of a remote website
    instead of an URL of Splash server. "Real" response URL is still available
    as ``response.real_url``.
    """
    def replace(self, *args, **kwargs):
        kwargs.setdefault('encoding', self.encoding)
        return _RealUrlMixin.replace(self, *args, **kwargs)


class SplashJsonResponse(SplashResponse):
    """
    Splash Response with JSON data. It provides a convenient way to access
    parsed JSON response using ``response.data`` attribute.

    TODO: If Scrapy-Splash magic integration is enabled in request,
    several other response attributes (headers, body, url, status code)
    are set automatically:

    * response.headers are filled from 'headers' key;
    * response.url is set to the value of 'url' key;
    * response.body is set to the value of 'html' key,
      or to base64-decoded value of 'body' key;
    * response.status is set from the value of 'status' key.
    """
    def __init__(self, *args, **kwargs):
        self._cached_ubody = None
        self._cached_data = None
        self._cached_selector = None
        kwargs.pop('encoding', None)  # encoding is always utf-8
        super(SplashJsonResponse, self).__init__(*args, **kwargs)

    @property
    def data(self):
        if self._cached_data is None:
            self._cached_data = json.loads(self._decoded_body)
        return self._cached_data

    @property
    def text(self):
        return self._decoded_body

    def body_as_unicode(self):
        return self._decoded_body

    @property
    def _decoded_body(self):
        if self._cached_ubody is None:
            self._cached_ubody = self.body.decode(self.encoding)
        return self._cached_ubody

    @property
    def encoding(self):
        return 'utf8'

    @property
    def selector(self):
        if self._cached_selector is None:
            self._cached_selector = Selector(text=self.text, type='html')
        return self._cached_selector

    def xpath(self, query):
        return self.selector.xpath(query)

    def css(self, query):
        return self.selector.css(query)
