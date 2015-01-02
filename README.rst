========================================
Scrapyjs - Scrapy+Javascript integration
========================================

This library provides Scrapy-Javascript integration through two different
mechanisms:

- a Scrapy download handler 
- a Scrapy downloader middlware

You only need to use ONE of them, not both.

Requirements
============

- python-gtk2
- python-webkit
- python-jswebkit

Usage
=====

Regardless of whether you are using the download handler or the downloader
middleware variant, the usage is the same: those requests containing a
"renderjs" key in request.meta will get download (and javascript rendered)
through webkit instead of the Scrapy downloader.

Download handler setup
======================

To enable the download handler add the following to your settings::

    DOWNLOAD_HANDLERS = {
        'http': 'scrapyjs.dhandler.WebkitDownloadHandler',
        'https': 'scrapyjs.dhandler.WebkitDownloadHandler',
    }

And make sure Scrapy uses the gtk2 reactor on twisted, for example by adding
the following lines to scrapy/__init__.py::

    from twisted.internet import gtk2reactor
    gtk2reactor.install()

Handler pros:

- it's asynchronous, and will merge with the main twisted reactor thread

Handler cons:

- requires patching scrapy (to use gtk2 reactor), but this could be fixed by
making Scrapy reactor type configurable.


Downloader middleware setup
==========================

To enable the downloader middleware add the following to your settings.py::

    DOWNLOADER_MIDDLEWARES = {
        'scrapyjs.middleware.WebkitDownloader': 1,
    }

Middleware pros:

- does not require patching scrapy (gtk reactor)

Middleware cons:

- blocking API (it spawns a gtk loop for each request)


TODO
====

- return WebView in response.meta, to support interaction and running custom
  javscript code from the spider
- support custom request headers (User-Agent, Accept, etc)
