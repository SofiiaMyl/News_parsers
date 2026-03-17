import requests
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
import trafilatura
import time
from __future__ import annotations
import xml.etree.ElementTree as ET
import pathlib
import time
from typing import List, Dict, Literal, cast
from datetime import datetime
import pandas as pd
from pathlib import Path
import re

from yandex_ai_studio_sdk import AIStudio
from yandex_ai_studio_sdk.search_api import (
    FamilyMode,
    FixTypoMode,
    GroupMode,
    Localization,
    SortMode,
    SortOrder,
)

import json
import requests
from openai import OpenAI
import pandas as pd

YANDEX_CLOUD_MODEL = "yandexgpt"
YANDEX_CLOUD_API_KEY=""
YANDEX_CLOUD_FOLDER=""

key=""
id=""

FOLDER_ID = id
API_KEY = key

USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.6422.112 Mobile Safari/537.36"
)

DATE_FROM = "20250101"
DATE_TO = "20251231"

MAX_SAFE_PAGES = 200  # защита от бесконечного цикла
DELAY_BETWEEN_REQUESTS = 0.5  # задержка для API
MODEL = f"gpt://{YANDEX_CLOUD_FOLDER}/yandexgpt"


async def get_full_crawl4ai(url: str):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=url,
            word_count_threshold=10,
            # Попробуйте разные селекторы для вашего сайта:
            css_selector="article, .news-content, .post, [itemprop='articleBody']"
        )
        
        if result.success:
            # return {
            #     'title': result.metadata.get('title'),
            #     'content': result.markdown,
            #     # 'url': url
            # }
            return result.markdown
        return None
    
def get_full_html(url: str) -> str:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        # максимально агрессивная чистка
        for tag in soup(["script", "style", "head", "meta", "link", "noscript"]):
            tag.decompose()
            
        text = soup.get_text(separator="\n", strip=True)
        lines = [line for line in text.splitlines() if len(line) > 30]
        full_line="\n".join(lines)
        print(full_line +"\n")
        return full_line
    except Exception as e:
        return f"Не удалось загрузить: {type(e).__name__} — {str(e)}"


def get_full_trafilatura(url, title_need=False):
    """Извлекает оригинальный заголовок и полный текст статьи"""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None, None
            
        result = trafilatura.extract(
            downloaded,
            include_formatting=True,   # сохраняет абзацы
            include_links=False,
            include_comments=False,
            include_tables=False,
            no_fallback=True,
            output_format="txt"
        )
        
        # trafilatura часто может вытащить и заголовок отдельно
        metadata = trafilatura.extract_metadata(downloaded)
        original_title = metadata.title if metadata and metadata.title else None
        if title_need:
            return original_title
        else:
            return result
        
    except Exception as e:
        print(f"Ошибка при парсинге {url}: {e}")
        return None, None

def create_search_query(company_name):
    """
    Преобразует название компании в поисковый запрос
    Порядок действий:
    1. Сначала выделяем то, что в скобках
    2. Удаляем скобки из исходной строки
    3. Удаляем запятые и получаем основное название
    """
    
    # Оригинальная строка
    original = company_name.strip()
    
    # ШАГ 1: Находим всё, что в скобках
    brackets_pattern = r'\(([^)]+)\)'
    brackets_content = re.findall(brackets_pattern, original)
    
    # Обрабатываем содержимое скобок
    bracket_terms = []
    for content in brackets_content:
        # Очищаем содержимое скобок
        clean_content = content.strip()
        # Если в скобках несколько вариантов через запятую
        if ',' in clean_content:
            for item in clean_content.split(','):
                item_clean = item.strip()
                if item_clean:
                    # Убираем лишние пробелы внутри
                    item_clean = ' '.join(item_clean.split())
                    bracket_terms.append(item_clean)
        else:
            # Убираем лишние пробелы
            clean_content = ' '.join(clean_content.split())
            bracket_terms.append(clean_content)
    
    # ШАГ 2: Удаляем скобки с содержимым из исходной строки
    without_brackets = re.sub(r'\s*\([^)]*\)', '', original).strip()

    main_name=without_brackets.split(',')[0].strip()
    
    # Формируем поисковый запрос
    search_parts = [f'"{main_name}"']
    
    # Добавляем термины из скобок
    for term in bracket_terms:
        if term and term != main_name:  # Избегаем дублирования
            search_parts.append(f'"{term}"')
    
    # Объединяем через "или"
    if len(search_parts) > 1:
        # Убираем дубликаты, сохраняя порядок
        unique_parts = []
        for part in search_parts:
            if part not in unique_parts:
                unique_parts.append(part)
        return ' | '.join(unique_parts)
    else:
        return search_parts[0]
    
def search(company, name, site):
    sdk = AIStudio(
        folder_id=FOLDER_ID,
        auth=API_KEY,
    )

    sdk.setup_default_logging()

    search = sdk.search_api.web("RU")

    search = search.configure(
        # family_mode=FamilyMode.STRICT,
        fix_typo_mode=FixTypoMode.OFF,
        # group_mode=GroupMode.DEEP,
        group_mode=GroupMode.FLAT,
        localization=Localization.RU,
        sort_mode=SortMode.BY_RELEVANCE,
        sort_order=SortOrder.DESC,
        user_agent=USER_AGENT,
        groups_on_page=100,
    )

    all_results: List[Dict] = []
    for month in range(1, 12, 1):
        new_name=create_search_query(name)
        # Формируем запрос
        if month>=10:
            search_query = (
                f"{new_name} "
                f"site:{site} "
                f"date:2025{month}01..2025{month+1}31"
            )
        else:
            search_query = (
                f"{new_name} "
                f"site:{site} "
                f"date:20250{month}01..20250{month+1}31"
            )

        print("Поисковый запрос:")
        print(search_query)
        print()

        for page in range(MAX_SAFE_PAGES):
            print(f"Запрос страницы {page}...")

            try:
                result_bytes = search.run(search_query, format="xml", page=page)
                result_text = result_bytes.decode("utf-8")
            except Exception as e:
                print("Ошибка запроса:", e)
                break

            root = ET.fromstring(result_text)
            # print(root)
            docs = root.findall(".//doc")
            # print(docs)

            if not docs:
                print("Результаты закончились.")
                break

            print(f"Найдено документов: {len(docs)}")

            timestamp = datetime.now().strftime('%Y-%m-%d')
            # Сохраняем XML страницы
            # xml_filename = f"Страницы/{company}_{site.split('.')[0]}_{month}_2025_page_{page+1}_{timestamp}.xml"
            # with open(xml_filename, "w", encoding="utf-8") as f:
            #     f.write(result_text)

            # Парсим результаты
            for doc in docs:
                url = doc.findtext("url")
                title = doc.findtext("title")
                if len(title)<=10 or "..." in title or title[-1] in ["'", '"', "‘", "“", "«", " "]:
                    title=get_full_trafilatura(url, title_need=True)
                    
                mime = doc.findtext("mime-type")
                date_str=doc.findtext("modtime")
                if date_str:
                    dt = datetime.strptime(date_str, "%Y%m%dT%H%M%S")
                    # Преобразуем в нужный формат
                    formatted_date = dt.strftime("%d.%m.%Y")
                else:
                    formatted_date=""

                if url and mime!="pdf" and mime!="doc" and mime!="docx" and not("pdf" in url.lower()) and not("doc" in url.lower()) and not("xls" in url.lower()) and not("odt" in url.lower()):
                    all_results.append({
                        'NewsFinder': "парсер",
                        "CompanyName": company,
                        "NewsTitle": title,
                        'NewsDate': formatted_date,
                        'NewsSource': site[:-1],
                        "NewsURL": url,
                        "NewsText":"",
                        "CompanyVar": name
                    })

            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Удаляем дубликаты
    unique_results = {item["NewsURL"]: item for item in all_results}.values()
    unique_results = list(unique_results)
    # print(type(unique_results), unique_results)

    print()
    print("Всего уникальных статей:", len(unique_results))

    return unique_results

async def formed_table(company, name, site):
    client = OpenAI(
        api_key=YANDEX_CLOUD_API_KEY,
        base_url="https://ai.api.cloud.yandex.net/v1",
        project=YANDEX_CLOUD_FOLDER
    )
    # ================= STEP 2 — DOWNLOAD ALL ARTICLES =================
    articles=search(company, name, site)
    try:
        ad=articles[0]["NewsSource"]
        pd.DataFrame(articles).to_csv(f"Urls_{company}_{name}_{ad}.csv")
    except: pass
    articles_text = []
    urls=[]

    for i in articles:
        i["NewsText"]=get_full_trafilatura(i["NewsURL"])

    print(articles)
    return articles


df=pd.read_csv("Строительство_Очень_крупные_65_компаний_2026_03_07.csv", delimiter=';')
print(df)
regions=pd.read_csv("Новостные сайты по регионам.csv", delimiter=';')
print(regions)

# основной цикл. Чтение файла с компаниями
full_names=df.iloc[:, 2]
short_names=df.iloc[:, 1]
extra_names=df.iloc[:, 3]
inns=df.iloc[:, 0]
regs=df.iloc[:, 6]


for i in range(len(df)):
# for i in [49, 50, 51, 52, 58, 59, 60, 61]:
    # формирование новостей по официальному названию
    name=full_names[i]
    print("name", name)
    region=regs[i]
    print(region)
    inn=inns[i]
    sites=[]
    all_names=[short_names[i]]+extra_names[i].split(',')

    sites = regions[regions.iloc[:, 0] == region].iloc[0, 1].split(",")
    sites = [''.join(s.split()) for s in sites]
    print(sites)

    for site in sites:
        news_full=formed_table(name, name, site)

        for n in all_names:
            news_short=formed_table(name, n, site)
            print('\n Other names:', news_short)
            if news_short:
                for k in range(len(news_short)):
                    if not news_short[k]["NewsURL"] in [item['NewsURL'] for item in news_full]:
                        news_full.append(news_short[k])

        timestamp = datetime.now().strftime('%Y-%m-%d')
        
        site2=site.split(".")[0]
        csv_filename = f"65 строительных компаний/{name}_{site2}_{timestamp}.csv"
        # csv_filename2 = f"5 строительных компаний с LLM/{name}_{site2}_{timestamp}.csv"
        print(csv_filename)

        df = pd.DataFrame(news_full)
        print(df)
        try:
            df['NewsTitle'] = df['NewsTitle'].str.replace(r'"', "'", regex=True)
            df['NewsTitle'] = '"' + df['NewsTitle'] + '"'

            df['NewsText'] = df['NewsText'].str.replace(r'[\n\r\t]+', ' ', regex=True)
            # df['NewsTitle'] = df['NewsTitle'].str.replace(r'\s+', ' ', regex=True).str.strip()
            df['NewsText'] = df['NewsText'].str.replace(r'"', "'", regex=True)
            df['NewsText'] = '"' + df['NewsText'] + '"'
        except: pass
        
        df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
