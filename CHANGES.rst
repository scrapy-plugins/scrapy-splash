Changes
=======

0.10.0 (2025-01-21)
-------------------

* Removed official support for Python 3.7 and 3.8, and added official support
  for Python 3.12 and 3.13.

* Added support for Scrapy 2.12+.

  This includes deprecating ``SplashAwareDupeFilter`` and
  ``SplashAwareFSCacheStorage`` in favor of the corresponding built-in, default
  Scrapy components, and instead using the new ``SplashRequestFingerprinter``
  component to ensure request fingerprinting for Splash requests stays the
  same, now for every Scrapy component doing request fingerprinting and not
  only for duplicate filtering and HTTP caching.

0.9.0 (2023-02-03)
------------------

* Removed official support for Python 2.7, 3.4, 3.5 and 3.6, and added official
  support for Python 3.9, 3.10 and 3.11.

* Deprecated ``SplashJsonResponse.body_as_unicode()``, to be replaced by
  ``SplashJsonResponse.text``.

* Removed calls to obsolete ``to_native_str``, removed in Scrapy 2.8.

0.8.0 (2021-10-05)
------------------

*   **Security bug fix:**

    If you use HttpAuthMiddleware_ (i.e. the ``http_user`` and ``http_pass``
    spider attributes) for Splash authentication, any non-Splash request will
    expose your credentials to the request target. This includes ``robots.txt``
    requests sent by Scrapy when the ``ROBOTSTXT_OBEY`` setting is set to
    ``True``.

    Use the new ``SPLASH_USER`` and ``SPLASH_PASS`` settings instead to set
    your Splash authentication credentials safely.

    .. _HttpAuthMiddleware: http://doc.scrapy.org/en/latest/topics/downloader-middleware.html#module-scrapy.downloadermiddlewares.httpauth

*   Responses now expose the HTTP status code and headers from Splash as
    ``response.splash_response_status`` and
    ``response.splash_response_headers`` (#158)

*   The ``meta`` argument passed to the ``scrapy_splash.request.SplashRequest``
    constructor is no longer modified (#164)

*   Website responses with 400 or 498 as HTTP status code are no longer
    handled as the equivalent Splash responses (#158)

*   Cookies are no longer sent to Splash itself (#156)

*   ``scrapy_splash.utils.dict_hash`` now also works with ``obj=None``
    (``225793b``)

*   Our test suite now includes integration tests (#156) and tests can be run
    in parallel (``6fb8c41``)

*   There’s a new ‘Getting help’ section in the ``README.rst`` file (#161,
    #162), the documentation about ``SPLASH_SLOT_POLICY`` has been improved
    (#157) and a typo as been fixed (#121)

*   Made some internal improvements (``ee5000d``, ``25de545``, ``2aaa79d``)


0.7.2 (2017-03-30)
------------------

* fixed issue with response type detection.

0.7.1 (2016-12-20)
------------------

* Scrapy 1.0.x support is back;
* README updates.

0.7 (2016-05-16)
----------------

* ``SPLASH_COOKIES_DEBUG`` setting allows to log cookies
  sent and received to/from Splash in ``cookies`` request/response fields.
  It is similar to Scrapy's builtin ``COOKIES_DEBUG``, but works for
  Splash requests;
* README cleanup.

0.6.1 (2016-04-29)
------------------

* Warning about HTTP methods is no longer logged for non-Splash requests.

0.6 (2016-04-20)
----------------

* ``SplashAwareDupeFilter`` and ``splash_request_fingerprint`` are improved:
  they now canonicalize URLs and take URL fragments in account;
* ``cache_args`` value fingerprints are now calculated faster.

0.5 (2016-04-18)
----------------

* ``cache_args`` SplashRequest argument and
  ``request.meta['splash']['cache_args']`` key allow to save network traffic
  and disk storage by not storing duplicate Splash arguments in disk request
  queues and not sending them to Splash multiple times. This feature requires
  Splash 2.1+.

To upgrade from v0.4 enable ``SplashDeduplicateArgsMiddleware`` in settings.py::

  SPIDER_MIDDLEWARES = {
      'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
  }

0.4 (2016-04-14)
----------------

* SplashFormRequest class is added; it is a variant of FormRequest which uses
  Splash;
* Splash parameters are no longer stored in request.meta twice; this change
  should decrease disk queues data size;
* SplashMiddleware now increases request priority when rescheduling the request;
  this should decrease disk queue data size and help with stale cookie
  problems.

0.3 (2016-04-11)
----------------

Package is renamed from ``scrapyjs`` to ``scrapy-splash``.

An easiest way to upgrade is to replace ``scrapyjs`` imports with
``scrapy_splash`` and update ``settings.py`` with new defaults
(check the README).

There are many new helpers to handle JavaScript rendering transparently;
the recommended way is now to use ``scrapy_splash.SplashRequest`` instead
of  ``request.meta['splash']``. Please make sure to read the README if
you're upgrading from scrapyjs - you may be able to drop some code from your
project, especially if you want to access response html, handle cookies
and headers.

* new SplashRequest class; it can be used as a replacement for scrapy.Request
  to provide a better integration with Splash;
* added support for POST requests;
* SplashResponse, SplashTextResponse and SplashJsonResponse allow to
  handle Splash responses transparently, taking care of response.url,
  response.body, response.headers and response.status. SplashJsonResponse
  allows to access decoded response JSON data as ``response.data``.
* cookie handling improvements: it is possible to handle Scrapy and Splash
  cookies transparently; current cookiejar is exposed as response.cookiejar;
* headers are passed to Splash by default;
* URLs with fragments are handled automatically when using SplashRequest;
* logging is improved: ``SplashRequest.__repr__`` shows both requested URL
  and Splash URL;
* in case of Splash HTTP 400 errors the response is logged by default;
* an issue with dupefilters is fixed: previously the order of keys in
  JSON request body could vary, making requests appear as non-duplicates;
* it is now possible to pass custom headers to Splash server itself;
* test coverage reports are enabled.

0.2 (2016-03-26)
----------------

* Scrapy 1.0 and 1.1 support;
* Python 3 support;
* documentation improvements;
* project is moved to https://github.com/scrapy-plugins/scrapy-splash.

0.1.1 (2015-03-16)
------------------

Fixed fingerprint calculation for non-string meta values.

0.1 (2015-02-28)
----------------

Initial release
