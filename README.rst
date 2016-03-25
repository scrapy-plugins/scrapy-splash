=========================================================
ScrapyJS - Scrapy & JavaScript integration through Splash
=========================================================

.. image:: https://travis-ci.org/scrapy-plugins/scrapy-splash.svg?branch=master
   :target: http://travis-ci.org/scrapy-plugins/scrapy-splash

This library provides Scrapy_ and JavaScript integration using Splash_.
The license is BSD 3-clause.

.. _Scrapy: https://github.com/scrapy/scrapy
.. _Splash: https://github.com/scrapinghub/splash

Installation
============

Install ScrapyJS using pip::

    $ pip install scrapyjs

ScrapyJS uses Splash_ HTTP API, so you also need a Splash instance.
Usually to install & run Splash, something like this is enough::

    $ docker run -p 8050:8050 scrapinghub/splash

Check Splash `install docs`_ for more info.

.. _install docs: http://splash.readthedocs.org/en/latest/install.html


Configuration
=============

1. Add the Splash server address to ``settings.py`` of your Scrapy project like this::

      SPLASH_URL = 'http://192.168.59.103:8050'

2. Enable the Splash middleware by adding it to ``DOWNLOADER_MIDDLEWARES`` in your ``settings.py`` file::

      DOWNLOADER_MIDDLEWARES = {
          'scrapyjs.SplashMiddleware': 725,
      }

.. note::

   Order `725` is just before `HttpProxyMiddleware` (750) in default
   scrapy settings.

3. Set a custom ``DUPEFILTER_CLASS``::

      DUPEFILTER_CLASS = 'scrapyjs.SplashAwareDupeFilter'

4. If you use Scrapy HTTP cache then a custom cache storage backend is required.
   ScrapyJS provides a subclass of ``scrapy.contrib.httpcache.FilesystemCacheStorage``::

      HTTPCACHE_STORAGE = 'scrapyjs.SplashAwareFSCacheStorage'

   If you use other cache storage then it is necesary to subclass it and
   replace all ``scrapy.util.request.request_fingerprint`` calls with
   ``scrapyjs.splash_request_fingerprint``.

.. note::

    Steps (3) and (4) are necessary because Scrapy doesn't provide a way
    to override request fingerprints calculation algorithm globally; this
    could change in future.


Usage
=====

To render the requests with Splash, use the ``'splash'`` Request `meta` key::

    yield Request(url, self.parse_result, meta={
        'splash': {
            'args': {
                # set rendering arguments here
                'html': 1,
                'png': 1,

                # 'url' is prefilled from request url
            },

            # optional parameters
            'endpoint': 'render.json',  # optional; default is render.json
            'splash_url': '<url>',      # overrides SPLASH_URL
            'slot_policy': scrapyjs.SlotPolicy.PER_DOMAIN,
        }
    })

* ``meta['splash']['args']`` contains arguments sent to Splash.
  ScrapyJS adds request.url to these arguments automatically.

  Note that by default Scrapy escapes URL fragments using AJAX escaping scheme.
  If you want to pass a URL with a fragment to Splash then set ``url``
  in ``args`` dict manually.

* ``meta['splash']['endpoint']`` is the Splash endpoint to use. By default
  `render.json <http://splash.readthedocs.org/en/latest/api.html#render-json>`_
  is used.

  See Splash `HTTP API docs`_ for a full list of available endpoints
  and parameters.

.. _HTTP API docs: http://splash.readthedocs.org/en/latest/api.html

* ``meta['splash']['splash_url']`` overrides the Splash URL set
  in ``settings.py``.

* ``meta['splash']['slot_policy']`` customize how
  concurrency & politeness are maintained for Splash requests.

  Currently there are 3 policies available:

  1. ``scrapyjs.SlotPolicy.PER_DOMAIN`` (default) - send Splash requests to
     downloader slots based on URL being rendered. It is useful if you want
     to maintain per-domain politeness & concurrency settings.

  2. ``scrapyjs.SlotPolicy.SINGLE_SLOT`` - send all Splash requests to
     a single downloader slot. It is useful if you want to throttle requests
     to Splash.

  3. ``scrapyjs.SlotPolicy.SCRAPY_DEFAULT`` - don't do anything with slots.
     It is similar to ``SINGLE_SLOT`` policy, but can be different if you access
     other services on the same address as Splash.


Examples
========

Get HTML contents::

    import scrapy

    class MySpider(scrapy.Spider):
        start_urls = ["http://example.com", "http://example.com/foo"]

        def start_requests(self):
            for url in self.start_urls:
                yield scrapy.Request(url, self.parse, meta={
                    'splash': {
                        'endpoint': 'render.html',
                        'args': {'wait': 0.5}
                    }
                })

        def parse(self, response):
            # response.body is a result of render.html call; it
            # contains HTML processed by a browser.
            # ...

Get HTML contents and a screenshot::

    import json
    import base64
    import scrapy

    class MySpider(scrapy.Spider):

        # ...
            yield scrapy.Request(url, self.parse_result, meta={
                'splash': {
                    'args': {
                        'html': 1,
                        'png': 1,
                        'width': 600,
                        'render_all': 1,
                    }
                }
            })

        # ...
        def parse_result(self, response):
            data = json.loads(response.body_as_unicode())
            body = data['html']
            png_bytes = base64.b64decode(data['png'])
            # ...

Run a simple `Splash Lua Script`_::

    import json
    import base64

    class MySpider(scrapy.Spider):

        # ...
            script = """
            function main(splash)
                assert(splash:go(splash.args.url))
                return splash:evaljs("document.title")
            end
            """
            yield scrapy.Request(url, self.parse_result, meta={
                'splash': {
                    'args': {'lua_source': script},
                    'endpoint': 'execute',
                }
            })

        # ...
        def parse_response(self, response):
            doc_title = response.body_as_unicode()
            # ...


.. _Splash Lua Script: http://splash.readthedocs.org/en/latest/scripting-tutorial.html


HTTP Basic Auth
===============

If you need HTTP Basic Authentication to access Splash, use
Scrapy's HttpAuthMiddleware_.

.. _HttpAuthMiddleware: http://doc.scrapy.org/en/latest/topics/downloader-middleware.html#module-scrapy.downloadermiddlewares.httpauth

Why not use the Splash HTTP API directly?
=========================================

The obvious alternative to ScrapyJS would be to send requests directly
to the Splash `HTTP API`_. Take a look at the example below and make
sure to read the observations after it::

    import json

    import scrapy
    from scrapy.http.headers import Headers

    RENDER_HTML_URL = "http://127.0.0.1:8050/render.html"

    class MySpider(scrapy.Spider):
        start_urls = ["http://example.com", "http://example.com/foo"]

        def start_requests(self):
            for url in self.start_urls:
                body = json.dumps({"url": url, "wait": 0.5})
                headers = Headers({'Content-Type': 'application/json'})
                yield scrapy.Request(RENDER_HTML_URL, self.parse, method="POST",
                                     body=body, headers=headers)

        def parse(self, response):
            # response.body is a result of render.html call; it
            # contains HTML processed by a browser.
            # ...


It works and is easy enough, but there are some issues that you should be
aware of:

1. There is a bit of boilerplate.

2. As seen by Scrapy, we're sending requests to ``RENDER_HTML_URL`` instead
   of the target URLs. It affects concurrency and politeness settings:
   ``CONCURRENT_REQUESTS_PER_DOMAIN``, ``DOWNLOAD_DELAY``, etc could behave
   in unexpected ways since delays and concurrency settings are no longer
   per-domain.

3. Some options depend on each other - for example, if you use timeout_
   Splash option then you may want to set ``download_timeout``
   scrapy.Request meta key as well.

ScrapyJS utlities allow to handle such edge cases and reduce the boilerplate.

.. _HTTP API: http://splash.readthedocs.org/en/latest/api.html
.. _timeout: http://splash.readthedocs.org/en/latest/api.html#arg-timeout



Contributing
============

Source code and bug tracker are on github:
https://github.com/scrapy-plugins/scrapy-splash

To run tests, install "tox" Python package and then run ``tox`` command
from the source checkout.
