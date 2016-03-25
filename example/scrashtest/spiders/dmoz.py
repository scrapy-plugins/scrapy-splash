# -*- coding: utf-8 -*-
import json

import scrapy
from scrapy.linkextractors import LinkExtractor


class DmozSpider(scrapy.Spider):
    name = "dmoz"
    allowed_domains = ["dmoz.org"]
    start_urls = ['http://www.dmoz.org/']

    # http_user = 'splash-user'
    # http_pass = 'splash-password'

    def parse(self, response):
        le = LinkExtractor()
        for link in le.extract_links(response):
            yield scrapy.Request(link.url, self.parse_link, meta={
                'splash': {
                    'args': {'har': 1, 'html': 0},
                }
            })

    def parse_link(self, response):
        res = json.loads(response.body_as_unicode())
        print(res["har"]["log"]["pages"])
