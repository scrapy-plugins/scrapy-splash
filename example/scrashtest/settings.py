# -*- coding: utf-8 -*-

BOT_NAME = 'scrashtest'

SPIDER_MODULES = ['scrashtest.spiders']
NEWSPIDER_MODULE = 'scrashtest.spiders'

DOWNLOADER_MIDDLEWARES = {
    # Engine side
    'scrapyjs.middleware.SplashCookiesMiddleware': 723,
    'scrapyjs.SplashMiddleware': 725,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
    # Downloader side
}

DUPEFILTER_CLASS = 'scrapyjs.SplashAwareDupeFilter'
SPLASH_URL = 'http://192.168.59.103:8050/'
