# -*- coding: utf-8 -*-
from __future__ import absolute_import
import hashlib


def dict_hash(obj, start=''):
    """ Return a hash for a dict, based on its contents """
    h = hashlib.sha1(start)
    h.update(obj.__class__.__name__)
    if isinstance(obj, dict):
        for key, value in sorted(obj.items()):
            h.update(key)
            h.update(dict_hash(value))
    elif isinstance(obj, (list, tuple)):
        for el in obj:
            h.update(dict_hash(el))
    else:
        # basic types
        if isinstance(obj, (bool, int)):
            value = str(int(obj))
        elif isinstance(obj, (long, float)):
            value = str(obj)
        elif isinstance(obj, unicode):
            value = obj.encode('utf8')
        elif isinstance(obj, bytes):
            value = obj
        else:
            raise ValueError("Unsupported value type: %s" % obj.__class__)
        h.update(value)
    return h.hexdigest()


