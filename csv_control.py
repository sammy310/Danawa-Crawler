from datetime import datetime
from datetime import timedelta
# from pytz import timezone
import csv
import os
import os.path
import shutil
import traceback


CRAWLING_DATA_CSV_FILE = 'CrawlingCategory.csv'
DATA_PATH = 'crawl_data'
DATA_REFRESH_PATH = f'{DATA_PATH}/Last_Data'


DATA_DIVIDER = '---'
DATA_REMARK = '//'
DATA_ROW_DIVIDER = '_'
DATA_PRODUCT_DIVIDER = '|'

STR_NAME = 'name'
STR_URL = 'url'
STR_CRAWLING_PAGE_SIZE = 'crawlingPageSize'


crawlingCategory = list()
with open(CRAWLING_DATA_CSV_FILE, 'r', newline='') as file:
    for crawlingValues in csv.reader(file, skipinitialspace=True):
        if not crawlingValues[0].startswith(DATA_REMARK):
            crawlingCategory.append({STR_NAME: crawlingValues[0], STR_URL: crawlingValues[1], STR_CRAWLING_PAGE_SIZE: int(crawlingValues[2])})


# 가장 뒤의 데이터에서
# n위(1위, 2위 ...) 로 시작하는 경우 제거
def LastColumnRankTextDelete():
    print('LastColumnRankTextDelete\n')

    # for crawlingValue in [1]:
        # dataName = 'CPU'
    for crawlingValue in crawlingCategory:
        dataName = crawlingValue[STR_NAME]

        dataPath = f'{DATA_PATH}/{dataName}.csv'

        if not os.path.exists(dataPath):
            continue
        
        dataList = list()

        with open(dataPath, 'r', newline='', encoding='utf8') as file:
            csvReader = csv.reader(file)
            for row in csvReader:
                dataList.append(row)
        
        
        if len(dataList) == 0:
            continue

        # dataSize = len(dataList[0])
        
        for i in range(len(dataList)):
        # for i in range(30):
            row = dataList[i]

            newData = ''
            lastData = row[-1]

            for product in lastData.split(DATA_PRODUCT_DIVIDER):
                newStr = product
                if len(product) > 2:
                    char1 = product[0]
                    char2 = product[1]

                    if char1.isdigit() and (1 <= int(char1) and int(char1) <= 9):
                        if char2 == '위':
                            newStr = newStr[2:].strip()
                
                newData += newStr + DATA_PRODUCT_DIVIDER
            
            if newData[-1] == DATA_PRODUCT_DIVIDER:
                newData = newData[:-1]
            
            # print(f'lastData: {lastData} -> newData: {newData}\n')

            if newData != lastData:
                dataList[i][-1] = newData

        with open(dataPath, 'w', newline='', encoding='utf8') as file:
            csvWriter = csv.writer(file)
            for data in dataList:
                csvWriter.writerow(data)
            file.close()

# 가장 마지막 열 데이터 제거
def LastColumnDelete():
    print('LastColumnDelete\n')

    # for crawlingValue in [1]:
        # dataName = 'CPU'
    for crawlingValue in crawlingCategory:
        dataName = crawlingValue[STR_NAME]

        dataPath = f'{DATA_PATH}/{dataName}.csv'

        if not os.path.exists(dataPath):
            continue
        
        dataList = list()

        with open(dataPath, 'r', newline='', encoding='utf8') as file:
            csvReader = csv.reader(file)
            for row in csvReader:
                dataList.append(row)
        
        
        if len(dataList) == 0:
            continue

        # dataSize = len(dataList[0])
        
        for i in range(len(dataList)):
            dataList[i] = dataList[i][:-1]

        with open(dataPath, 'w', newline='', encoding='utf8') as file:
            csvWriter = csv.writer(file)
            for data in dataList:
                csvWriter.writerow(data)
            file.close()

if __name__ == '__main__':
    # LastColumnRankTextDelete()
    # LastColumnDelete()
    pass
