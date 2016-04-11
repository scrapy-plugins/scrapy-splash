from scrapy_splash import SplashRequest


def test_meta_None():
    req1 = SplashRequest('http://example.com')
    req2 = SplashRequest('http://example.com', meta=None)
    assert req1.meta == req2.meta
