# -*- coding: utf-8 -*-
from __future__ import absolute_import
import scrapy
from scrapy.http import FormRequest

from scrapy_splash import SlotPolicy
from scrapy_splash.utils import to_native_str

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
                 dont_send_headers=False,
                 magic_response=True,
                 session_id='default',
                 http_status_from_error_code=True,
                 cache_args=None,
                 meta=None,
                 **kwargs):

        if url is None:
            url = 'about:blank'
        url = to_native_str(url)

        meta = meta or {}
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
        if dont_send_headers:
            splash_meta['dont_send_headers'] = True
        if http_status_from_error_code:
            splash_meta['http_status_from_error_code'] = True
        if cache_args is not None:
            splash_meta['cache_args'] = cache_args

        if session_id is not None:
            if splash_meta['endpoint'].strip('/') == 'execute':
                splash_meta.setdefault('session_id', session_id)

        _args = {'url': url}  # put URL to args in order to preserve #fragment
        _args.update(args or {})
        _args.update(splash_meta.get('args', {}))
        splash_meta['args'] = _args

        # This is not strictly required, but it strengthens Splash
        # requests against AjaxCrawlMiddleware
        meta['ajax_crawlable'] = True

        super(SplashRequest, self).__init__(url, callback, method, meta=meta,
                                            **kwargs)

    @property
    def _processed(self):
        return self.meta.get('_splash_processed')

    @property
    def _splash_args(self):
        return self.meta.get('splash', {}).get('args', {})

    @property
    def _original_url(self):
        return self._splash_args.get('url')

    @property
    def _original_method(self):
        return self._splash_args.get('http_method', 'GET')

    def __str__(self):
        if not self._processed:
            return super(SplashRequest, self).__str__()
        return "<%s %s via %s>" % (self._original_method, self._original_url, self.url)

    __repr__ = __str__


class SplashFormRequest(SplashRequest, FormRequest):
    """
    Use SplashFormRequest if you want to make a FormRequest via splash.
    Accepts the same arguments as SplashRequest, and also formdata,
    like FormRequest. First, FormRequest is initialized, and then it's
    url, method and body are passed to SplashRequest.
    Note that FormRequest calls escape_ajax on url (via Request._set_url).
    """
    def __init__(self, url=None, callback=None, method=None, formdata=None,
                 body=None, **kwargs):
        # First init FormRequest to get url, body and method
        if formdata:
            FormRequest.__init__(
                self, url=url, method=method, formdata=formdata)
            url, method, body = self.url, self.method, self.body
        # Then pass all other kwargs to SplashRequest
        SplashRequest.__init__(
            self, url=url, callback=callback, method=method, body=body,
            **kwargs)
