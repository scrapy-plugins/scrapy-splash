from scrapy_splash import SplashRequest, SplashFormRequest


def test_meta_None():
    req1 = SplashRequest('http://example.com')
    req2 = SplashRequest('http://example.com', meta=None)
    assert req1.meta == req2.meta


def test_splash_form_request():
    req = SplashFormRequest(
        'http://example.com', formdata={'foo': 'bar'})
    assert req.method == 'POST'
    assert req.body == b'foo=bar'
    assert req.meta['splash']['args']['url'] == 'http://example.com'

    req = SplashFormRequest(
        'http://example.com', method='GET', formdata={'foo': 'bar'},
        endpoint='execute')
    assert req.method == 'GET'
    assert req.body == b''
    assert req.url == req.meta['splash']['args']['url'] ==\
        'http://example.com?foo=bar'
    assert req.meta['splash']['endpoint'] == 'execute'
