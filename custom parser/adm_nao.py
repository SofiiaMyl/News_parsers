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

def parse_adm_nao(driver, company, date_from="2025-01-01", date_to="2025-12-31", name=""):
    if name == "":
        name = company

    company_name = name.replace(" ", "%20")

    base_url = (
        f"https://adm-nao.ru/search/?searchid=2246212&text={company_name}"
        f"&web=0#lr=2&constraintid=31&within=777"
        f"&from_day=1&from_month=1&from_year=2025"
        f"&to_day=31&to_month=12&to_year=2025"
    )

    articles = []
    page = 0
    previous_links = set()

    while True:
        page_url = base_url + (f"&p={page}" if page > 0 else "")
        print("Открываем:", page_url)

        driver.get(page_url)
        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        main = soup.find("yass-ol", class_="b-serp-list")

        if main is None:
            print("Список новостей не найден. Завершаем.")
            break

        items = main.find_all("yass-li", class_="b-serp-item")

        if not items:
            print("Новости закончились.")
            break

        # ---- собираем ссылки текущей страницы ----
        current_links = set()
        for item in items:
            title_elem = item.find('yass-h3')
            if title_elem and title_elem.find('a'):
                current_links.add(title_elem.find('a')['href'])

        print(f"Страница {page+1}, найдено ссылок:", len(current_links))

        # ---- проверка на повтор страницы ----
        if current_links == previous_links:
            print("Обнаружено повторение страницы. Останавливаем пагинацию.")
            break

        previous_links = current_links.copy()

        # ---- парсинг статей ----
        for item in items:
            try:
                title_elem = item.find('yass-h3')
                title = title_elem.find('yass-span').text.strip() if title_elem else ''
                link = title_elem.find('a')['href']

                ll = item.find('yass-div', class_="b-serp-item__content")
                date = ll.find_all('yass-span', class_="b-serp-url__item")[-1].text
                date_str = date.strip()

                # Фильтр по дате
                try:
                    article_date = datetime.strptime(date_str, '%d.%m.%Y')
                    if not (datetime.strptime(date_from, '%Y-%m-%d') <= article_date <= datetime.strptime(date_to, '%Y-%m-%d')):
                        continue
                except ValueError:
                    pass

                # Открываем статью
                driver.get(link)
                time.sleep(3)
                article_soup = BeautifulSoup(driver.page_source, 'html.parser')

                summary = ""
                article_text = article_soup.find_all('article')

                for art in article_text:
                    for p in art.find_all('p'):
                        summary += "\n" + p.get_text(strip=True)

                articles.append({
                    'NewsFinder': "парсер",
                    'CompanyName': company,
                    'NewsTitle': title,
                    'NewsDate': date_str,
                    'NewsSource': 'adm-nao.ru',
                    'NewsURL': link,
                    'NewsText': summary,
                    "CompanyVar": name
                })

            except Exception as e:
                print("Ошибка:", e)
                continue

        page += 1

    print("Всего собрано:", len(articles))
    return articles


if __name__ == "__main__":
    industry="Транспорт_2"

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

    news = parse_adm_nao(driver, name)
    print(news)