from scrapy.http import HtmlResponse, TextResponse, Response
from scrapy_splash.response import (
    SplashTextResponse, SplashHtmlResponse, SplashResponse,
)


def test_response_types():
    assert issubclass(SplashResponse, Response)
    assert issubclass(SplashTextResponse, TextResponse)
    assert issubclass(SplashHtmlResponse, HtmlResponse)
