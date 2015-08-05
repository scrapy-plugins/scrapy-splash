# -*- coding: utf-8 -*-
import json

import scrapy
from scrapy.linkextractors import LinkExtractor


class DmozSpider(scrapy.Spider):
    name = "dmoz"
    allowed_domains = ["dmoz.org"]
    start_urls = ['http://www.dmoz.org/']

    def parse(self, response):
        le = LinkExtractor()
        for link in le.extract_links(response):
            yield scrapy.Request(link.url, self.parse_link, meta={
                'splash': {
                    'args': {'har': 1, 'html': 0},
                }
            })

    def parse_link(self, response):
        res = json.loads(response.body)
        print(res["har"]["log"]["pages"])
