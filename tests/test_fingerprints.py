# -*- coding: utf-8 -*-
from __future__ import absolute_import
import pytest
import scrapy
from scrapy.dupefilters import request_fingerprint

from scrapy_splash.dupefilter import splash_request_fingerprint
from scrapy_splash.utils import dict_hash


def test_dict_hash():
    h1 = dict_hash({"foo": "bar", "bar": "baz"})
    h2 = dict_hash({"foo": "bar", "bar": "baz"})
    assert h1 == h2

    h3 = dict_hash({"egg": "spam"})
    assert h3 != h2


def test_dict_hash_nested():
    h1 = dict_hash({"foo": "bar", "bar": {"baz": "spam"}})
    h2 = dict_hash({"foo": "bar", "bar": {"baz": "spam"}})
    assert h1 == h2

    h3 = dict_hash({"foo": "bar", "bar": {"baz": "egg"}})
    h4 = dict_hash({"foo": "bar", "bar": {"bam": "spam"}})
    assert h3 != h2
    assert h4 != h2


def test_dict_hash_non_strings():
    h1 = dict_hash({"foo": "bar", "float": 1.1, "int": 2, "bool": False,
                    "seq": ["x", "y", (2, 3.7, {"x": 5, "y": [6, 7]})]})
    h2 = dict_hash({"foo": "bar", "float": 1.2, "int": 2, "bool": False})
    assert h1 != h2


def test_dict_hash_invalid():
    with pytest.raises(ValueError):
        dict_hash({"foo": scrapy})


def test_request_fingerprint_nosplash():
    r1 = scrapy.Request("http://example.com")
    r2 = scrapy.Request("http://example.com", meta={"foo": "bar"})
    assert request_fingerprint(r1) == splash_request_fingerprint(r1)
    assert request_fingerprint(r1) == request_fingerprint(r2)
    assert request_fingerprint(r1) == splash_request_fingerprint(r2)


def test_request_fingerprint_splash():
    r1 = scrapy.Request("http://example.com")
    r2 = scrapy.Request("http://example.com", meta={"splash": {"args": {"html": 1}}})
    r3 = scrapy.Request("http://example.com", meta={"splash": {"args": {"png": 1}}})
    r4 = scrapy.Request("http://example.com", meta={"foo": "bar", "splash": {"args": {"html": 1}}})
    r5 = scrapy.Request("http://example.com", meta={"splash": {"args": {"html": 1, "wait": 1.0}}})

    assert request_fingerprint(r1) == request_fingerprint(r2)
    assert splash_request_fingerprint(r1) != splash_request_fingerprint(r2)
    assert splash_request_fingerprint(r1) != splash_request_fingerprint(r3)
    assert splash_request_fingerprint(r1) != splash_request_fingerprint(r4)
    assert splash_request_fingerprint(r1) != splash_request_fingerprint(r5)
    assert splash_request_fingerprint(r2) != splash_request_fingerprint(r3)

    # only "splash" contents is taken into account
    assert splash_request_fingerprint(r2) == splash_request_fingerprint(r4)
