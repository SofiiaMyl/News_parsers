import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote
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
import os
import shutil

import info83
# import rgru
import adm_nao
import nvinder

def process_folder(folder_path, column_name):
    # исправление кодировки
    for file in os.listdir(folder_path):
        if not file.lower().endswith('.csv'):
            continue
        csv_path = os.path.join(folder_path, file)
        print(f"\n📂 Проверяю файл: {file}")
        try:
            df=pd.read_csv(csv_path)
            # df.dropna(how='all', inplace=True)
            for i in range(len(df)):
                try:
                    df.iloc[i, 5]=df.iloc[i, 5].encode("mac_roman").decode("utf-8", errors="replace")
                except: pass
            
            print(df)
            df.to_csv(csv_path)
        except: pass

def folder_formation(folder_name, file_names):
    # Путь к папке, куда хотите перенести файлы (можете указать полный или относительный путь)
    destination_folder = os.path.join(os.getcwd(), folder_name)

    # Создаем папку, если ее еще нет
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
        print(f"Папка '{folder_name}' создана.")
    else:
        print(f"Папка '{folder_name}' уже существует.")

    # Путь к папке с файлами, которые нужно перенести
    source_folder = os.getcwd()
    print(source_folder)
    # print(names)

    names=file_names.iloc[:, 0:1]
    # Переносим файлы из source_folder в новую папку
    for i in range(len(names)):
        filename=names.iloc[i, 0]+"_news.csv"
        print(filename)
        source_path = os.path.join(source_folder, filename)
        destination_path = os.path.join(destination_folder, filename)
        if os.path.isfile(source_path):
            shutil.move(source_path, destination_path)
            print(f"Файл {filename} перемещен.")

date_from = "2025-01-01"
date_to = "2025-12-31"
File_name="Companies - Коммунальные услуги - 78_47_83"
industry="Коммунальные услуги"

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

# names=pd.read_csv("Парсинг новостей/Ненецкий автономный округ/Companies - СЗФО.csv", header=0)


file_names=pd.read_csv("Парсинг новостей/"+File_name+".csv")
print("full file\n", file_names)
names = file_names[lambda df: df.iloc[:, 3]==83]

print("region 83\n", names)

for i in range(len(names)):
    # формирование новостей по официальному названию
    name=names.iloc[i, 0]
    print("name", name)
    extra_name=names.iloc[i, -1].split(",")
    print("extra names", extra_name)
    inn=names.iloc[i, 1]
    print('inn', inn)

    news_info83=info83.parse_info83(driver, name, date_from, date_to)
    print("\n", news_info83, "\n")

    news_adm_nao=adm_nao.parse_adm_nao(driver, name, date_from, date_to)
    print(news_adm_nao, "\n")

    news_nvinder=nvinder.parse_nvinder(driver, name, date_from, date_to)
    print(news_nvinder, "\n")

    # names_extra=[names.iloc[i, 2].split(',')]
    # формирование новостей по дополнительным вариантам написания названия
    for n in extra_name:
        try:
            news_info83_extra=info83.parse_info83(driver, n, date_from, date_to)
            print(news_info83_extra)
            # сбор всех уникальных новостей новостей в один массив
            for article in news_info83_extra:
                if article not in news_info83:
                    news_info83.append(article)
        except: pass
        try:
            news_adm_nao_extra=adm_nao.parse_adm_nao(driver, n, date_from, date_to)
            print(news_info83_extra)
            for article in news_adm_nao_extra:
                if article not in news_adm_nao:
                    news_adm_nao.append(article)
        except: pass
        try:
            news_nvinder_extra=nvinder.parse_nvinder(driver, n, date_from, date_to)
            print(news_info83_extra)
            for article in news_nvinder_extra:
                if article not in news_nvinder:
                    news_nvinder.append(article)
        except: pass

    timestamp = datetime.now().strftime('%Y-%m-%d')
    
    # Сохранение во временный файл
    news_info83_f=pd.DataFrame(news_info83)
    news_info83_f.to_csv(f"{name}_{inn}_info83_{timestamp}.csv", index=False, encoding="utf-8-sig")

    news_adm_nao_f=pd.DataFrame(news_adm_nao)
    news_adm_nao_f.to_csv(f"{name}_{inn}_adm_nao_{timestamp}.csv", index=False, encoding="utf-8-sig")

    news_nvinder_f=pd.DataFrame(news_nvinder)
    news_nvinder_f.to_csv(f"{name}_{inn}_nvinder_{timestamp}.csv", index=False, encoding="utf-8-sig")

    all_news=pd.DataFrame(news_info83+news_adm_nao+news_nvinder)
    all_news.to_csv(f"{name}_news.csv", index=False, encoding="utf-8-sig")

driver.quit()

# создание папки по отрасли
folder_formation(industry, names)

# проверка и исправление кодировки
process_folder(industry, column_name = "text")