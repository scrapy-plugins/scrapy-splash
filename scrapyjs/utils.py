# -*- coding: utf-8 -*-
from __future__ import absolute_import
import hashlib
import six
from six.moves.http_cookies import SimpleCookie, Morsel

from scrapy.http import Headers

try:
    from scrapy.utils.python import to_bytes, to_unicode, to_native_str
except ImportError:
    # scrapy < 1.1
    from scrapy.utils.python import unicode_to_str as to_bytes
    from scrapy.utils.python import str_to_unicode as to_unicode

    def to_native_str(text, encoding=None, errors='strict'):
        """ Return str representation of `text`
        (bytes in Python 2.x and unicode in Python 3.x). """
        if six.PY2:
            return to_bytes(text, encoding, errors)
        else:
            return to_unicode(text, encoding, errors)


def dict_hash(obj, start=''):
    """ Return a hash for a dict, based on its contents """
    h = hashlib.sha1(to_bytes(start))
    h.update(to_bytes(obj.__class__.__name__))
    if isinstance(obj, dict):
        for key, value in sorted(obj.items()):
            h.update(to_bytes(key))
            h.update(to_bytes(dict_hash(value)))
    elif isinstance(obj, (list, tuple)):
        for el in obj:
            h.update(to_bytes(dict_hash(el)))
    else:
        # basic types
        if isinstance(obj, bool):
            value = str(int(obj))
        elif isinstance(obj, (six.integer_types, float)):
            value = str(obj)
        elif isinstance(obj, (six.text_type, bytes)):
            value = obj
        else:
            raise ValueError("Unsupported value type: %s" % obj.__class__)
        h.update(to_bytes(value))
    return h.hexdigest()


def headers_to_scrapy(headers):
    """
    Return scrapy.http.Headers instance from headers data.
    3 data formats are supported:

    * {name: value, ...} dict;
    * [(name, value), ...] list;
    * [{'name': name, 'value': value'}, ...] list (HAR headers format).
    """
    if isinstance(headers or {}, dict):
        return Headers(headers or {})

    if isinstance(headers[0], dict):
        return Headers([
            (d['name'], d.get('value', ''))
            for d in headers
        ])

    return Headers(headers)


def cookies_to_header_values(cookie_data):
    """
    Convert cookie data to a list of Set-Cookie header values.
    Cookie data can be either

    * a list of strings (it is returned as-is);
    * a list of dicts in HAR cookie format
      (see http://www.softwareishard.com/blog/har-12-spec/#cookies)
    """
    if not cookie_data:
        return []

    first = cookie_data[0]

    if isinstance(first, six.string_types):
        return cookie_data

    if isinstance(first, dict):  # HAR cookies
        return [har_cookie_to_morsel(c).OutputString() for c in cookie_data]

    raise ValueError("Invalid data format: expected a list of strings or "
                     "dicts, got a list of %s instead" % first.__class__)


def har_cookie_to_morsel(cookie):
    """
    Convert a cookie in HAR format to http.cookies.Morsel instance.

    >>> har_cookie =  {
    ...     "name": "TestCookie",
    ...     "value": "Cookie Value",
    ...     "path": "/",
    ...     "domain": "www.janodvarko.cz",
    ...     "expires": "2009-07-24T19:20:30.123+02:00",
    ...     "httpOnly": False,
    ...     "secure": True,
    ...     "comment": "this is a test"
    ... }
    >>> m = har_cookie_to_morsel(har_cookie)
    >>> m.key
    'TestCookie'
    >>> m.value
    'Cookie Value'
    >>> m['expires']
    '2009-07-24T19:20:30.123+02:00'
    >>> m['path']
    '/'
    >>> m['comment']
    'this is a test'
    >>> m['domain']
    'www.janodvarko.cz'
    >>> m['max-age']
    ''
    >>> m['secure']
    True
    >>> m['version']
    ''
    >>> m['httponly']
    ''
    """
    kv_map = {
        'path': 'path',
        'domain': 'domain',
        'expires': 'expires',
        'httpOnly': 'httponly',
        'httponly': 'httponly',
        'version': 'version',
        'max-age': 'max-age',
        'secure': 'secure',
        'comment': 'comment',
    }

    c = SimpleCookie()
    c[to_native_str(cookie['name'])] = to_native_str(cookie.get('value', ''))
    for key, morsel in c.items():
        break
    for har_key, py_key in kv_map.items():
        if har_key in cookie:
            value = cookie[har_key]
            # Python 2.x workaround: in Python 2.x False value for
            # httponly still makes the attribute set.
            if value or (py_key not in {'secure', 'httponly'}):
                if isinstance(value, six.string_types):
                    # another Python 2.x workaround: cookie methods
                    # don't accept unicode
                    value = to_native_str(value)
                morsel[py_key] = value
    return morsel


