import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote
import cloudscraper
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
import chardet
import re
from datetime import datetime

def open_page(url, driver):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36', 
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',}
    response = requests.get(url, headers=headers)
    encoding = chardet.detect(response.content)['encoding']
    response.encoding = encoding if encoding else 'utf-8'
    if "www.info83.ru" in url:
        soup=BeautifulSoup(response.text, 'html.parser')
        return soup

    driver.set_page_load_timeout(300) 
    driver.implicitly_wait(20)
    driver.set_script_timeout(60)

    retries=3
    for attempt in range(retries):
        try:
            driver.get(url)
            time.sleep(5)
            WebDriverWait(driver, 180).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            # driver.quit()
            return soup
        except TimeoutException:
            print(f"Таймаут при загрузке {url}, попытка {attempt + 1}")
            time.sleep(10)  # подождать перед повтором
    raise Exception(f"Не удалось загрузить {url} после {retries} попыток")


def parse_info83(driver, company, date_from, date_to, name=""):
    if name=="":
        name=company
    
    company_name = name.replace(" ", "+")

    url = f"https://www.info83.ru/component/search/?searchword={company_name}&ordering=newest&searchphrase=all&areas[0]=content"
    print(url)
    soup=open_page(url, driver)
    articles = []
    print("Найдено новостей:", len(soup.find_all('li')))
    main=soup.find('ol')
    # print(main)
    if not(main is None):
        for item in main.find_all('li'):
            title_elem = item.find('a')
            title = title_elem.text.strip() if title_elem else ''
            link = 'https://www.info83.ru' + title_elem['href'] if title_elem else ''
            print(title)
            for d in item.find_all('p'):
                date=d.get_text(strip=True)
                
                date_formats = ['%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']

                for date_format in date_formats:
                    try:
                        datetime.strptime(date, date_format)
                        break
                    except ValueError:
                        continue
                date_str = date.strip()  # Формат: DD.MM.YYYY
            # print(date)
            
            
            # Фильтр по дате
            try:
                article_date = datetime.strptime(date_str, '%d.%m.%Y')
                if not (datetime.strptime(date_from, '%Y-%m-%d') <= article_date <= datetime.strptime(date_to, '%Y-%m-%d')):
                    continue
            except ValueError:
                pass
            
            # print(title)
            # print(date_str)
            # print(link)

            summary=""
            soup=open_page(link, driver)
            article_text=soup.find_all('div', class_="paragraph-wrapper", attrs={'_ngcontent-dpruapp-c95':""})
            for item in article_text:
                texts = item.find_all('div', class_="paragraph paragraph-text")
                for t in texts:
                    text=t.text.strip()
                    summary=summary+"\n"+text


            articles.append({
                'NewsFinder': "парсер",
                'CompanyName': company,
                'NewsTitle': title,
                'NewsDate': date_str,
                'NewsSource': 'info83.ru',
                'NewsURL': link,
                'NewsText': summary,
                "CompanyVar":name
            })
    print(len(articles))
    return articles

if __name__ == "__main__":
    date_from = "2025-01-01"
    date_to = "2025-12-31"
    industry="Транспорт_2"

    name="газppppp"

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # без окна
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")

    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    news = parse_info83(driver, name, date_from, date_to)
    print(news)
