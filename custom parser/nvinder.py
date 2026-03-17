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

def parse_nvinder(driver, company, date_from, date_to, name=""):
    if name=="":
        name=company

    # print(type(name), name)
    company_name = name.replace(" ", "%20")
    # url = f"https://www.fontanka.ru/cgi-bin/search.scgi?query={company_name}&fdate={date_from}&tdate={date_to}&sortt=date"
    url=f"https://nvinder.ru/search/node/{company_name}%20type%3Anews%2Carticle"
    print(url)
    soup=open_page(url, driver)
    # headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    # response = requests.get(url, headers=headers)
    # soup = BeautifulSoup(response.text, "html.parser")



    articles = []
    # print(soup)
    # print(soup.find_all('li', class_="search-result"))
    if len(soup.find_all('li', class_='search-result'))!=0:
        for item in soup.find_all('li', class_='search-result'):
            title_elem = item.find('h3', class_='title')
            title_elem = title_elem.find('a')
            title = title_elem.text.strip() if title_elem else ''
            # print(title_elem['href'])
            if 'https://nvinder.ru/' in title_elem['href'] or 'https://' in title_elem['href']:
                link=title_elem['href']
            else:
                link = 'https://nvinder.ru/' + title_elem['href'] if title_elem else ''
            date_time = item.find('p', class_='search-info').get_text(strip=True)
            dt = datetime.strptime(date_time, "%m/%d/%Y - %H:%M")
            date_str = dt.strftime("%d.%m.%Y")
            # print(date_str)
            # print(date_time)
            # date_str = date_time.text.strip()  # Формат: DD.MM.YYYY
            # summary = item.find('p', class_='snippet').text.strip() if item.find('p', class_='snippet') else ''
            
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

            # response = requests.get(link, headers=headers)
            # soup = BeautifulSoup(response.text, "html.parser")
            # print(soup)

            soup=open_page(link, driver)
            article_text=soup.find_all('div', class_="field-items")
            # print("Article", article_text)
            for item in article_text:
                texts = item.find_all('p')
                for t in texts:
                    text=t.text.strip()
                    summary=summary+"\n"+text

            # print(summary)

            articles.append({
                'NewsFinder': "парсер",
                'CompanyName': company,
                'NewsTitle': title,
                'NewsDate': date_str,
                'NewsSource': 'nvinder.ru',
                'NewsURL': link,
                'NewsText': summary,
                "CompanyVar":name
            })


    j=1
    while True:
        try:
            url = f"https://nvinder.ru/search/node/{company_name}%20type%3Anews%2Carticle?page={j}"
            # print(url)
            soup=open_page(url, driver)

            url_last = f"https://nvinder.ru/search/node/{company_name}%20type%3Anews%2Carticle?page={j-1}"
            soup_last=open_page(url_last, driver)
            item_last=soup_last.find_all('li', class_='search-result')

            if soup.find_all('li', class_='search-result')==item_last: break
            if not(soup.find_all('li', class_='search-result')): break

            for item in soup.find_all('li', class_='search-result'):
                # print(item)
                title_elem = item.find('h3', class_='title')
                title_elem = title_elem.find('a')
                title = title_elem.text.strip() if title_elem else ''
                if 'https://nvinder.ru/' in title_elem['href'] or 'https://' in title_elem['href']:
                    link=title_elem['href']
                else:
                    link = 'https://nvinder.ru/' + title_elem['href'] if title_elem else ''
                date_time = item.find('p', class_='search-info').get_text(strip=True)
                dt = datetime.strptime(date_time, "%m/%d/%Y - %H:%M")
                date_str = dt.strftime("%d.%m.%Y")
                # print(date_str)

                    
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
                article_text=soup.find_all('div', class_="field-items")
                # print("Article", article_text)
                for item in article_text:
                    texts = item.find_all('p')
                    for t in texts:
                        text=t.text.strip()
                        summary=summary+"\n"+text

                # print(summary)

                articles.append({
                    'NewsFinder': "парсер",
                    'CompanyName': company,
                    'NewsTitle': title,
                    'NewsDate': date_str,
                    'NewsSource': 'nvinder.ru',
                    'NewsURL': link,
                    'NewsText': summary,
                    "CompanyVar":name
                })
            j+=1
        except: 
            print("break")
            break
            

    print(len(articles))
    return articles

if __name__ == "__main__":

    date_from = "2025-01-01"
    date_to = "2025-12-31"
    industry="Транспорт_2"
    # name="Транспорт - Все компании - 2026.01.04"

    # file_names=pd.read_csv(name+".csv", delimiter=";")
    # print(file_names)

    name="газпром"

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

    news = parse_nvinder(driver, name, date_from, date_to)
