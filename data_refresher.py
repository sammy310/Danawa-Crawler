# -*- coding: utf-8 -*-
"""
@author: sammy310
"""

import os
import shutil
import datetime

DATA_PATH = 'crawl_data/'
DATA_SAVE_PATH = 'crawl_data/Last_Data/'
DATA_FILE = 'ComputerCrawlerFile.csv'
CSVLIST = ['CPU.csv', 'VGA.csv', 'MBoard.csv', 'RAM.csv', 'SSD.csv', 'HDD.csv', 'Power.csv', 'Cooler.csv', 'Case.csv', 'Monitor.csv']


dTime = datetime.datetime.today() + datetime.timedelta(hours=9)
if dTime.day == 1:
    if not os.path.exists(DATA_PATH):
        os.mkdir(DATA_PATH)
    
    dTime -= datetime.timedelta(days=1)
    dateStr = dTime.strftime('%Y-%m')
    if os.path.exists(DATA_PATH + CSVLIST[0]):
        
        
        dataFormat = 'Crawl_Data_' + dateStr + '.csv'
        shutil.move(DATA_FILE, DATA_SAVE_PATH + dataFormat)
        
        dataSavePath = DATA_SAVE_PATH + dateStr
        if not os.path.exists(dataSavePath):
            os.mkdir(dataSavePath)
        
        for fName in CSVLIST:
            shutil.move(DATA_PATH + fName, dataSavePath + '/' + fName)
    
    