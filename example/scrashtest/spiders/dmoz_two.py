# -*- coding: utf-8 -*-
from urlparse import urljoin
import json

import scrapy
from scrapy.contrib.linkextractors import LinkExtractor


class DmozSpider(scrapy.Spider):
    name = "js_spider"
    start_urls = ['http://www.isjavascriptenabled.com/']
    splash = {'args': {'har': 1, 'html': 1}}

    def parse(self, response):
        is_js = response.xpath("//h1/text()").extract()
        if "".join(is_js).lower() == "yes":
            self.log("JS enabled!")
        else:
            self.log("Error! JS disabled!", scrapy.log.ERROR)
        le = LinkExtractor()

        for link in le.extract_links(response):
            url = urljoin(response.url, link.url)
            yield scrapy.Request(url, self.parse_link)
            break

    def parse_link(self, response):
        title = response.xpath("//title").extract()
        yes = response.xpath("//h1").extract()
        self.log("response is: {}".format(repr(response)))
        self.log(u"Html in response contains {} {}".format("".join(title), "".join(yes)))
