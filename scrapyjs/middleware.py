# -*- coding: utf-8 -*-
from __future__ import absolute_import
import json
import logging
from collections import defaultdict

from six.moves.urllib.parse import urljoin
from six.moves.http_cookiejar import CookieJar

from scrapy.exceptions import NotConfigured
from scrapy.http.headers import Headers

from scrapyjs.responsetypes import responsetypes
from scrapyjs.cookies import jar_to_har, har_to_jar
from scrapyjs.utils import scrapy_headers_to_unicode_dict


logger = logging.getLogger(__name__)


class SlotPolicy(object):
    PER_DOMAIN = 'per_domain'
    SINGLE_SLOT = 'single_slot'
    SCRAPY_DEFAULT = 'scrapy_default'

    _known = {PER_DOMAIN, SINGLE_SLOT, SCRAPY_DEFAULT}


class SplashCookiesMiddleware(object):
    """
    This middleware maintains cookiejars for Splash requests.

    It gets cookies from 'cookies' field in Splash JSON responses
    and sends current cookies in 'cookies' JSON POST argument.

    It should process requests before SplashMiddleware, and process responses
    after SplashMiddleware.
    """
    def __init__(self):
        self.jars = defaultdict(CookieJar)

    def process_request(self, request, spider):
        """
        For Splash requests add 'cookies' key with current
        cookies to request.meta['splash']['args']
        """
        if 'splash' not in request.meta:
            return

        if '_splash_processed' in request.meta:
            return

        splash_options = request.meta['splash']

        splash_args = splash_options.setdefault('args', {})
        if 'cookies' in splash_args:  # cookies already set
            return

        if 'session_id' not in splash_options:
            return

        jar = self.jars[splash_options['session_id']]

        cookies = self._get_request_cookies(request)
        har_to_jar(jar, cookies)

        splash_args['cookies'] = jar_to_har(jar)

    def process_response(self, request, response, spider):
        """
        For Splash JSON responses add all cookies from
        'cookies' in a response to the cookiejar.
        """
        from scrapyjs import SplashJsonResponse
        if not isinstance(response, SplashJsonResponse):
            return response

        if 'cookies' not in response.data:
            return response

        if 'splash' not in request.meta:
            return response

        splash_options = request.meta['splash']
        session_id = splash_options.get('new_session_id',
                                        splash_options.get('session_id'))
        if session_id is None:
            return response

        jar = self.jars[session_id]
        # response.data['cookies'] contains all cookies, but does not contain
        # removed ones, so we first clear all cookies and then load them.
        jar.clear()
        har_to_jar(jar, response.data['cookies'])
        response.cookiejar = jar
        return response

    def _get_request_cookies(self, request):
        if isinstance(request.cookies, dict):
            return [
                {'name': k, 'value': v} for k, v in request.cookies.items()
            ]
        return request.cookies or []


class SplashMiddleware(object):
    """
    Scrapy downloader middleware that passes requests through Splash
    when 'splash' Request.meta key is set.
    """
    default_splash_url = 'http://127.0.0.1:8050'
    default_endpoint = "render.json"
    splash_extra_timeout = 5.0
    default_policy = SlotPolicy.PER_DOMAIN

    def __init__(self, crawler, splash_base_url, slot_policy, log_400):
        self.crawler = crawler
        self.splash_base_url = splash_base_url
        self.slot_policy = slot_policy
        self.log_400 = log_400

    @classmethod
    def from_crawler(cls, crawler):
        splash_base_url = crawler.settings.get('SPLASH_URL',
                                               cls.default_splash_url)
        log_400 = crawler.settings.getbool('SPLASH_LOG_400', True)
        slot_policy = crawler.settings.get('SPLASH_SLOT_POLICY',
                                           cls.default_policy)
        if slot_policy not in SlotPolicy._known:
            raise NotConfigured("Incorrect slot policy: %r" % slot_policy)

        return cls(crawler, splash_base_url, slot_policy, log_400)

    def process_request(self, request, spider):
        if request.method not in {'GET', 'POST'}:
            logger.warn(
                "Currently only GET and POST requests are supported by "
                "SplashMiddleware; %(request)s will be handled without Splash",
                {'request': request},
                extra={'spider': spider}
            )
            return request

        if 'splash' not in request.meta:
            return

        if request.meta.get("_splash_processed"):
            # don't process the same request more than once
            return

        splash_options = request.meta['splash']
        meta = request.meta
        meta['_splash_processed'] = splash_options

        slot_policy = splash_options.get('slot_policy', self.slot_policy)
        self._set_download_slot(request, meta, slot_policy)

        args = splash_options.setdefault('args', {})
        args.setdefault('url', request.url)
        if request.method == 'POST':
            args.setdefault('http_method', request.method)
            # XXX: non-UTF8 bodies are not supported now
            args.setdefault('body', request.body.decode('utf8'))

        if not splash_options.get('dont_send_headers'):
            headers = scrapy_headers_to_unicode_dict(request.headers)
            if headers:
                args.setdefault('headers', headers)

        body = json.dumps(args, ensure_ascii=False, sort_keys=True, indent=4)
        # print(body)

        if 'timeout' in args:
            # User requested a Splash timeout explicitly.
            #
            # We can't catch a case when user requested `download_timeout`
            # explicitly because a default value for `download_timeout`
            # is set by DownloadTimeoutMiddleware.
            #
            # As user requested Splash timeout explicitly, we shouldn't change
            # it. Another reason not to change the requested Splash timeout is
            # because it may cause a validation error on the remote end.
            #
            # But we can change Scrapy `download_timeout`: increase
            # it when it's too small. Decreasing `download_timeout` is not
            # safe.

            timeout_requested = float(args['timeout'])
            timeout_expected = timeout_requested + self.splash_extra_timeout

            # no timeout means infinite timeout
            timeout_current = meta.get('download_timeout', 1e6)

            if timeout_expected > timeout_current:
                meta['download_timeout'] = timeout_expected

        endpoint = splash_options.setdefault('endpoint', self.default_endpoint)
        splash_base_url = splash_options.get('splash_url', self.splash_base_url)
        splash_url = urljoin(splash_base_url, endpoint)

        headers = Headers({'Content-Type': 'application/json'})
        headers.update(splash_options.get('splash_headers', {}))
        req_rep = request.replace(
            url=splash_url,
            method='POST',
            body=body,
            headers=headers,
        )
        self.crawler.stats.inc_value('splash/%s/request_count' % endpoint)
        return req_rep

    def process_response(self, request, response, spider):
        splash_options = request.meta.get("_splash_processed")
        if not splash_options:
            return response

        # update stats
        endpoint = splash_options['endpoint']
        self.crawler.stats.inc_value(
            'splash/%s/response_count/%s' % (endpoint, response.status)
        )

        if splash_options.get('dont_process_response', False):
            return response

        from scrapyjs import SplashResponse, SplashTextResponse, SplashJsonResponse
        if not isinstance(response, (SplashResponse, SplashTextResponse)):
            # create a custom Response subclass based on response Content-Type
            # XXX: usually request is assigned to response only when all
            # downloader middlewares are executed. Here it is set earlier.
            # Does it have any negative consequences?
            respcls = responsetypes.from_args(headers=response.headers)
            response = response.replace(cls=respcls, request=request)

        if self.log_400:
            if response.status == 400 and isinstance(response, SplashJsonResponse):
                logger.warning(
                    "Bad request to Splash: %s" % response.data,
                    {'request': request},
                    extra={'spider': spider}
                )

        return response

    def _set_download_slot(self, request, meta, slot_policy):
        if slot_policy == SlotPolicy.PER_DOMAIN:
            # Use the same download slot to (sort of) respect download
            # delays and concurrency options.
            meta['download_slot'] = self._get_slot_key(request)

        elif slot_policy == SlotPolicy.SINGLE_SLOT:
            # Use a single slot for all Splash requests
            meta['download_slot'] = '__splash__'

        elif slot_policy == SlotPolicy.SCRAPY_DEFAULT:
            # Use standard Scrapy concurrency setup
            pass

    def _get_slot_key(self, request_or_response):
        return self.crawler.engine.downloader._get_slot_key(
            request_or_response, None
        )
