==============================================
Scrapy & JavaScript integration through Splash
==============================================

.. image:: https://img.shields.io/pypi/v/scrapy-splash.svg
   :target: https://pypi.python.org/pypi/scrapy-splash
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

Install scrapy-splash using pip::

    $ pip install scrapy-splash

Scrapy-Splash uses Splash_ HTTP API, so you also need a Splash instance.
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
          'scrapy_splash.SplashCookiesMiddleware': 723,
          'scrapy_splash.SplashMiddleware': 725,
          'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
      }

   Order `723` is just before `HttpProxyMiddleware` (750) in default
   scrapy settings.

   HttpCompressionMiddleware priority should be changed in order to allow
   advanced response processing; see https://github.com/scrapy/scrapy/issues/1895
   for details.

3. Enable ``SplashDeduplicateArgsMiddleware`` by adding it to
   ``SPIDER_MIDDLEWARES`` in your ``settings.py``::

      SPIDER_MIDDLEWARES = {
          'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
      }

   This middleware is needed to support ``cache_args`` feature; it allows
   to save disk space by not storing duplicate Splash arguments multiple
   times in a disk request queue. If Splash 2.1+ is used the middleware
   also allows to save network traffic by not sending these duplicate
   arguments to Splash server multiple times.

4. Set a custom ``DUPEFILTER_CLASS``::

      DUPEFILTER_CLASS = 'scrapy_splash.SplashAwareDupeFilter'

5. If you use Scrapy HTTP cache then a custom cache storage backend
   is required. scrapy-splash provides a subclass of
   ``scrapy.contrib.httpcache.FilesystemCacheStorage``::

      HTTPCACHE_STORAGE = 'scrapy_splash.SplashAwareFSCacheStorage'

   If you use other cache storage then it is necesary to subclass it and
   replace all ``scrapy.util.request.request_fingerprint`` calls with
   ``scrapy_splash.splash_request_fingerprint``.

.. note::

    Steps (4) and (5) are necessary because Scrapy doesn't provide a way
    to override request fingerprints calculation algorithm globally; this
    could change in future.


There are also some additional options available.
Put them into your ``settings.py`` if you want to change the defaults:

* ``SPLASH_COOKIES_DEBUG`` is ``False`` by default.
  Set to ``True`` to enable debugging cookies in the ``SplashCookiesMiddleware``.
  This option is similar to ``COOKIES_DEBUG``
  for the built-in scarpy cookies middleware: it logs sent and received cookies
  for all requests.
* ``SPLASH_LOG_400`` is ``True`` by default - it instructs to log all 400 errors
  from Splash. They are important because they show errors occurred
  when executing the Splash script. Set it to ``False`` to disable this logging.
* ``SPLASH_SLOT_POLICY`` is ``scrapy_splash.SlotPolicy.PER_DOMAIN`` by default.
  It specifies how concurrency & politeness are maintained for Splash requests,
  and specify the default value for ``slot_policy`` argument for
  ``SplashRequest``, which is described below.


Usage
=====

Requests
--------

The easiest way to render requests with Splash is to
use ``scrapy_splash.SplashRequest``::

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
        slot_policy=scrapy_splash.SlotPolicy.PER_DOMAIN,  # optional
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
            'slot_policy': scrapy_splash.SlotPolicy.PER_DOMAIN,
            'splash_headers': {},       # optional; a dict with headers sent to Splash
            'dont_process_response': True, # optional, default is False
            'dont_send_headers': True,  # optional, default is False
            'magic_response': False,    # optional, default is True
        }
    })

Use ``request.meta['splash']`` API in middlewares or when scrapy.Request
subclasses are used (there is also ``SplashFormRequest`` described below).
For example, ``meta['splash']`` allows to create a middleware which enables
Splash for all outgoing requests by default.

``SplashRequest`` is a convenient utility to fill ``request.meta['splash']``;
it should be easier to use in most cases. For each ``request.meta['splash']``
key there is a corresponding ``SplashRequest`` keyword argument: for example,
to set ``meta['splash']['args']`` use ``SplashRequest(..., args=myargs)``.

* ``meta['splash']['args']`` contains arguments sent to Splash.
  scrapy-splash adds some default keys/values to ``args``:

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

* ``meta['splash']['cache_args']`` is a list of argument names to cache
  on Splash side. These arguments are sent to Splash only once, then cached
  values are used; it allows to save network traffic and decreases request
  queue disk memory usage. Use ``cache_args`` only for large arguments
  which don't change with each request; ``lua_source`` is a good candidate
  (if you don't use string formatting to build it). Splash 2.1+ is required
  for this feature to work.

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

  1. ``scrapy_splash.SlotPolicy.PER_DOMAIN`` (default) - send Splash requests to
     downloader slots based on URL being rendered. It is useful if you want
     to maintain per-domain politeness & concurrency settings.

  2. ``scrapy_splash.SlotPolicy.SINGLE_SLOT`` - send all Splash requests to
     a single downloader slot. It is useful if you want to throttle requests
     to Splash.

  3. ``scrapy_splash.SlotPolicy.SCRAPY_DEFAULT`` - don't do anything with slots.
     It is similar to ``SINGLE_SLOT`` policy, but can be different if you access
     other services on the same address as Splash.

* ``meta['splash']['dont_process_response']`` - when set to True,
  SplashMiddleware won't change the response to a custom scrapy.Response
  subclass. By default for Splash requests one of SplashResponse,
  SplashTextResponse or SplashJsonResponse is passed to the callback.

* ``meta['splash']['dont_send_headers']``: by default scrapy-splash passes
  request headers to Splash in 'headers' JSON POST field. For all render.xxx
  endpoints it means Scrapy header options are respected by default
  (http://splash.readthedocs.org/en/stable/api.html#arg-headers). In Lua
  scripts you can use ``headers`` argument of ``splash:go`` to apply the
  passed headers: ``splash:go{url, headers=splash.args.headers}``.

  Set 'dont_send_headers' to True if you don't want to pass ``headers``
  to Splash.

* ``meta['splash']['http_status_from_error_code']`` - set response.status
  to HTTP error code when ``assert(splash:go(..))`` fails; it requires
  ``meta['splash']['magic_response']=True``. ``http_status_from_error_code``
  option is False by default if you use raw meta API;
  SplashRequest sets it to True by default.

* ``meta['splash']['magic_response']`` - when set to True and a JSON
  response is received from Splash, several attributes of the response
  (headers, body, url, status code) are filled using data returned in JSON:

  * response.headers are filled from 'headers' keys;
  * response.url is set to the value of 'url' key;
  * response.body is set to the value of 'html' key,
    or to base64-decoded value of 'body' key;
  * response.status is set to the value of 'http_status' key.
    When ``meta['splash']['http_status_from_error_code']`` is True
    and ``assert(splash:go(..))`` fails with an HTTP error
    response.status is also set to HTTP error code.

  This option is set to True by default if you use SplashRequest.
  ``render.json`` and ``execute`` endpoints may not have all the necessary
  keys/values in the response.
  For non-JSON endpoints, only url is filled, regardless of the
  ``magic_response`` setting.


Use ``scrapy_splash.SplashFormRequest`` if you want to make a ``FormRequest``
via splash. It accepts the same arguments as ``SplashRequest``,
and also ``formdata``, like ``FormRequest`` from scrapy::

    >>> SplashFormRequest('http://example.com', formdata={'foo': 'bar'})
    <POST http://example.com>

``SplashFormRequest.from_response`` is also supported, and works as described
in `scrapy documentation <http://scrapy.readthedocs.org/en/latest/topics/request-response.html#scrapy.http.FormRequest.from_response>`_.

Responses
---------

scrapy-splash returns Response subclasses for Splash requests:

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

* If Splash session handling is configured, you can access current cookies
  as ``response.cookiejar``; it is a CookieJar instance.

* If Scrapy-Splash response magic is enabled in request (default),
  several response attributes (headers, body, url, status code)
  are set automatically from original response body:

  * response.headers are filled from 'headers' keys;
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

Session Handling
================

Splash itself is stateless - each request starts from a clean state.
In order to support sessions the following is required:

1. client (Scrapy) must send current cookies to Splash;
2. Splash script should make requests using these cookies and update
   them from HTTP response headers or JavaScript code;
3. updated cookies should be sent back to the client;
4. client should merge current cookies wiht the updated cookies.

For (2) and (3) Splash provides ``spalsh:get_cookies()`` and
``splash:init_cookies()`` methods which can be used in Splash Lua scripts.

scrapy-splash provides helpers for (1) and (4): to send current cookies
in 'cookies' field and merge cookies back from 'cookies' response field
set ``request.meta['splash']['session_id']`` to the session
identifier. If you only want a single session use the same ``session_id`` for
all request; any value like '1' or 'foo' is fine.

For scrapy-splash session handling to work you must use ``/execute`` endpoint
and a Lua script which accepts 'cookies' argument and returns 'cookies'
field in the result::

   function main(splash)
       splash:init_cookies(splash.args.cookies)

       -- ... your script

       return {
           cookies = splash:get_cookies(),
           -- ... other results, e.g. html
       }
   end

SplashRequest sets ``session_id`` automatically for ``/execute`` endpoint,
i.e. cookie handling is enabled by default if you use SplashRequest,
``/execute`` endpoint and a compatible Lua rendering script.

If you want to start from the same set of cookies, but then 'fork' sessions
set ``request.meta['splash']['new_session_id']`` in addition to
``session_id``. Request cookies will be fetched from cookiejar ``session_id``,
but response cookies will be merged back to the ``new_session_id`` cookiejar.

Standard Scrapy ``cookies`` argument can be used with ``SplashRequest``
to add cookies to the current Splash cookiejar.

Examples
========

Get HTML contents::

    import scrapy
    from scrapy_splash import SplashRequest

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
    from scrapy_splash import SplashRequest

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
    from scrapy_splash import SplashRequest


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
    from scrapy_splash import SplashRequest

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


Use a Lua script to get an HTML response with cookies, headers, body
and method set to correct values; ``lua_source`` argument value is cached
on Splash server and is not sent with each request (it requires Splash 2.1+)::

    import scrapy
    from scrapy_splash import SplashRequest

    script = """
    function last_response_headers(splash)
      local entries = splash:history()
      local last_entry = entries[#entries]
      return last_entry.response.headers
    end

    function main(splash)
      splash:init_cookies(splash.args.cookies)
      assert(splash:go{
        splash.args.url,
        headers=splash.args.headers,
        http_method=splash.args.http_method,
        body=splash.args.body,
        })
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
                cache_args=['lua_source'],
                args={'lua_source': script},
                headers={'X-My-Header': 'value'},
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

The obvious alternative to scrapy-splash would be to send requests directly
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

6. Default Scrapy duplication filter doesn't take Splash specifics in
   account. For example, if an URL is sent in a JSON POST request body
   Scrapy will compute request fingerprint without canonicalizing this URL.

7. Splash Bad Request (HTTP 400) errors are hard to debug because by default
   response content is not displayed by Scrapy. SplashMiddleware logs content
   of HTTP 400 Splash responses by default (it can be turned off by setting
   ``SPLASH_LOG_400 = False`` option).

8. Cookie handling is tedious to implement, and you can't use Scrapy
   built-in Cookie middleware to handle cookies when working with Splash.

9. Large Splash arguments which don't change with every request
   (e.g. ``lua_source``) may take a lot of space when saved to Scrapy disk
   request queues. ``scrapy-splash`` provides a way to store such static
   parameters only once.

10. Splash 2.1+ provides a way to save network traffic by caching large
    static arguments on server, but it requires client support: client should
    send proper ``save_args`` and ``load_args`` values and handle HTTP 498
    responses.

scrapy-splash utlities allow to handle such edge cases and reduce
the boilerplate.

.. _HTTP API: http://splash.readthedocs.org/en/latest/api.html
.. _timeout: http://splash.readthedocs.org/en/latest/api.html#arg-timeout


Contributing
============

Source code and bug tracker are on github:
https://github.com/scrapy-plugins/scrapy-splash

To run tests, install "tox" Python package and then run ``tox`` command
from the source checkout.
