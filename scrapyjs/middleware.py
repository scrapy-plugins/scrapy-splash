# -*- coding: utf-8 -*-
from __future__ import absolute_import
import json
import logging
from six.moves.urllib.parse import urljoin

from scrapy.exceptions import NotConfigured
from scrapy.http.headers import Headers


logger = logging.getLogger(__name__)


class SlotPolicy(object):
    PER_DOMAIN = 'per_domain'
    SINGLE_SLOT = 'single_slot'
    SCRAPY_DEFAULT = 'scrapy_default'

    _known = {PER_DOMAIN, SINGLE_SLOT, SCRAPY_DEFAULT}


class SplashMiddleware(object):
    """
    Scrapy downloader middleware that passes requests through Splash
    when 'splash' Request.meta key is set.
    """
    default_splash_url = 'http://127.0.0.1:8050'
    default_endpoint = "render.json"
    splash_extra_timeout = 5.0
    default_policy = SlotPolicy.PER_DOMAIN

    def __init__(self, crawler, splash_base_url, slot_policy):
        self.crawler = crawler
        self.splash_base_url = splash_base_url
        self.slot_policy = slot_policy

    @classmethod
    def from_crawler(cls, crawler):
        splash_base_url = crawler.settings.get('SPLASH_URL',
                                               cls.default_splash_url)
        slot_policy = crawler.settings.get('SPLASH_SLOT_POLICY',
                                           cls.default_policy)

        if slot_policy not in SlotPolicy._known:
            raise NotConfigured("Incorrect slot policy: %r" % slot_policy)

        return cls(crawler, splash_base_url, slot_policy)

    def process_request(self, request, spider):
        splash_options = request.meta.get('splash')
        if not splash_options:
            return

        if request.meta.get("_splash_processed"):
            # don't process the same request more than once
            return

        if request.method != 'GET':
            logger.warn(
                "Currently only GET requests are supported by SplashMiddleware;"
                " %(request)s will be handled without Splash",
                {'request': request},
                extra={'spider': spider}
            )
            return request

        meta = request.meta
        meta['_splash_processed'] = splash_options

        slot_policy = splash_options.get('slot_policy', self.slot_policy)
        self._set_download_slot(request, meta, slot_policy)

        args = splash_options.setdefault('args', {})
        args.setdefault('url', request.url)
        body = json.dumps(args, ensure_ascii=False)

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

            # no timeout means infinite timeout
            timeout_current = meta.get('download_timeout', 1e6)
            timeout_expected = float(args['timeout']) + self.splash_extra_timeout

            if timeout_expected > timeout_current:
                meta['download_timeout'] = timeout_expected

        endpoint = splash_options.setdefault('endpoint', self.default_endpoint)
        splash_base_url = splash_options.get('splash_url', self.splash_base_url)
        splash_url = urljoin(splash_base_url, endpoint)

        req_rep = request.replace(
            url=splash_url,
            method='POST',
            body=body,

            # FIXME: original HTTP headers (including cookies)
            # are not respected.
            headers=Headers({'Content-Type': 'application/json'}),
        )

        self.crawler.stats.inc_value('splash/%s/request_count' % endpoint)
        return req_rep

    def process_response(self, request, response, spider):
        splash_options = request.meta.get("_splash_processed")
        if splash_options:
            endpoint = splash_options['endpoint']
            self.crawler.stats.inc_value(
                'splash/%s/response_count/%s' % (endpoint, response.status)
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
