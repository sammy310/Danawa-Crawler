# -*- coding: utf-8 -*-
"""
@author: sammy310
"""

import csv
import os.path


csvList = {'CPU':'cpu_data.csv', 'VGA':'vga_data.csv', 'MBoard':'mboard_data.csv', 'RAM':'ram_data.csv', 'SSD':'ssd_data.csv', 'HDD':'hdd_data.csv', 'Power':'power_data.csv', 'Cooler':'cooler_data.csv', 'Case':'case_data.csv', 'Monitor':'monitor_data.csv'}
dataPath = 'crawl_data/'
sortData = '20200906-20201031'
dateName = '2020-09'
dataDate = '09'


for key in csvList.keys():
    dataList = list()
    crawl_dataList = list()
    dataName = f'{key}.csv'
    sortName = f'{sortData}/{dataName}'
    
    
    with open(sortName, 'r', newline='', encoding='utf8') as file:
        csvReader = csv.reader(file)
        for row in csvReader:
            crawl_dataList.append(row)
        file.close()
        
    
    
    startIndex = 0
    endIndex = 0
    for j, d in enumerate(crawl_dataList[0]):
        if j > 2:
            if d[5:7] == dataDate:
                if startIndex == 0:
                    startIndex = j
                endIndex = j
            elif startIndex != 0 and endIndex != 0:
                break
    
    for i1, d1 in enumerate(crawl_dataList):
        dataList.append(list())
        for i2, d2 in enumerate(d1):
            if i2 < 2:
                dataList[i1].append(d2)
            elif startIndex <= i2 and i2 <= endIndex:
                dataList[i1].append(d2)
    
    if not os.path.exists(dateName):
        os.mkdir(dateName);
    
    dataFile = f'{dateName}/{dataName}'
    dList = list()
    
    if not os.path.exists(dataFile):
        continue
    
    with open(dataFile, 'r', newline='', encoding='utf8') as file:
        csvReader = csv.reader(file)
        for row in csvReader:
            dList.append(row)
        file.close()
    
    for i1, rd in enumerate(dataList):
        if i1 == 0:
            for rdd in rd[2:]:
                dList[0].append(rdd)
        else:
            isExist = -1
            for i2, d in enumerate(dList):
                if d[0] == rd[0]:
                    isExist = i2
                    break
            if isExist != -1:
                for i3, rdd in enumerate(rd[2:]):
                    dList[isExist].append(rdd)
            else:
                for loop in range(5):
                    rd.insert(2, 0)
                dList.append(rd)
                
                
    productData = dList.pop(0)
    dList.sort(key= lambda x: x[1])
    dList.insert(0, productData)
    
    dataSize = 0
    for i, dd in enumerate(dList):
        if i == 0:
            dataSize = len(dd)
        else:
            if len(dd) != dataSize:
                for ii in range(dataSize-len(dd)):
                    dd.append(0)
        
    
    
    with open(dataFile, 'w', newline='', encoding='utf8') as file:
        csvWriter = csv.writer(file)
        for data in dList:
            csvWriter.writerow(data)
        file.close()
        
            
        
    
    