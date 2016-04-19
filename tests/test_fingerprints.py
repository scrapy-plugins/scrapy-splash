# -*- coding: utf-8 -*-
from __future__ import absolute_import
from copy import deepcopy

import pytest
import scrapy
from scrapy.dupefilters import request_fingerprint

from scrapy_splash import SplashRequest
from scrapy_splash.dupefilter import splash_request_fingerprint
from scrapy_splash.utils import dict_hash

from .test_middleware import _get_mw


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


def assert_fingerprints_match(r1, r2):
    assert splash_request_fingerprint(r1) == splash_request_fingerprint(r2)


def assert_fingerprints_dont_match(r1, r2):
    assert splash_request_fingerprint(r1) != splash_request_fingerprint(r2)


def test_request_fingerprint_splash():
    r1 = scrapy.Request("http://example.com")
    r2 = scrapy.Request("http://example.com", meta={"splash": {"args": {"html": 1}}})
    r3 = scrapy.Request("http://example.com", meta={"splash": {"args": {"png": 1}}})
    r4 = scrapy.Request("http://example.com", meta={"foo": "bar", "splash": {"args": {"html": 1}}})
    r5 = scrapy.Request("http://example.com", meta={"splash": {"args": {"html": 1, "wait": 1.0}}})

    assert request_fingerprint(r1) == request_fingerprint(r2)
    assert_fingerprints_dont_match(r1, r2)
    assert_fingerprints_dont_match(r1, r3)
    assert_fingerprints_dont_match(r1, r4)
    assert_fingerprints_dont_match(r1, r5)
    assert_fingerprints_dont_match(r2, r3)

    # only "splash" contents is taken into account
    assert_fingerprints_match(r2, r4)



@pytest.fixture()
def splash_middleware():
    return _get_mw()


@pytest.fixture
def splash_mw_process(splash_middleware):
    def _process(r):
        r_copy = r.replace(meta=deepcopy(r.meta))
        return splash_middleware.process_request(r_copy, None) or r
    return _process


@pytest.fixture()
def requests():
    url1 = "http://example.com/foo?x=1&y=2"
    url2 = "http://example.com/foo?y=2&x=1"
    url3 = "http://example.com/foo?x=1&y=2&z=3"
    url4 = "http://example.com/foo?x=1&y=2#id2"
    url5 = "http://example.com/foo?x=1&y=2#!id2"
    request_kwargs = [
        dict(url=url1),                         # 0
        dict(url=url1, method='POST'),          # 1
        dict(url=url1, endpoint='render.har'),  # 2
        dict(url=url2),                         # 3
        dict(url=url1, args={'wait': 0.5}),     # 4
        dict(url=url2, args={'wait': 0.5}),     # 5
        dict(url=url3),                         # 6
        dict(url=url2, method='POST'),          # 7
        dict(args={'wait': 0.5}),               # 8
        dict(args={'wait': 0.5}),               # 9
        dict(args={'wait': 0.7}),               # 10
        dict(url=url4),                         # 11
    ]
    splash_requests = [SplashRequest(**kwargs) for kwargs in request_kwargs]
    scrapy_requests = [
        scrapy.Request(url=url1),               # 12
        scrapy.Request(url=url2),               # 13
        scrapy.Request(url=url4),               # 14
        scrapy.Request(url=url5),               # 15
    ]
    return splash_requests + scrapy_requests


@pytest.mark.parametrize(["i", "dupe_indices"], [
    (0, {3}),
    (1, {7}),
    (2, set()),
    (3, {0}),
    (4, {5}),
    (5, {4}),
    (6, set()),
    (7, {1}),
    (8, {9}),
    (9, {8}),
    (10, set()),
    (11, set()),
    (12, {13, 14}),
    (13, {12, 14}),
    (14, {13, 12}),
    (15, set()),
])
def test_duplicates(i, dupe_indices, requests, splash_mw_process):
    def assert_not_filtered(r1, r2):
        assert_fingerprints_dont_match(r1, r2)
        assert_fingerprints_dont_match(
            splash_mw_process(r1),
            splash_mw_process(r2),
        )

    def assert_filtered(r1, r2):
        # request is filtered if it is filtered either
        # before rescheduling or after
        fp1 = splash_request_fingerprint(r1)
        fp2 = splash_request_fingerprint(r2)
        if fp1 != fp2:
            assert_fingerprints_match(
                splash_mw_process(r1),
                splash_mw_process(r2),
            )

    dupe_indices = set(dupe_indices)
    dupe_indices.add(i)
    non_dupe_indices = set(range(len(requests))) - dupe_indices

    for j in dupe_indices:
        assert_filtered(requests[i], requests[j])
    for j in non_dupe_indices:
        assert_not_filtered(requests[i], requests[j])
