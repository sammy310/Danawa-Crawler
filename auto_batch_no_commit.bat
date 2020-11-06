@echo off

call C:\Users\kippe\anaconda3\Scripts\activate.bat

scrapy crawl cpucrawler -o cpu_data.csv -t csv

scrapy crawl vgacrawler -o vga_data.csv -t csv

scrapy crawl mboardcrawler -o mboard_data.csv -t csv

scrapy crawl ramcrawler -o ram_data.csv -t csv

scrapy crawl ssdcrawler -o ssd_data.csv -t csv

scrapy crawl hddcrawler -o hdd_data.csv -t csv

scrapy crawl powercrawler -o power_data.csv -t csv

scrapy crawl coolercrawler -o cooler_data.csv -t csv

scrapy crawl casecrawler -o case_data.csv -t csv

scrapy crawl monitorcrawler -o monitor_data.csv -t csv

python data_sorter.py

