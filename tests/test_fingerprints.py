# -*- coding: utf-8 -*-
from __future__ import absolute_import
import scrapy
from scrapy.dupefilter import request_fingerprint
from scrapyjs.dupefilter import splash_request_fingerprint
from scrapyjs.utils import dict_hash


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

    assert request_fingerprint(r1) == request_fingerprint(r2)
    assert splash_request_fingerprint(r1) != splash_request_fingerprint(r2)
    assert splash_request_fingerprint(r1) != splash_request_fingerprint(r3)
    assert splash_request_fingerprint(r1) != splash_request_fingerprint(r4)
    assert splash_request_fingerprint(r2) != splash_request_fingerprint(r3)

    # only "splash" contents is taken into account
    assert splash_request_fingerprint(r2) == splash_request_fingerprint(r4)
