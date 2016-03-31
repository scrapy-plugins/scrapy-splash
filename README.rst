=========================================================
ScrapyJS - Scrapy & JavaScript integration through Splash
=========================================================

.. image:: https://img.shields.io/pypi/v/scrapyjs.svg
   :target: https://pypi.python.org/pypi/scrapyjs
   :alt: PyPI Version

.. image:: https://travis-ci.org/scrapy-plugins/scrapy-splash.svg?branch=master
   :target: http://travis-ci.org/scrapy-plugins/scrapy-splash
   :alt: Build Status

.. image:: http://codecov.io/github/scrapy-plugins/scrapy-splash/coverage.svg?branch=master
   :target: http://codecov.io/github/scrapy-plugins/scrapy-splash?branch=master
   :alt: Code Coverage

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

1. Add the Splash server address to ``settings.py`` of your Scrapy project
   like this::

      SPLASH_URL = 'http://192.168.59.103:8050'

2. Enable the Splash middleware by adding it to ``DOWNLOADER_MIDDLEWARES``
   in your ``settings.py`` file and changing HttpCompressionMiddleware
   priority::

      DOWNLOADER_MIDDLEWARES = {
          'scrapyjs.SplashMiddleware': 725,
          'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
      }

.. note::

   Order `725` is just before `HttpProxyMiddleware` (750) in default
   scrapy settings. `725` is also after ``CookiesMiddleware`` (700);
   this allows Scrapy to handle cookies.

   HttpCompressionMiddleware priority should be changed in order to allow
   advanced response processing; see https://github.com/scrapy/scrapy/issues/1895
   for details.

3. Set a custom ``DUPEFILTER_CLASS``::

      DUPEFILTER_CLASS = 'scrapyjs.SplashAwareDupeFilter'

4. If you use Scrapy HTTP cache then a custom cache storage backend
   is required. ScrapyJS provides a subclass of
   ``scrapy.contrib.httpcache.FilesystemCacheStorage``::

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

Requests
--------

The easiest way to render requests with Splash is to
use ``scrapyjs.SplashRequest``::

    yield SplashRequest(url, self.parse_result,
        args={
            # optional; parameters passed to Splash HTTP API
            'wait': 0.5,

            # 'url' is prefilled from request url
            # 'http_method' is set to 'POST' for POST requests
            # 'body' is set to request body for POST requests
        },
        endpoint='render.json', # optional; default is render.html
        splash_url='<url>',     # optional; overrides SPLASH_URL
        slot_policy=scrapyjs.SlotPolicy.PER_DOMAIN,  # optional
    )

Alternatively, you can use regular scrapy.Request and
``'splash'`` Request `meta` key::

    yield scrapy.Request(url, self.parse_result, meta={
        'splash': {
            'args': {
                # set rendering arguments here
                'html': 1,
                'png': 1,

                # 'url' is prefilled from request url
                # 'http_method' is set to 'POST' for POST requests
                # 'body' is set to request body for POST requests
            },

            # optional parameters
            'endpoint': 'render.json',  # optional; default is render.json
            'splash_url': '<url>',      # optional; overrides SPLASH_URL
            'slot_policy': scrapyjs.SlotPolicy.PER_DOMAIN,
            'splash_headers': {},       # optional; a dict with headers sent to Splash
            'dont_process_response': True, # optional, default is False
            'magic_response': False,    # optional, default is True
        }
    })

Use ``request.meta['splash']`` API in middlewares or when other scrapy.Request
subclasses (e.g. scrapy.FormRequest) are used. For example, ``meta['splash']``
allows to create a middleware which enables Splash for all outgoing requests
by default.

``SplashRequest`` is a convenient utility to fill ``request.meta['splash']``;
it should be easier to use in most cases.

* ``meta['splash']['args']`` contains arguments sent to Splash.
  ScrapyJS adds some default keys/values to ``args``:

  * 'url' is set to request.url;
  * 'http_method' is set to 'POST' for POST requests;
  * 'body' is set to to request.body for POST requests.

  You can override default values by setting them explicitly.

  Note that by default Scrapy escapes URL fragments using AJAX escaping scheme.
  If you want to pass a URL with a fragment to Splash then set ``url``
  in ``args`` dict manually. This is handled automatically if you use
  ``SplashRequest``, but you need to keep that in mind if you use raw
  ``meta['splash']`` API.

  Splash 1.8+ is required to handle POST requests; in earlier Splash versions
  'http_method' and 'body' arguments are ignored. If you work with ``/execute``
  endpoint and want to support POST requests you have to handle
  ``http_method`` and ``body`` arguments in your Lua script manually.

* ``meta['splash']['endpoint']`` is the Splash endpoint to use.
   In case of SplashRequest
  `render.html <http://splash.readthedocs.org/en/latest/api.html#render-html>`_
  is used by default. If you're using raw scrapy.Request then
  `render.json <http://splash.readthedocs.org/en/latest/api.html#render-json>`_
  is a default (for historical reasons). It is better to always pass endpoint
  explicitly.

  See Splash `HTTP API docs`_ for a full list of available endpoints
  and parameters.

.. _HTTP API docs: http://splash.readthedocs.org/en/latest/api.html

* ``meta['splash']['splash_url']`` overrides the Splash URL set
  in ``settings.py``.

* ``meta['splash']['splash_headers']`` allows to add or change headers
  which are sent to Splash server. Note that this option **is not** for
  setting headers which are sent to the remote website.

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

* ``meta['splash']['dont_process_response']`` - when set to True,
  SplashMiddleware won't change the response to a custom scrapy.Response
  subclass. By default for Splash requests one of SplashResponse,
  SplashTextResponse or SplashJsonResponse is passed to the callback.

* ``meta['splash']['magic_response']`` - when set to True and a JSON
  response is received from Splash, several attributes of the response
  (headers, body, url, status code) are filled using data returned in JSON:

  * response.headers are filled from 'headers' and 'cookies' keys;
  * response.url is set to the value of 'url' key;
  * response.body is set to the value of 'html' key,
    or to base64-decoded value of 'body' key;
  * response.status is set to the value of 'http_status' key.

Responses
---------

ScrapyJS returns Response subclasses for Splash requests:

* SplashResponse is returned for binary Splash responses - e.g. for
  /render.png responses;
* SplashTextResponse is returned when the result is text - e.g. for
  /render.html responses;
* SplashJsonResponse is returned when the result is a JSON object - e.g.
  for /render.json responses or /execute responses when script returns
  a Lua table.

To use standard Response classes set ``meta['splash']['dont_process_response']=True``
or pass ``dont_process_response=True`` argument to SplashRequest.

All these responses set ``response.url`` to the URL of the original request
(i.e. to the URL of a website you want to render), not to the URL of the
requested Splash endpoint. "True" URL is still available as
``response.real_url``.

SplashJsonResponse provide extra features:

* ``response.data`` attribute contains response data decoded from JSON;
  you can access it like ``response.data['html']``.

* If Scrapy-Splash response magic is enabled in request (default),
  several response attributes (headers, body, url, status code)
  are set automatically from original response body:

  * response.headers are filled from 'headers' and 'cookies' keys;
  * response.url is set to the value of 'url' key;
  * response.body is set to the value of 'html' key,
    or to base64-decoded value of 'body' key;
  * response.status is set from the value of 'http_status' key.

When ``respone.body`` is updated in SplashJsonResponse
(either from 'html' or from 'body' keys) familiar ``response.css``
and ``response.xpath`` methods are available.

To turn off special handling of JSON result keys either set
``meta['splash']['magic_response']=False`` or pass ``magic_response=False``
argument to SplashRequest.

Examples
========

Get HTML contents::

    import scrapy
    from scrapyjs import SplashRequest

    class MySpider(scrapy.Spider):
        start_urls = ["http://example.com", "http://example.com/foo"]

        def start_requests(self):
            for url in self.start_urls:
                yield SplashRequest(url, self.parse, args={'wait': 0.5})

        def parse(self, response):
            # response.body is a result of render.html call; it
            # contains HTML processed by a browser.
            # ...

Get HTML contents and a screenshot::

    import json
    import base64
    import scrapy
    from scrapyjs import SplashRequest

    class MySpider(scrapy.Spider):

        # ...
            splash_args = {
                'html': 1,
                'png': 1,
                'width': 600,
                'render_all': 1,
            }
            yield SplashRequest(url, self.parse_result, endpoint='render.json',
                                args=splash_args)

        # ...
        def parse_result(self, response):
            # magic responses are turned ON by default,
            # so the result under 'html' key is available as response.body
            html = response.body

            # you can also query the html result as usual
            title = response.css('title').extract_first()

            # full decoded JSON data is available as response.data:
            png_bytes = base64.b64decode(response.data['png'])

            # ...

Run a simple `Splash Lua Script`_::

    import json
    import base64
    from scrapyjs import SplashRequest


    class MySpider(scrapy.Spider):

        # ...
            script = """
            function main(splash)
                assert(splash:go(splash.args.url))
                return splash:evaljs("document.title")
            end
            """
            yield SplashRequest(url, self.parse_result, endpoint='execute',
                                args={'lua_source': script})

        # ...
        def parse_result(self, response):
            doc_title = response.body_as_unicode()
            # ...


More complex `Splash Lua Script`_ example - get a screenshot of an HTML
element by its CSS selector (it requires Splash 2.1+).
Note how are arguments passed to the script::

    import json
    import base64
    from scrapyjs import SplashRequest

    script = """
    -- Arguments:
    -- * url - URL to render;
    -- * css - CSS selector to render;
    -- * pad - screenshot padding size.

    -- this function adds padding around region
    function pad(r, pad)
      return {r[1]-pad, r[2]-pad, r[3]+pad, r[4]+pad}
    end

    -- main script
    function main(splash)

      -- this function returns element bounding box
      local get_bbox = splash:jsfunc([[
        function(css) {
          var el = document.querySelector(css);
          var r = el.getBoundingClientRect();
          return [r.left, r.top, r.right, r.bottom];
        }
      ]])

      assert(splash:go(splash.args.url))
      assert(splash:wait(0.5))

      -- don't crop image by a viewport
      splash:set_viewport_full()

      local region = pad(get_bbox(splash.args.css), splash.args.pad)
      return splash:png{region=region}
    end
    """

    class MySpider(scrapy.Spider):


        # ...
            yield SplashRequest(url, self.parse_element_screenshot,
                endpoint='execute',
                args={
                    'lua_source': script,
                    'pad': 32,
                    'css': 'a.title'
                }
             )

        # ...
        def parse_element_screenshot(self, response):
            image_data = response.body  # binary image data in PNG format
            # ...


Use a Lua script to get an HTML response with cookies and headers set to
correct values::

    import scrapy
    from scrapyjs import SplashRequest

    script = """
    function last_response_headers(splash)
      local entries = splash:history()
      local last_entry = entries[#entries]
      return last_entry.response.headers
    end

    function main(splash)
      assert(splash:go(splash.args.url))
      assert(splash:wait(0.5))

      return {
        headers = last_response_headers(splash),
        cookies = splash:get_cookies(),
        html = splash:html(),
      }
    end
    """

    class MySpider(scrapy.Spider):


        # ...
            yield SplashRequest(url, self.parse_result,
                endpoint='execute',
                args={'lua_source': script}
            )

        def parse_result(self, response):
            # here response.body contains result HTML;
            # response.headers are filled with headers from last
            # web page loaded to Splash;
            # cookies from all responses and from JavaScript are collected
            # and put into Set-Cookie response header, so that Scrapy
            # can remember them.



.. _Splash Lua Script: http://splash.readthedocs.org/en/latest/scripting-tutorial.html


HTTP Basic Auth
===============

If you need HTTP Basic Authentication to access Splash, use
Scrapy's HttpAuthMiddleware_.

Another option is ``meta['splash']['splash_headers']``: it allows to set
custom headers which are sent to Splash server; add Authorization header
to ``splash_headers`` if HttpAuthMiddleware doesn't fit for some reason.

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
                body = json.dumps({"url": url, "wait": 0.5}, sort_keys=True)
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

3. As seen by Scrapy, response.url is an URL of the Splash server.
   scrapy-splash fixes it to be an URL of a requested page.
   "Real" URL is still available as ``response.real_url``.

4. Some options depend on each other - for example, if you use timeout_
   Splash option then you may want to set ``download_timeout``
   scrapy.Request meta key as well.

5. It is easy to get it subtly wrong - e.g. if you won't use
   ``sort_keys=True`` argument when preparing JSON body then binary POST body
   content could vary even if all keys and values are the same, and it means
   dupefilter and cache will work incorrectly.

ScrapyJS utlities allow to handle such edge cases and reduce the boilerplate.

.. _HTTP API: http://splash.readthedocs.org/en/latest/api.html
.. _timeout: http://splash.readthedocs.org/en/latest/api.html#arg-timeout


Contributing
============

Source code and bug tracker are on github:
https://github.com/scrapy-plugins/scrapy-splash

To run tests, install "tox" Python package and then run ``tox`` command
from the source checkout.
