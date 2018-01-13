import os

import pytest
from scrapy.settings import Settings


@pytest.fixture()
def settings(request):
    """ Default scrapy-splash settings """
    s = dict(
        # collect scraped items to .collected_items attribute
        ITEM_PIPELINES={
            'tests.utils.CollectorPipeline': 100,
        },

        # scrapy-splash settings
        SPLASH_URL=os.environ.get('SPLASH_URL'),
        DOWNLOADER_MIDDLEWARES={
            # Engine side
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
            # Downloader side
        },
        SPIDER_MIDDLEWARES={
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        DUPEFILTER_CLASS='scrapy_splash.SplashAwareDupeFilter',
        HTTPCACHE_STORAGE='scrapy_splash.SplashAwareFSCacheStorage',
    )
    return Settings(s)


