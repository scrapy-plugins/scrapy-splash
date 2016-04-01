# -*- coding: utf-8 -*-
"""
Cookie-related utilities.
"""
from __future__ import absolute_import
import time
import calendar

from six.moves.http_cookiejar import CookieJar, Cookie, DefaultCookiePolicy


class SplashCookiePolicy(DefaultCookiePolicy):
    """
    Policy for shared Splash CookieJars.

    Unlike regular CookieJar we need to send all cookies in each request,
    not only matching cookies, because Splash fetches related resources.
    Splash handles domain/path filtering itself.
    """
    def set_ok_verifiability(self, cookie, request):
        return True

    def set_ok_path(self, cookie, request):
        return True

    def set_ok_domain(self, cookie, request):
        return True

    def set_ok_port(self, cookie, request):
        return True

    def return_ok(self, cookie, request):
        """Return true if (and only if) cookie should be returned to server."""
        return True

    def domain_return_ok(self, domain, request):
        """Return false if cookies should not be returned, given cookie domain.
        """
        return True

    def path_return_ok(self, path, request):
        """Return false if cookies should not be returned, given cookie path.
        """
        return True


def jar_to_har(cookiejar):
    """ Convert CookieJar to HAR cookies format """
    return [cookie_to_har(c) for c in cookiejar]


def har_to_jar(cookiejar, har_cookies):
    """ Add HAR cookies to the cookiejar """
    for c in har_cookies:
        cookiejar.set_cookie(har_to_cookie(c))


def har_to_cookie(har_cookie):
    """
    Convert a cookie dict in HAR format to a Cookie instance.

    >>> har_cookie =  {
    ...     "name": "TestCookie",
    ...     "value": "Cookie Value",
    ...     "path": "/foo",
    ...     "domain": "www.janodvarko.cz",
    ...     "expires": "2009-07-24T19:20:30Z",
    ...     "httpOnly": True,
    ...     "secure": True,
    ...     "comment": "this is a test"
    ... }
    >>> cookie = har_to_cookie(har_cookie)
    >>> cookie.name
    'TestCookie'
    >>> cookie.value
    'Cookie Value'
    >>> cookie.port
    >>> cookie.domain
    'www.janodvarko.cz'
    >>> cookie.path
    '/foo'
    >>> cookie.secure
    True
    >>> cookie.expires
    1248463230
    >>> cookie.comment
    'this is a test'
    >>> cookie.get_nonstandard_attr('HttpOnly')
    True
    """

    expires_timestamp = None
    if har_cookie.get('expires'):
        expires = time.strptime(har_cookie['expires'], "%Y-%m-%dT%H:%M:%SZ")
        expires_timestamp = calendar.timegm(expires)

    return create_cookie(
        comment=har_cookie.get('comment'),
        comment_url=bool(har_cookie.get('comment')),
        discard=False,
        domain=har_cookie.get('domain'),
        expires=expires_timestamp,
        name=har_cookie['name'],
        path=har_cookie.get('path'),
        port=None,
        rest={'HttpOnly': har_cookie.get('httpOnly', False)},
        rfc2109=False,
        secure=har_cookie.get('secure', False),
        value=har_cookie['value'],
        version=har_cookie.get('version') or 0,
    )


def cookie_to_har(cookie):
    """
    Convert a Cookie instance to a dict in HAR cookie format.
    """
    c = {
        'name': cookie.name,
        'value': cookie.value,
        'secure': cookie.secure,
    }
    if cookie.path_specified:
        c['path'] = cookie.path

    if cookie.domain_specified:
        c['domain'] = cookie.domain

    if cookie.expires:
        tm = time.localtime(cookie.expires)
        c['expires'] = time.strftime("%Y-%m-%dT%H:%M:%SZ", tm)

    http_only = cookie.get_nonstandard_attr('HttpOnly')
    if http_only is not None:
        c['httpOnly'] = bool(http_only)

    if cookie.comment:
        c['comment'] = cookie.comment

    return c


# Stolen from
# https://github.com/kennethreitz/requests/blob/master/requests/cookies.py:
def create_cookie(name, value, **kwargs):
    """Make a cookie from underspecified parameters.

    By default, the pair of `name` and `value` will be set for the domain ''
    and sent on every request (this is sometimes called a "supercookie").
    """
    result = dict(
        version=0,
        name=name,
        value=value,
        port=None,
        domain='',
        path='/',
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={'HttpOnly': None},
        rfc2109=False,)

    badargs = set(kwargs) - set(result)
    if badargs:
        err = 'create_cookie() got unexpected keyword arguments: %s'
        raise TypeError(err % list(badargs))

    result.update(kwargs)
    result['port_specified'] = bool(result['port'])
    result['domain_specified'] = bool(result['domain'])
    result['domain_initial_dot'] = result['domain'].startswith('.')
    result['path_specified'] = bool(result['path'])

    return Cookie(**result)
