# -*- coding: utf-8 -*-
from __future__ import absolute_import

import copy
import json
import logging
import warnings
from collections import defaultdict

from six.moves.urllib.parse import urljoin
from six.moves.http_cookiejar import CookieJar

import scrapy
from scrapy.exceptions import NotConfigured
from scrapy.http.headers import Headers
from scrapy import signals

from scrapy_splash.responsetypes import responsetypes
from scrapy_splash.cookies import jar_to_har, har_to_jar
from scrapy_splash.utils import (
    scrapy_headers_to_unicode_dict,
    json_based_hash,
    parse_x_splash_saved_arguments_header,
)


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
    def __init__(self, debug=False):
        self.jars = defaultdict(CookieJar)
        self.debug = debug

    @classmethod
    def from_crawler(cls, crawler):
        return cls(debug=crawler.settings.getbool('SPLASH_COOKIES_DEBUG'))

    def process_request(self, request, spider):
        """
        For Splash requests add 'cookies' key with current
        cookies to request.meta['splash']['args']
        """
        if 'splash' not in request.meta:
            return

        if request.meta.get('_splash_processed'):
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
        self._debug_cookie(request, spider)

    def process_response(self, request, response, spider):
        """
        For Splash JSON responses add all cookies from
        'cookies' in a response to the cookiejar.
        """
        from scrapy_splash import SplashJsonResponse
        if not isinstance(response, SplashJsonResponse):
            return response

        if 'cookies' not in response.data:
            return response

        if 'splash' not in request.meta:
            return response

        if not request.meta.get('_splash_processed'):
            warnings.warn("SplashCookiesMiddleware requires SplashMiddleware")
            return response

        splash_options = request.meta['splash']
        session_id = splash_options.get('new_session_id',
                                        splash_options.get('session_id'))
        if session_id is None:
            return response

        jar = self.jars[session_id]
        request_cookies = splash_options['args'].get('cookies', [])
        har_to_jar(jar, response.data['cookies'], request_cookies)
        self._debug_set_cookie(response, spider)
        response.cookiejar = jar
        return response

    def _get_request_cookies(self, request):
        if isinstance(request.cookies, dict):
            return [
                {'name': k, 'value': v} for k, v in request.cookies.items()
            ]
        return request.cookies or []

    def _debug_cookie(self, request, spider):
        if self.debug:
            cl = request.meta['splash']['args']['cookies']
            if cl:
                cookies = '\n'.join(
                    'Cookie: {}'.format(self._har_repr(c)) for c in cl)
                msg = 'Sending cookies to: {}\n{}'.format(request, cookies)
                logger.debug(msg, extra={'spider': spider})

    def _debug_set_cookie(self, response, spider):
        if self.debug:
            cl = response.data['cookies']
            if cl:
                cookies = '\n'.join(
                    'Set-Cookie: {}'.format(self._har_repr(c)) for c in cl)
                msg = 'Received cookies from: {}\n{}'.format(response, cookies)
                logger.debug(msg, extra={'spider': spider})

    @staticmethod
    def _har_repr(har_cookie):
        return '{}={}'.format(har_cookie['name'], har_cookie['value'])


class SplashDeduplicateArgsMiddleware(object):
    """
    Spider middleware which allows not to store duplicate Splash argument
    values in request queue. It works together with SplashMiddleware downloader
    middleware.
    """
    local_values_key = '_splash_local_values'

    def process_spider_output(self, response, result, spider):
        for el in result:
            if isinstance(el, scrapy.Request):
                yield self._process_request(el, spider)
            else:
                yield el

    def process_start_requests(self, start_requests, spider):
        if not hasattr(spider, 'state'):
            spider.state = {}
        spider.state.setdefault(self.local_values_key, {})  # fingerprint => value dict

        for req in start_requests:
            yield self._process_request(req, spider)

    def _process_request(self, request, spider):
        """
        Replace requested meta['splash']['args'] values with their fingerprints.
        This allows to store values only once in request queue, which helps
        with disk queue size.

        Downloader middleware should restore the values from fingerprints.
        """
        if 'splash' not in request.meta:
            return request

        if '_replaced_args' in request.meta['splash']:
            # don't process re-scheduled requests
            # XXX: does it work as expected?
            warnings.warn("Unexpected request.meta['splash']['_replaced_args']")
            return request

        request.meta['splash']['_replaced_args'] = []
        cache_args = request.meta['splash'].get('cache_args', [])
        args = request.meta['splash'].setdefault('args', {})

        for name in cache_args:
            if name not in args:
                continue
            value = args[name]
            fp = 'LOCAL+' + json_based_hash(value)
            spider.state[self.local_values_key][fp] = value
            args[name] = fp
            request.meta['splash']['_replaced_args'].append(name)

        return request


class SplashMiddleware(object):
    """
    Scrapy downloader and spider middleware that passes requests
    through Splash when 'splash' Request.meta key is set.

    This middleware also works together with SplashDeduplicateArgsMiddleware
    spider middleware to allow not to store duplicate Splash argument values
    in request queue and not to send them multiple times to Splash
    (the latter requires Splash 2.1+).
    """
    default_splash_url = 'http://127.0.0.1:8050'
    default_endpoint = "render.json"
    splash_extra_timeout = 5.0
    default_policy = SlotPolicy.PER_DOMAIN
    rescheduling_priority_adjust = +100
    retry_498_priority_adjust = +50
    remote_keys_key = '_splash_remote_keys'

    def __init__(self, crawler, splash_base_url, slot_policy, log_400):
        self.crawler = crawler
        self.splash_base_url = splash_base_url
        self.slot_policy = slot_policy
        self.log_400 = log_400
        self.crawler.signals.connect(self.spider_opened, signals.spider_opened)

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

    def spider_opened(self, spider):
        if not hasattr(spider, 'state'):
            spider.state = {}

        # local fingerprint => key returned by splash
        spider.state.setdefault(self.remote_keys_key, {})

    @property
    def _argument_values(self):
        key = SplashDeduplicateArgsMiddleware.local_values_key
        return self.crawler.spider.state[key]

    @property
    def _remote_keys(self):
        return self.crawler.spider.state[self.remote_keys_key]

    def process_request(self, request, spider):
        if 'splash' not in request.meta:
            return

        if request.method not in {'GET', 'POST'}:
            logger.warn(
                "Currently only GET and POST requests are supported by "
                "SplashMiddleware; %(request)s will be handled without Splash",
                {'request': request},
                extra={'spider': spider}
            )
            return request

        if request.meta.get("_splash_processed"):
            # don't process the same request more than once
            return

        splash_options = request.meta['splash']
        request.meta['_splash_processed'] = True

        slot_policy = splash_options.get('slot_policy', self.slot_policy)
        self._set_download_slot(request, request.meta, slot_policy)

        args = splash_options.setdefault('args', {})

        if '_replaced_args' in splash_options:
            # restore arguments before sending request to the downloader
            load_args = {}
            save_args = []
            local_arg_fingerprints = {}
            for name in splash_options['_replaced_args']:
                fp = args[name]
                # Use remote Splash argument cache: if Splash key
                # for a value is known then don't send the value to Splash;
                # if it is unknown then try to save the value on server using
                # ``save_args``.
                if fp in self._remote_keys:
                    load_args[name] = self._remote_keys[fp]
                    del args[name]
                else:
                    save_args.append(name)
                    args[name] = self._argument_values[fp]

                local_arg_fingerprints[name] = fp

            if load_args:
                args['load_args'] = load_args
            if save_args:
                args['save_args'] = save_args
            splash_options['_local_arg_fingerprints'] = local_arg_fingerprints

            del splash_options['_replaced_args']  # ??

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
            timeout_current = request.meta.get('download_timeout', 1e6)

            if timeout_expected > timeout_current:
                request.meta['download_timeout'] = timeout_expected

        endpoint = splash_options.setdefault('endpoint', self.default_endpoint)
        splash_base_url = splash_options.get('splash_url', self.splash_base_url)
        splash_url = urljoin(splash_base_url, endpoint)

        headers = Headers({'Content-Type': 'application/json'})
        headers.update(splash_options.get('splash_headers', {}))
        new_request = request.replace(
            url=splash_url,
            method='POST',
            body=body,
            headers=headers,
            priority=request.priority + self.rescheduling_priority_adjust
        )
        self.crawler.stats.inc_value('splash/%s/request_count' % endpoint)
        return new_request

    def process_response(self, request, response, spider):
        if not request.meta.get("_splash_processed"):
            return response

        splash_options = request.meta['splash']
        if not splash_options:
            return response

        # update stats
        endpoint = splash_options['endpoint']
        self.crawler.stats.inc_value(
            'splash/%s/response_count/%s' % (endpoint, response.status)
        )

        # handle save_args/load_args
        self._process_x_splash_saved_arguments(request, response)
        if response.status == 498:
            logger.debug("Got HTTP 498 response for {}; "
                         "sending arguments again.".format(request),
                         extra={'spider': spider})
            return self._498_retry_request(request, response)

        if splash_options.get('dont_process_response', False):
            return response

        response = self._change_response_class(request, response)

        if self.log_400 and response.status == 400:
            self._log_400(request, response, spider)

        return response

    def _change_response_class(self, request, response):
        from scrapy_splash import SplashResponse, SplashTextResponse
        if not isinstance(response, (SplashResponse, SplashTextResponse)):
            # create a custom Response subclass based on response Content-Type
            # XXX: usually request is assigned to response only when all
            # downloader middlewares are executed. Here it is set earlier.
            # Does it have any negative consequences?
            respcls = responsetypes.from_args(headers=response.headers)
            response = response.replace(cls=respcls, request=request)
        return response

    def _log_400(self, request, response, spider):
        from scrapy_splash import SplashJsonResponse
        if isinstance(response, SplashJsonResponse):
            logger.warning(
                "Bad request to Splash: %s" % response.data,
                {'request': request},
                extra={'spider': spider}
            )

    def _process_x_splash_saved_arguments(self, request, response):
        """ Keep track of arguments saved by Splash. """
        saved_args = response.headers.get(b'X-Splash-Saved-Arguments')
        if not saved_args:
            return
        saved_args = parse_x_splash_saved_arguments_header(saved_args)
        arg_fingerprints = request.meta['splash']['_local_arg_fingerprints']
        for name, key in saved_args.items():
            fp = arg_fingerprints[name]
            self._remote_keys[fp] = key

    def _498_retry_request(self, request, response):
        """
        Return a retry request for HTTP 498 responses. HTTP 498 means
        load_args are not present on server; client should retry the request
        with full argument values instead of their hashes.
        """
        meta = copy.deepcopy(request.meta)
        local_arg_fingerprints = meta['splash']['_local_arg_fingerprints']
        args = meta['splash']['args']
        args.pop('load_args', None)
        args['save_args'] = list(local_arg_fingerprints.keys())

        for name, fp in local_arg_fingerprints.items():
            args[name] = self._argument_values[fp]
            # print('remote_keys before:', self._remote_keys)
            self._remote_keys.pop(fp, None)
            # print('remote_keys after:', self._remote_keys)

        body = json.dumps(args, ensure_ascii=False, sort_keys=True, indent=4)
        # print(body)
        request = request.replace(
            meta=meta,
            body=body,
            priority=request.priority+self.retry_498_priority_adjust
        )
        return request

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
