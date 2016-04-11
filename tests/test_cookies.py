from scrapy_splash.cookies import har_to_cookie, cookie_to_har


# See also doctests in scrapy_splash.cookies module


def test_cookie_to_har():
    har_cookie = {
        "name": "TestCookie",
        "value": "Cookie Value",
        "path": "/foo",
        "domain": "www.janodvarko.cz",
        "expires": "2009-07-24T19:20:30Z",
        "httpOnly": True,
        "secure": True,
        "comment": "this is a test"
    }
    assert cookie_to_har(har_to_cookie(har_cookie)) == har_cookie
    cookie = har_to_cookie(har_cookie)
    assert vars(cookie) == vars(har_to_cookie(cookie_to_har(cookie)))
