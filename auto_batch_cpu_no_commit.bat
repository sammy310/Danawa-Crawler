@echo off

call C:\Users\kippe\anaconda3\Scripts\activate.bat

scrapy crawl cpucrawler -o cpu_data.csv -t csv

python data_sorter.py

