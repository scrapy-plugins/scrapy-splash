# -*- coding: utf-8 -*-
from __future__ import absolute_import
import hashlib
import six

try:
    from scrapy.utils.python import to_bytes
except ImportError:
    from scrapy.utils.python import unicode_to_str as to_bytes


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


