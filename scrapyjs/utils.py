# -*- coding: utf-8 -*-
from __future__ import absolute_import
import hashlib
import six

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


def scrapy_headers_to_unicode_dict(headers):
    """
    Convert scrapy.http.Headers instance to a dictionary
    suitable for JSON encoding.
    """
    return {
        to_unicode(key): to_unicode(b','.join(value))
        for key, value in headers.items()
    }
