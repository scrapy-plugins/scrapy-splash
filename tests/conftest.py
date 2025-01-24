import os

import pytest
from .mockserver import MockServer
from .resources import SplashProtected


@pytest.fixture()
def settings():
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
        REQUEST_FINGERPRINTER_CLASS='scrapy_splash.SplashRequestFingerprinter',
    )
    return s


@pytest.fixture()
def settings_auth(settings):
    with MockServer(SplashProtected) as s:
        print("splash url:", s.root_url)
        settings['SPLASH_URL'] = s.root_url
        yield settings
