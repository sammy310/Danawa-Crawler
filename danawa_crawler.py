# -*- coding: utf-8 -*-

# danawa_cralwer.py
# sammy310


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scrapy.selector import Selector

from datetime import datetime
from datetime import timedelta
from pytz import timezone
import csv
import os
import os.path
import shutil

from multiprocessing import Pool

from github import Github

PROCESS_COUNT = 2

GITHUB_TOKEN_KEY = 'MY_GITHUB_TOKEN'
GITHUB_REPOSITORY_NAME = 'sammy310/Danawa-Crawler'

CRAWLING_DATA_CSV_FILE = 'CrawlingCategory.csv'
DATA_PATH = 'crawl_data'
DATA_REFRESH_PATH = f'{DATA_PATH}/Last_Data'

TIMEZONE = 'Asia/Seoul'

# CHROMEDRIVER_PATH = 'chromedriver_94.exe'
CHROMEDRIVER_PATH = 'chromedriver'

DATA_DIVIDER = '---'
DATA_REMARK = '//'
DATA_ROW_DIVIDER = '_'
DATA_PRODUCT_DIVIDER = '|'

STR_NAME = 'name'
STR_URL = 'url'
STR_CRAWLING_PAGE_SIZE = 'crawlingPageSize'


class DanawaCrawler:
    def __init__(self):
        self.errorList = list()
        self.crawlingCategory = list()
        with open(CRAWLING_DATA_CSV_FILE, 'r', newline='') as file:
            for crawlingValues in csv.reader(file, skipinitialspace=True):
                if not crawlingValues[0].startswith(DATA_REMARK):
                    self.crawlingCategory.append({STR_NAME: crawlingValues[0], STR_URL: crawlingValues[1], STR_CRAWLING_PAGE_SIZE: int(crawlingValues[2])})

    def StartCrawling(self):
        self.chrome_option = webdriver.ChromeOptions()
        self.chrome_option.add_argument('--headless')
        self.chrome_option.add_argument('--window-size=1920,1080')
        self.chrome_option.add_argument('--start-maximized')
        self.chrome_option.add_argument('--disable-gpu')
        self.chrome_option.add_argument('lang=ko=KR')

        if __name__ == '__main__':
            pool = Pool(processes=PROCESS_COUNT)
            pool.map(self.CrawlingCategory, self.crawlingCategory)
            pool.close()
            pool.join()

            
    
    def CrawlingCategory(self, categoryValue):
        crawlingName = categoryValue[STR_NAME]
        crawlingURL = categoryValue[STR_URL]
        crawlingSize = categoryValue[STR_CRAWLING_PAGE_SIZE]

        print('Crawling Start : ' + crawlingName)

        # data
        crawlingFile = open(f'{crawlingName}.csv', 'w', newline='', encoding='utf8')
        crawlingData_csvWriter = csv.writer(crawlingFile)
        crawlingData_csvWriter.writerow([self.GetCurrentDate().strftime('%Y-%m-%d %H:%M:%S')])
        
        try:
            browser = webdriver.Chrome(CHROMEDRIVER_PATH, options=self.chrome_option)
            browser.implicitly_wait(5)
            browser.get(crawlingURL)

            browser.find_element_by_xpath('//option[@value="90"]').click()
        
            wait = WebDriverWait(browser, 10)
            wait.until(EC.invisibility_of_element((By.CLASS_NAME, 'product_list_cover')))
            
            for i in range(-1, crawlingSize):
                if i == -1:
                    browser.find_element_by_xpath('//li[@data-sort-method="NEW"]').click()
                elif i == 0:
                    browser.find_element_by_xpath('//li[@data-sort-method="BEST"]').click()
                elif i > 0:
                    if i % 10 == 0:
                        browser.find_element_by_xpath('//a[@class="edge_nav nav_next"]').click()
                    else:
                        browser.find_element_by_xpath('//a[@class="num "][%d]'%(i%10)).click()
                wait.until(EC.invisibility_of_element((By.CLASS_NAME, 'product_list_cover')))
                
                html = browser.find_element_by_xpath('//div[@class="main_prodlist main_prodlist_list"]').get_attribute('outerHTML')
                selector = Selector(text=html)
                
                productIds = selector.xpath('//li[@class="prod_item prod_layer "]/@id').getall()
                if not productIds:
                    productIds = selector.xpath('//li[@class="prod_item prod_layer width_change"]/@id').getall()
                productNames = selector.xpath('//a[@name="productName"]/text()').getall()
                productPriceList = selector.xpath('//div[@class="prod_pricelist "]/ul')
                
                adCounter = 0
                errCounter = 0
                for j in range(len(productIds)) :
                    productId = productIds[j][11:]
                    productName = productNames[j].strip()
                    productPrice = ''
                    
                    bNotAd = False
                    while not bNotAd:
                        bMultiProduct = False
                        productPrice = ''

                        pList = productPriceList[j+adCounter+errCounter].xpath('li')
                        if pList[0].xpath('@class').get() == "opt_item":
                            adCounter += 1
                            bNotAd = False
                            continue
                        else:
                            if not pList[0].xpath('div').get():
                                errCounter += 1
                                continue
                            bNotAd = True
                        
                        priceStr = ''
                        for pStr in pList[0].xpath('div/p/text()').getall():
                            if bool(pStr.strip()):
                                priceStr += pStr.strip()
                        if priceStr:
                            bMultiProduct = True

                        if bMultiProduct:
                            for k in range(len(pList)):
                                for pStr in pList[k].xpath('div/p/text()').getall():
                                    if bool(pStr.strip()):
                                        productPrice += pStr.strip()
                                
                                if pList[k].xpath('div/p/a/span/text()').get():
                                    productPrice += DATA_ROW_DIVIDER + pList[k].xpath('div/p/a/span/text()').get()
                                elif pList[k].xpath('div/p/a/span/em/text()').get():
                                    productPrice += DATA_ROW_DIVIDER + pList[k].xpath('div/p/a/span/em/text()').get()

                                productPrice += DATA_ROW_DIVIDER
                                productPrice += pList[k].xpath('p[2]/a/strong/text()').get()
                                productPrice += DATA_PRODUCT_DIVIDER
                            
                            if productPrice[-1] == DATA_PRODUCT_DIVIDER:
                                productPrice = productPrice[:-1]
                        else:
                            productPrice = pList[0].xpath('p[2]/a/strong/text()').get()
                            if not productPrice:
                                errCounter += 1
                                continue
                            bNotAd = True
                    
                    crawlingData_csvWriter.writerow([productId, productName, productPrice])
            
        except Exception as e:
            print('Error - ' + crawlingName + ' ->')
            print(e)
            self.errorList.append(crawlingName)

        crawlingFile.close()

        print('Crawling Finish : ' + crawlingName)

    def DataSort(self):
        print('Data Sort\n')

        for crawlingValue in self.crawlingCategory:
            dataName = crawlingValue[STR_NAME]
            crawlingDataPath = f'{dataName}.csv'

            if not os.path.exists(crawlingDataPath):
                continue

            crawl_dataList = list()
            dataList = list()
            
            with open(crawlingDataPath, 'r', newline='', encoding='utf8') as file:
                csvReader = csv.reader(file)
                for row in csvReader:
                    crawl_dataList.append(row)
            
            if len(crawl_dataList) == 0:
                continue
            
            dataPath = f'{DATA_PATH}/{dataName}.csv'
            if not os.path.exists(dataPath):
                file = open(dataPath, 'w', encoding='utf8')
                file.close()
            with open(dataPath, 'r', newline='', encoding='utf8') as file:
                csvReader = csv.reader(file)
                for row in csvReader:
                    dataList.append(row)
            
            
            if len(dataList) == 0:
                dataList.append(['Id', 'Name'])
                
            dataList[0].append(crawl_dataList[0][0])
            dataSize = len(dataList[0])
            
            for product in crawl_dataList:
                if not str(product[0]).isdigit():
                    continue
                
                isDataExist = False
                for data in dataList:
                    if data[0] == product[0]:
                        if len(data) < dataSize:
                            data.append(product[2])
                        isDataExist = True
                        break
                
                if not isDataExist:
                    newDataList = ([product[0], product[1]])
                    for i in range(2,len(dataList[0])-1):
                        newDataList.append(0)
                    newDataList.append(product[2])
                
                    dataList.append(newDataList)
                
            for data in dataList:
                if len(data) < dataSize:
                    for i in range(len(data),dataSize):
                        data.append(0)
                
            
            productData = dataList.pop(0)
            dataList.sort(key= lambda x: x[1])
            dataList.insert(0, productData)
                
            with open(dataPath, 'w', newline='', encoding='utf8') as file:
                csvWriter = csv.writer(file)
                for data in dataList:
                    csvWriter.writerow(data)
                file.close()
                
            if os.path.isfile(crawlingDataPath):
                os.remove(crawlingDataPath)

    def DataRefresh(self):
        dTime = self.GetCurrentDate()
        if dTime.day == 1:
            print('Data Refresh\n')

            if not os.path.exists(DATA_PATH):
                os.mkdir(DATA_PATH)
            
            dTime -= timedelta(days=1)
            dateStr = dTime.strftime('%Y-%m')

            dataSavePath = f'{DATA_REFRESH_PATH}/{dateStr}'
            if not os.path.exists(dataSavePath):
                os.mkdir(dataSavePath)
            
            for file in os.listdir(DATA_PATH):
                fileName, fileExt = os.path.splitext(file)
                if fileExt == '.csv':
                    filePath = f'{DATA_PATH}/{file}'
                    refreshFilePath = f'{dataSavePath}/{file}'
                    shutil.move(filePath, refreshFilePath)
    
    def GetCurrentDate(self):
        tz = timezone(TIMEZONE)
        return (datetime.now(tz))

    def CreateIssue(self):
        if len(self.errorList) > 0:
            g = Github(os.environ[GITHUB_TOKEN_KEY])
            repo = g.get_repo(GITHUB_REPOSITORY_NAME)
            
            title = f'Crawling Error - ' + self.GetCurrentDate().strftime('%Y-%m-%d')
            body = ''
            for err in self.errorList:
                body += f'- {err}\n'
            labels = [repo.get_label('bug')]
            repo.create_issue(title=title, body=body, labels=labels)
        


if __name__ == '__main__':
    crawler = DanawaCrawler()
    crawler.DataRefresh()
    crawler.StartCrawling()
    crawler.DataSort()
    crawler.CreateIssue()
