# -*- coding: utf-8 -*-

# danawa_cralwer.py
# sammy310


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException

from datetime import datetime
from datetime import timedelta
from pytz import timezone
import csv
import os
import os.path
import shutil
import sys
import time
import traceback

from multiprocessing import Pool

from github import Github

IS_TEST = False
# IS_TEST = True

PROCESS_COUNT = 2

CATEGORY_READY_ATTEMPTS = 4
CATEGORY_READY_TIMEOUT = 15
CATEGORY_READY_RETRY_DELAY = 3

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
        self.successfulCategoryNames = list()
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
            with Pool(processes=PROCESS_COUNT) as pool:
                results = pool.map(self.CrawlingCategory, self.crawlingCategory)

            self.errorList = list()
            self.successfulCategoryNames = list()
            for crawlingName, errorMessage in results:
                if errorMessage is None:
                    self.successfulCategoryNames.append(crawlingName)
                else:
                    self.errorList.append(crawlingName)

    def RemoveKnownBlockingOverlays(self, browser):
        browser.execute_script(
            "document.querySelectorAll('modal-widget').forEach(element => element.remove());"
        )

    def ClickElement(self, browser, xpath):
        wait = WebDriverWait(browser, 10)

        # Danawa can inject a modal-widget over the product list after page load.
        self.RemoveKnownBlockingOverlays(browser)
        element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))

        try:
            element.click()
        except ElementClickInterceptedException:
            # The widget can be injected again between lookup and click.
            self.RemoveKnownBlockingOverlays(browser)
            element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            browser.execute_script("arguments[0].click();", element)

    def GetCategoryReadinessState(self, browser):
        newXpath = '//li[@data-sort-method="NEW"]'
        bestXpath = '//li[@data-sort-method="BEST"]'
        option90Xpath = '//option[@value="90"]'
        productXpath = '//ul[@class="product_list"]/li[@id]'

        return {
            'title': browser.title,
            'ready': browser.execute_script('return document.readyState'),
            'new': len(browser.find_elements(By.XPATH, newXpath)),
            'best': len(browser.find_elements(By.XPATH, bestXpath)),
            'option90': len(browser.find_elements(By.XPATH, option90Xpath)),
            'products': len(browser.find_elements(By.XPATH, productXpath)),
        }

    def WaitForCategoryReady(self, browser, stage):
        def readiness(driver):
            state = self.GetCategoryReadinessState(driver)
            if (
                state['ready'] == 'complete'
                and state['new'] > 0
                and state['best'] > 0
                and state['option90'] > 0
                and state['products'] > 0
            ):
                return state
            return False

        try:
            return WebDriverWait(
                browser,
                CATEGORY_READY_TIMEOUT,
                poll_frequency=0.5,
            ).until(readiness)
        except TimeoutException:
            state = self.GetCategoryReadinessState(browser)
            raise RuntimeError(
                f'Category page readiness timeout ({stage}): {state}'
            ) from None

    def PrepareCategoryBrowser(self, crawlingName, crawlingURL):
        lastError = None

        for attempt in range(1, CATEGORY_READY_ATTEMPTS + 1):
            browser = None

            try:
                browser = webdriver.Chrome(options=self.chrome_option)

                # Readiness polling uses find_elements(), so disable implicit
                # waits here to keep each readiness snapshot bounded.
                browser.implicitly_wait(0)
                browser.get(crawlingURL)

                self.WaitForCategoryReady(browser, 'initial')

                self.ClickElement(browser, '//option[@value="90"]')

                wait = WebDriverWait(browser, 10)
                wait.until(
                    EC.invisibility_of_element(
                        (By.CLASS_NAME, 'product_list_cover')
                    )
                )

                # Danawa can occasionally return only the category shell.
                # Verify usable sort/product UI again after the 90-item refresh.
                self.WaitForCategoryReady(browser, 'after 90')

                browser.implicitly_wait(5)

                if attempt > 1:
                    print(
                        f'Category readiness recovered : {crawlingName} '
                        f'-> attempt {attempt}/{CATEGORY_READY_ATTEMPTS}'
                    )

                return browser

            except Exception as error:
                lastError = error

                state = None
                if browser is not None:
                    try:
                        state = self.GetCategoryReadinessState(browser)
                    except Exception:
                        state = {'snapshot': 'unavailable'}

                print(
                    f'Category readiness failed : {crawlingName} '
                    f'-> attempt {attempt}/{CATEGORY_READY_ATTEMPTS}'
                )
                print(f'Readiness error : {error}')
                print(f'Readiness state : {state}')

                if browser is not None:
                    try:
                        browser.quit()
                    except Exception:
                        print(
                            'Browser cleanup failed during readiness retry '
                            f'- {crawlingName} ->'
                        )
                        print(traceback.format_exc())

                if attempt < CATEGORY_READY_ATTEMPTS:
                    time.sleep(CATEGORY_READY_RETRY_DELAY * attempt)

        raise RuntimeError(
            f'Category page readiness failed after '
            f'{CATEGORY_READY_ATTEMPTS} attempts: {crawlingName}: {lastError}'
        ) from lastError

    def HasVisibleElement(self, browser, xpath):
        for element in browser.find_elements(By.XPATH, xpath):
            if element.is_displayed() and element.is_enabled():
                return True
        return False

    def GetVisibleProductPages(self, browser):
        pageXpath = (
            '//a[contains(concat(" ", normalize-space(@class), " "), " num ")]'
        )
        visiblePages = list()
        for element in browser.find_elements(By.XPATH, pageXpath):
            if not element.is_displayed():
                continue
            pageText = element.text.strip()
            if pageText.isdigit():
                visiblePages.append(int(pageText))
        return sorted(set(visiblePages))

    def GetCurrentProductPage(self, browser):
        currentPageXpath = (
            '//a[contains(concat(" ", normalize-space(@class), " "), " num ") '
            'and contains(concat(" ", normalize-space(@class), " "), " now_on ")]'
        )
        wait = WebDriverWait(browser, 10)
        currentPageElement = wait.until(
            EC.visibility_of_element_located((By.XPATH, currentPageXpath))
        )
        currentPageText = currentPageElement.text.strip()
        if not currentPageText.isdigit():
            raise RuntimeError('Could not determine current product page')
        return int(currentPageText)

    def WaitForCurrentProductPage(self, browser, pageNumber):
        currentPageXpath = (
            '//a[contains(concat(" ", normalize-space(@class), " "), " num ") '
            'and contains(concat(" ", normalize-space(@class), " "), " now_on ") '
            f'and normalize-space(.)="{pageNumber}"]'
        )
        wait = WebDriverWait(browser, 10)
        wait.until(EC.visibility_of_element_located((By.XPATH, currentPageXpath)))

    def ClickProductPage(self, browser, pageNumber):
        currentPage = self.GetCurrentProductPage(browser)
        expectedCurrentPage = pageNumber - 1
        if currentPage != expectedCurrentPage:
            raise RuntimeError(
                f'Unexpected current product page: expected {expectedCurrentPage}, got {currentPage}'
            )

        pageXpath = (
            '//a[contains(concat(" ", normalize-space(@class), " "), " num ") '
            f'and normalize-space(.)="{pageNumber}"]'
        )
        if self.HasVisibleElement(browser, pageXpath):
            self.ClickElement(browser, pageXpath)
            self.WaitForCurrentProductPage(browser, pageNumber)
            return True

        nextBlockXpath = (
            '//a[contains(concat(" ", normalize-space(@class), " "), " edge_nav ") '
            'and contains(concat(" ", normalize-space(@class), " "), " nav_next ")]'
        )

        # Page-number groups are displayed in blocks of ten. At 10 -> 11,
        # 20 -> 21, etc., use the block navigation control when it exists.
        if pageNumber % 10 == 1:
            if self.HasVisibleElement(browser, nextBlockXpath):
                self.ClickElement(browser, nextBlockXpath)
                self.WaitForCurrentProductPage(browser, pageNumber)
                return True

        visiblePages = self.GetVisibleProductPages(browser)
        nextBlockVisible = self.HasVisibleElement(browser, nextBlockXpath)

        # Crawling Page Size is a maximum, but absence alone is not enough to
        # declare success. Only the actual end of the visible paginator is a
        # natural category end. A missing interior page remains a crawl error.
        if (
            currentPage in visiblePages
            and max(visiblePages, default=0) == currentPage
            and not nextBlockVisible
        ):
            return False

        raise RuntimeError(
            f'Expected product page {pageNumber} is unavailable from page {currentPage}; '
            f'visible pages: {visiblePages}; next block visible: {nextBlockVisible}'
        )

    def CrawlingCategory(self, categoryValue):
        crawlingName = categoryValue[STR_NAME]
        crawlingURL = categoryValue[STR_URL]
        crawlingSize = categoryValue[STR_CRAWLING_PAGE_SIZE]

        print('Crawling Start : ' + crawlingName)

        crawlingDataPath = f'{crawlingName}.csv'
        crawlingTempPath = f'{crawlingDataPath}.tmp'
        browser = None
        productCount = 0

        # Only a fully completed category crawl may be consumed by DataSort().
        # Remove leftovers from an interrupted local/re-run before starting.
        for path in (crawlingDataPath, crawlingTempPath):
            if os.path.exists(path):
                os.remove(path)

        try:
            with open(crawlingTempPath, 'w', newline='', encoding='utf8') as crawlingFile:
                crawlingData_csvWriter = csv.writer(crawlingFile)
                crawlingData_csvWriter.writerow([self.GetCurrentDate().strftime('%Y-%m-%d %H:%M:%S')])

                browser = self.PrepareCategoryBrowser(crawlingName, crawlingURL)
                wait = WebDriverWait(browser, 10)

                for i in range(-1, crawlingSize):
                    if i == -1:
                        self.ClickElement(browser, '//li[@data-sort-method="NEW"]')
                    elif i == 0:
                        self.ClickElement(browser, '//li[@data-sort-method="BEST"]')
                    elif i > 0:
                        targetPage = i + 1
                        if not self.ClickProductPage(browser, targetPage):
                            print(f'Crawling Page End : {crawlingName} -> {targetPage - 1} pages')
                            break
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

                                mallName = productPrice.find_element(By.XPATH, './a/div[1]').text.strip()
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
                        productCount += 1

            # A DOM change can yield no recognized products without raising Selenium errors.
            if productCount == 0:
                raise RuntimeError(f'No products crawled: {crawlingName}')

            # Atomic promotion: DataSort() only sees a complete category crawl.
            os.replace(crawlingTempPath, crawlingDataPath)

        except Exception:
            errorMessage = traceback.format_exc()
            print('Error - ' + crawlingName + ' ->')
            print(errorMessage)

            for path in (crawlingTempPath, crawlingDataPath):
                if os.path.exists(path):
                    os.remove(path)

            return crawlingName, errorMessage

        finally:
            if browser is not None:
                try:
                    browser.quit()
                except Exception:
                    print('Browser cleanup failed - ' + crawlingName + ' ->')
                    print(traceback.format_exc())

        print('Crawling Finish : ' + crawlingName)
        return crawlingName, None

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

        successfulCategories = set(self.successfulCategoryNames)

        for crawlingValue in self.crawlingCategory:
            dataName = crawlingValue[STR_NAME]

            if dataName not in successfulCategories:
                print('Data Sort Skip - ' + dataName + ' (crawl failed)')
                continue

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

    if crawler.errorList:
        sys.exit(1)
