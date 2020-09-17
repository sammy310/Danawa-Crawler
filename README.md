# 다나와 크롤러

각종 PC부품들의 가격의 변동을 알아보기 위해서 제작했습니다

크롤링은 GitHub의 Actions를 사용하여 매일 UTP 0시(한국시간으로 9:00 AM)에 실행되도록 설정하였습니다

Actions의 큐 대기시간이 존재해 보통 9시 2~30분에 완료됩니다


## [크롤링 데이터](https://github.com/sammy310/Danawa_Crawler/tree/master/crawl_data)
- [CPU](https://sammy310.github.io/csv_viewer/CSV_Viewer.html?cpu) / [(데이터 파일)](https://github.com/sammy310/Danawa_Crawler/blob/master/crawl_data/CPU.csv)
- [그래픽카드](https://sammy310.github.io/csv_viewer/CSV_Viewer.html?vga) / [(데이터 파일)](https://github.com/sammy310/Danawa_Crawler/blob/master/crawl_data/VGA.csv)

- [마더보드](https://sammy310.github.io/csv_viewer/CSV_Viewer.html?mboard) / [(데이터 파일)](https://github.com/sammy310/Danawa_Crawler/blob/master/crawl_data/MBoard.csv)
- [램](https://sammy310.github.io/csv_viewer/CSV_Viewer.html?ram) / [(데이터 파일)](https://github.com/sammy310/Danawa_Crawler/blob/master/crawl_data/RAM.csv)

- [SSD](https://sammy310.github.io/csv_viewer/CSV_Viewer.html?ssd) / [(데이터 파일)](https://github.com/sammy310/Danawa_Crawler/blob/master/crawl_data/SSD.csv)
- [HDD](https://sammy310.github.io/csv_viewer/CSV_Viewer.html?hdd) / [(데이터 파일)](https://github.com/sammy310/Danawa_Crawler/blob/master/crawl_data/HDD.csv)

- [쿨러](https://sammy310.github.io/csv_viewer/CSV_Viewer.html?cooler) / [(데이터 파일)](https://github.com/sammy310/Danawa_Crawler/blob/master/crawl_data/Cooler.csv)
- [케이스](https://sammy310.github.io/csv_viewer/CSV_Viewer.html?case) / [(데이터 파일)](https://github.com/sammy310/Danawa_Crawler/blob/master/crawl_data/Case.csv)
- [파워](https://sammy310.github.io/csv_viewer/CSV_Viewer.html?power) / [(데이터 파일)](https://github.com/sammy310/Danawa_Crawler/blob/master/crawl_data/Power.csv)

- [모니터](https://sammy310.github.io/csv_viewer/CSV_Viewer.html?monitor) / [(데이터 파일)](https://github.com/sammy310/Danawa_Crawler/blob/master/crawl_data/Monitor.csv)


---

### 제작에 사용된 것들

- Python : 3.7
- Scrapy : 2.1.0
- selenium : 3.141.0
- Chromedriver : 2.40 (linux 64)
