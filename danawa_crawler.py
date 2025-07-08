# -*- coding: utf-8 -*-

# danawa_cralwer.py
# sammy310


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from datetime import datetime
from datetime import timedelta
from pytz import timezone
import csv
import os
import os.path
import shutil
import traceback

from multiprocessing import Pool

from github import Github

IS_TEST = False
# IS_TEST = True

PROCESS_COUNT = 2

GITHUB_TOKEN_KEY = 'MY_GITHUB_TOKEN'
GITHUB_REPOSITORY_NAME = 'sammy310/Danawa-Crawler'

CRAWLING_DATA_CSV_FILE = 'CrawlingCategory.csv'
if IS_TEST:
    CRAWLING_DATA_CSV_FILE = 'CrawlingCategory_test.csv'

DATA_PATH = 'crawl_data'
DATA_REFRESH_PATH = f'{DATA_PATH}/Last_Data'

TIMEZONE = 'Asia/Seoul'

CHROMEDRIVER_PATH = 'chromedriver'
if IS_TEST:
    CHROMEDRIVER_PATH = 'chromedriver_112.exe'

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
        self.chrome_option = Options()
        self.chrome_option.add_argument('--headless')
        self.chrome_option.add_argument('--window-size=1920x1080')
        self.chrome_option.add_argument('--start-maximized')
        self.chrome_option.add_argument('--disable-gpu')
        self.chrome_option.add_argument('lang=ko=KR')
        custom_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
        self.chrome_option.add_argument(f'user-agent={custom_user_agent}')
        self.chrome_option.add_argument('--no-sandbox')
        self.chrome_option.add_argument('--disable-dev-shm-usage')


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
            # browser = webdriver.Chrome(CHROMEDRIVER_PATH, options=self.chrome_option)
            browser = webdriver.Chrome(options=self.chrome_option)
            browser.implicitly_wait(5)
            browser.get(crawlingURL)

            browser.find_element(By.XPATH, '//option[@value="90"]').click()
        
            wait = WebDriverWait(browser, 10)
            wait.until(EC.invisibility_of_element((By.CLASS_NAME, 'product_list_cover')))
            
            for i in range(-1, crawlingSize):
                if i == -1:
                    browser.find_element(By.XPATH, '//li[@data-sort-method="NEW"]').click()
                elif i == 0:
                    browser.find_element(By.XPATH, '//li[@data-sort-method="BEST"]').click()
                elif i > 0:
                    if i % 10 == 0:
                        browser.find_element(By.XPATH, '//a[@class="edge_nav nav_next"]').click()
                    else:
                        browser.find_element(By.XPATH, '//a[@class="num "][%d]'%(i%10)).click()
                wait.until(EC.invisibility_of_element((By.CLASS_NAME, 'product_list_cover')))
                
                # Get Product List
                productListDiv = browser.find_element(By.XPATH, '//div[@class="main_prodlist main_prodlist_list"]')
                products = productListDiv.find_elements(By.XPATH, '//ul[@class="product_list"]/li')

                for product in products:
                    if not product.get_attribute('id'):
                        continue

                    # ad
                    if 'prod_ad_item' in product.get_attribute('class').split(' '):
                        continue
                    if product.get_attribute('id').strip().startswith('ad'):
                        continue

                    productId = product.get_attribute('id')[11:]
                    productName = product.find_element(By.XPATH, './div/div[2]/p/a').text.strip()
                    productPrices = product.find_elements(By.XPATH, './div/div[3]/ul/li')
                    productPriceStr = ''

                    # Check Mall
                    isMall = False
                    if 'prod_top5' in product.find_element(By.XPATH, './div/div[3]').get_attribute('class').split(' '):
                        isMall = True
                    
                    if isMall:
                        for productPrice in productPrices:
                            if 'top5_button' in productPrice.get_attribute('class').split(' '):
                                continue
                            
                            if productPriceStr:
                                productPriceStr += DATA_PRODUCT_DIVIDER
                            
                            mallName = productPrice.find_element_by(By.XPATH, './a/div[1]').text.strip()
                            if not mallName:
                                mallName = productPrice.find_element(By.XPATH, './a/div[1]/span[1]').text.strip()
                            
                            price = productPrice.find_element(By.XPATH, './a/div[2]/em').text.strip()

                            productPriceStr += f'{mallName}{DATA_ROW_DIVIDER}{price}'
                    else:
                        for productPrice in productPrices:
                            if productPriceStr:
                                productPriceStr += DATA_PRODUCT_DIVIDER
                            
                            # Default
                            productType = productPrice.find_element(By.XPATH, './div/p').text.strip()

                            # like Ram/HDD/SSD
                            # HDD : 'WD60EZAZ, 6TB\n25원/1GB_149,000'
                            productType = productType.replace('\n', DATA_ROW_DIVIDER)

                            # Remove rank text
                            # 1위, 2위 ...
                            productType = self.RemoveRankText(productType)
                            
                            price = productPrice.find_element(By.XPATH, './p[2]/a/strong').text.strip()

                            if productType:
                                productPriceStr += f'{productType}{DATA_ROW_DIVIDER}{price}'
                            else:
                                productPriceStr += f'{price}'
                    
                    crawlingData_csvWriter.writerow([productId, productName, productPriceStr])

        except Exception as e:
            print('Error - ' + crawlingName + ' ->')
            print(traceback.format_exc())
            self.errorList.append(crawlingName)

        crawlingFile.close()

        print('Crawling Finish : ' + crawlingName)

    def RemoveRankText(self, productText):
        if len(productText) < 2:
            return productText
        
        char1 = productText[0]
        char2 = productText[1]

        if char1.isdigit() and (1 <= int(char1) and int(char1) <= 9):
            if char2 == '위':
                return productText[2:].strip()
        
        return productText

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
