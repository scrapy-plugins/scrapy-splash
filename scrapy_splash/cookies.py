# -*- coding: utf-8 -*-
"""
Cookie-related utilities.
"""
from __future__ import absolute_import
import time
import calendar

from six.moves.http_cookiejar import CookieJar, Cookie


def jar_to_har(cookiejar):
    """ Convert CookieJar to HAR cookies format """
    return [cookie_to_har(c) for c in cookiejar]


def har_to_jar(cookiejar, har_cookies, request_cookies=None):
    """ Add HAR cookies to the cookiejar.
    If request_cookies is given, remove cookies absent from har_cookies
    but present in request_cookies (they were removed). """
    har_cookie_keys = set()
    for c in har_cookies:
        cookie = har_to_cookie(c)
        cookiejar.set_cookie(cookie)
        har_cookie_keys.add(_cookie_key(cookie))
    if request_cookies:
        for c in request_cookies:
            cookie = har_to_cookie(c)
            if _cookie_key(cookie) not in har_cookie_keys:
                # We sent it but it did not come back: remove it
                try:
                    cookiejar.clear(cookie.domain, cookie.path, cookie.name)
                except KeyError:
                    pass  # It could have been already removed


def _cookie_key(cookie):
    return (cookie.domain, cookie.path, cookie.name)


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

    kwargs = dict(
        version=har_cookie.get('version') or 0,
        name=har_cookie['name'],
        value=har_cookie['value'],
        port=None,
        domain=har_cookie.get('domain', ''),
        path=har_cookie.get('path', '/'),
        secure=har_cookie.get('secure', False),
        expires=expires_timestamp,
        discard=False,
        comment=har_cookie.get('comment'),
        comment_url=bool(har_cookie.get('comment')),
        rest={'HttpOnly': har_cookie.get('httpOnly')},
        rfc2109=False,
    )
    kwargs['port_specified'] = bool(kwargs['port'])
    kwargs['domain_specified'] = bool(kwargs['domain'])
    kwargs['domain_initial_dot'] = kwargs['domain'].startswith('.')
    kwargs['path_specified'] = bool(kwargs['path'])
    return Cookie(**kwargs)


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
        tm = time.gmtime(cookie.expires)
        c['expires'] = time.strftime("%Y-%m-%dT%H:%M:%SZ", tm)

    http_only = cookie.get_nonstandard_attr('HttpOnly')
    if http_only is not None:
        c['httpOnly'] = bool(http_only)

    if cookie.comment:
        c['comment'] = cookie.comment

    return c
