@echo off

call C:\anaconda3\Scripts\activate.bat

scrapy crawl cpucrawler -o cpu_data.csv -t csv

python data_sorter.py


git add --all
git commit -m "Auto Update : CPU - %date% %time%"
git push -u origin master
