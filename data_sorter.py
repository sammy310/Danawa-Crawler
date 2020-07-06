# -*- coding: utf-8 -*-
"""
Created on Sun Jul  5 09:49:21 2020

@author: sammy310
"""

import csv
import os.path


csvList = {'CPU':'cpu_data.csv', 'VGA':'vga_data.csv', 'MBoard':'mboard_data.csv', 'RAM':'ram_data.csv', 'SSD':'ssd_data.csv', 'HDD':'hdd_data.csv', 'Power':'power_data.csv', 'Cooler':'cooler_data.csv', 'Case':'case_data.csv'}
dataPath = 'crawl_data/'

for key in csvList.keys():
    dataList = list()
    crawl_dataList = list()
    
    
    if not os.path.exists(csvList[key]):
        continue
    
    with open(csvList[key], 'r', newline='', encoding='utf8') as file:
        csvReader = csv.reader(file)
        for row in csvReader:
            crawl_dataList.append(row)
        file.close()
    
    dataFile = dataPath + key + '.csv'
    if not os.path.exists(dataFile):
        file = open(dataFile, 'w', encoding='utf8')
        file.close()
    with open(dataFile, 'r', newline='', encoding='utf8') as file:
        csvReader = csv.reader(file)
        for row in csvReader:
            dataList.append(row)
        file.close()
    
    
    if len(dataList) == 0:
        dataList.append(['Id', 'Name'])
        
    dataList[0].append(crawl_dataList[0][0])
    
    for product in crawl_dataList:
        if not str(product[0]).isdigit():
            continue
        
        isDataExist = False
        for data in dataList:
            if data[0] == product[0]:
                data.append(product[2])
                isDataExist = True
        
        if not isDataExist:
            newDataList = ([product[0], product[1]])
            for i in range(2,len(dataList[0])-1):
                newDataList.append(0)
            newDataList.append(product[2])
        
            dataList.append(newDataList)
        
    dataSize = len(dataList[0])
    for data in dataList:
        if len(data) < dataSize:
            for i in range(len(data),dataSize):
                data.append(0)
        
    
    productData = dataList.pop(0)
    dataList.sort(key= lambda x: x[1])
    dataList.insert(0, productData)
        
    with open(dataFile, 'w', newline='', encoding='utf8') as file:
        csvWriter = csv.writer(file)
        for data in dataList:
            csvWriter.writerow(data)
        file.close()
        
    if os.path.isfile(csvList[key]):
        os.remove(csvList[key])
        
    