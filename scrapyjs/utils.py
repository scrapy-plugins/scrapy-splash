# -*- coding: utf-8 -*-
from __future__ import absolute_import
import hashlib

from scrapy.utils.python import unicode_to_str


def dict_hash(dct, start=''):
    """ Return a hash for a dict, based on its contents """
    h = hashlib.sha1(start)
    for key, value in sorted(dct.items()):
        h.update(key)
        if isinstance(value, dict):
            h.update(dict_hash(value))
        else:
            if isinstance(value, (bool, int)):
                value = str(int(value))
            h.update(unicode_to_str(value, 'utf8'))
    return h.hexdigest()


