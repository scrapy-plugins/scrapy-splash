import cgi

from scrapy.http import HtmlResponse
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


def test_form_request_from_response():
    # Copied from scrapy tests (test_from_response_submit_not_first_clickable)
    def _buildresponse(body, **kwargs):
        kwargs.setdefault('body', body)
        kwargs.setdefault('url', 'http://example.com')
        kwargs.setdefault('encoding', 'utf-8')
        return HtmlResponse(**kwargs)
    response = _buildresponse(
        """<form action="get.php" method="GET">
        <input type="submit" name="clickable1" value="clicked1">
        <input type="hidden" name="one" value="1">
        <input type="hidden" name="two" value="3">
        <input type="submit" name="clickable2" value="clicked2">
        </form>""")
    req = SplashFormRequest.from_response(
        response, formdata={'two': '2'}, clickdata={'name': 'clickable2'})
    assert req.method == 'GET'
    assert req.meta['splash']['args']['url'] == req.url
    fs = cgi.parse_qs(req.url.partition('?')[2], True)
    assert fs['clickable2'] == ['clicked2']
    assert 'clickable1' not in fs
    assert fs['one'] == ['1']
    assert fs['two'] == ['2']
