# -*- coding: utf-8 -*-
"""
Created on Sat Jun 20 11:23:18 2020

@author: sammy310
"""

import scrapy
import sys
from scrapy.spiders import Spider
#from scrapy.selector import HtmlXPathSelector
from computercrawler.items import ComputercrawlerItem
from scrapy.http import Request
from scrapy.selector import Selector

from selenium import webdriver
import time
import csv


class computercrawler_Spider(scrapy.Spider):
    name = "computercrawler"  #spider 이름
    allowed_domains = ["www.danawa.com"]  #최상위 도메인
    
    def __init__(self):
        self.browser = webdriver.Chrome("C:\\anaconda3\\chromedriver.exe")
        file = open('ComputerCrawlerFile.csv','a', newline='')
        csvWriter = csv.writer(file)
        csvWriter.writerow(["---"])
        csvWriter.writerow([time.strftime('%c', time.localtime(time.time()))])
        file.close()
 
    #1번만 실행
    def start_requests(self):
        yield scrapy.Request("http://prod.danawa.com/list/?cate=112747",self.parse)
 
    #아이템 parse
    def parse(self, response):
        self.browser.get('http://prod.danawa.com/list/?cate=112747')
        listSizeOption = self.browser.find_element_by_xpath('//option[@value="90"]')
        listSizeOption.click()
        
        time.sleep(10)
        
        
        
        html = self.browser.find_element_by_xpath('//*[@id="productListArea"]/div[4]/ul').get_attribute('outerHTML')
        selector = Selector(text=html)
        
        productIds = selector.xpath('//li[@class="prod_item prod_layer "]/@id').getall()
        productNames = selector.xpath('//a[@name="productName"]/text()').getall()
        productPrices = selector.xpath('//div[@class="prod_pricelist"]').xpath('ul/li[1]/p/a/strong/text()').getall()
        
        for i in range(len(productIds)) :
            item = ComputercrawlerItem()
            item['productId'] = productIds[i][11:]
            item['productName'] = productNames[i].strip()
            item['productPrice'] = productPrices[i]
            yield item
            
        self.browser.close()
