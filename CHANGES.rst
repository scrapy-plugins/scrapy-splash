Changes
=======

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
