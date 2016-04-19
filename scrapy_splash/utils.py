# -*- coding: utf-8 -*-
from __future__ import absolute_import
import json
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


def _process(value, sha=False):
    if isinstance(value, (six.text_type, bytes)):
        if sha:
            return hashlib.sha1(to_bytes(value)).hexdigest()
        return 'h', hash(value)
    if isinstance(value, dict):
        return {_process(k, sha=True): _process(v, sha) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_process(v, sha) for v in value]
    return value


def _fast_hash(value):
    """
    Return a hash for any JSON-serializable value.
    Hash is not guaranteed to be the same in different Python processes,
    but it is very fast to compute for data structures with large string
    values.
    """
    return _json_based_hash(_process(value))


_hash_cache = {}  # fast hash => hash
def json_based_hash(value):
    """
    Return a hash for any JSON-serializable value.

    >>> json_based_hash({"foo": "bar", "baz": [1, 2]})
    '0570066939bea46c610bfdc35b20f37ef09d05ed'
    """
    fp = _fast_hash(value)
    if fp not in _hash_cache:
        _hash_cache[fp] = _json_based_hash(_process(value, sha=True))
    return _hash_cache[fp]


def _json_based_hash(value):
    v = json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf8')
    return hashlib.sha1(v).hexdigest()


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


def parse_x_splash_saved_arguments_header(value):
    """
    Parse X-Splash-Saved-Arguments header value.

    >>> value = u"name1=9a6747fc6259aa374ab4e1bb03074b6ec672cf99;name2=ba001160ef96fe2a3f938fea9e6762e204a562b3"
    >>> dct = parse_x_splash_saved_arguments_header(value)
    >>> sorted(list(dct.keys()))
    ['name1', 'name2']
    >>> dct['name1']
    '9a6747fc6259aa374ab4e1bb03074b6ec672cf99'
    >>> dct['name2']
    'ba001160ef96fe2a3f938fea9e6762e204a562b3'

    Binary header values are also supported:
    >>> dct2 = parse_x_splash_saved_arguments_header(value.encode('utf8'))
    >>> dct2 == dct
    True
    """
    value = to_unicode(value)
    return dict(kv.split('=', 1) for kv in  value.split(";"))
