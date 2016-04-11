Changes
=======

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
