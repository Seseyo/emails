import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Адрес прокси сервера
proxy = "213.241.205.2:8080"

urls_base = pd.read_excel('urls_base.xlsx')

# Загружаем список ссылок из файла
with open('url.init', 'r') as file:
    url_search = file.readlines()


service = Service(executable_path='/usr/lib/chromium-browser/chromedriver')
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
#chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument(f"--proxy-server={proxy}")
chrome_options.add_argument("--window-size=1400,3000")

url_base = 'https://clearspending.ru'
url_show = '#contracts'
url_gov = 'https://zakupki.gov.ru'

# Функция, которая забирает емаил со страницы заказчика
def email_parse(soup, tab='com'):
    soup = BeautifulSoup(driver.page_source, 'lxml')
    cards = soup.find("div", class_ = "cardWrapper outerWrapper")
    if tab == 'add':
        cards = cards.find("div", class_ = "tabs-container")
        cards = cards.find("div", {"id": "tab-other"})
    cards = cards.find_all("div", class_ = "container")
    cards = cards[-1].find_all("span")

    email = 'NOT FOUND'
    for id,card in enumerate(cards):
        if 'электронной' in card.text:
            email = cards[id + 1].text
    print('FIND EMAIL:', email)
    return email

# Функция поиска емаила заказчика
def find_customer_email(driver, url_customer):
    wait = WebDriverWait(driver, 5)
    try:
        driver.get(url_customer)
        print('SEARCH CUSTOMER... ID :', url_customer[-9:-1])
        customer = driver.find_element(By.XPATH, "//span[contains(text(),'Полное наименование заказчика')]/following::span[1]/a")
        ActionChains(driver).click(customer).perform()
        driver.implicitly_wait(1)
        driver.switch_to.window(driver.window_handles[1])
        try:
            print('SEARCH ADD_INFO...')
            add_info = driver.find_element(By.XPATH, "//a[contains(text(),'ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ')]")
            ActionChains(driver).click(add_info).perform()
            try:
                print('SEARCH EMAIL ON ADD_INFO TAB')
                xpath_email = "//span[contains(text(),'Контактный адрес электронной почты')]/following::span[1]"
                email = driver.find_element(By.XPATH, xpath_email)
                soup = BeautifulSoup(driver.page_source, 'lxml')
                return email_parse(soup, 'add')
            except Exception as ex:
                print(f'Error: {ex}', "// ER // Email not found on add_info tab")

        except Exception as ex:
            print(f'Error: {ex}', '// ER // Add_info tab not found')
            try:
                print('SEARCH EMAIL ON COMMON TAB')
                email = driver.find_element(By.XPATH, "//span[contains(text(),'Контактный адрес электронной почты')]/following::span[1]")
                soup = BeautifulSoup(driver.page_source, 'lxml')
                return email_parse(soup)
            except Exception as ex:
                print(f'Error: {ex}', "// ER // Email not found on common tab")

    except Exception as ex:
        print(f'Error: {ex}', '// ER // Full_name of customer not found')
    return 'NOT FOUND'


# ================================ Сбор ссылок ================================

# Функция подсчета количества страниц в запросе
def pages_count(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        count = soup.find("div", {"id": "content"}).find("div", class_ = "wrap clearfix")
        count = count.find("div", class_ = "col-12").find("p").text

        print(count) # Вывод строки 'Найдено организаций: 13 (максимум 500)'

        word_list = count.split()
        num_list = []
        for word in word_list:
            if word.isnumeric():
                num_list.append(int(word))
        number = int(num_list[0] // 25) + 1
        print('Количество страниц:', number)
        return number
    except Exception as ex:
        print(f'Error: {ex}', 'Not response : ', url)
        return 0

# Фунция, которая забирает ссылку на одну компанию с одной страницы
def get_company_urls_from_page(search_url, page):
    try:
        url_pagination = search_url + '&page=' + str(page)
        print('Обработана страница: ', str(page))
        response = requests.get(url_pagination)

        soup = BeautifulSoup(response.text, 'lxml')

        table = soup.find("table", {"id": "table"})
        tbody = table.find("tbody").find_all("tr")

        page_urls = []
        for tr in tbody:
            tds = tr.find_all("td")
            orders = re.sub('\D', '', tds[3].text)
            url_current = tds[0].find("a")
            if (orders != '') and (url_current is not None):
                page_urls.append(url_current['href'])
        return page_urls
    except Exception as ex:
        print(f'Error: {ex}', ' 2 / Не удалось перейти : ', url_pagination)
    return None

# Функция, которая собирает ссылки на все компании из одного поискового запроса
def search_url_parse(url):
    print('\n',url)
    try:
        number = pages_count(url)

        company_urls = []
        for page in range(1,number + 1):
            current_page_urls = get_company_urls_from_page(url, page)
            print('Отладка: ', current_page_urls)
            if current_page_urls is not None:
                company_urls.extend(current_page_urls)
        # добавляем к списку поисков адреса соттветствующих ему компаний
        print('Отладка: ', company_urls)
        return company_urls
    except Exception as ex:
        print(f'Error: {ex}', '1 / Не удалось перейти : ', url)
        with open('url.error', 'a') as file:
            file.write('\n' + url)
        return None

# Функция получения ссылки на заказчика по ссылке на компанию
def get_url_customer(url_total):
    # Переход на карточку организации
    try:
        response = requests.get(url_total)
        soup = BeautifulSoup(response.text, 'lxml')
    except Exception as ex:
        print(f'Error: {ex}', ' response переход на карточку организации')
    try:
        table = soup.find("div", class_ = "tab-pane active clearfix").find("table", class_ = "table")
        url_contract = table.find("a")['href']
        url_total = url_base + url_contract
    except Exception as ex:
        print(f'Error: {ex}', ' soup переход на карточку организации')

    # Переход на карточку контракта
    try:
        response = requests.get(url_total)
        soup = BeautifulSoup(response.text, 'lxml')
    except Exception as ex:
        print(f'Error: {ex}', '// ER // r.get to contract card')

    try:
        table = soup.find("div", class_ = "col-6 col-m-12 left").find("table", class_ = "table")
        url_customer = table.find("a")['href']
        return url_customer
        #print(url_customer)
    except Exception as ex:
        print(f'Error: {ex}', ' soup переход на карточку контракта')
    return None

# =============================== Основная программа =========================
result = []
for search_id,url_s in enumerate(url_search):
    # Сбор ссылок на компании на открывшейся странице
    try:

        companies = search_url_parse(url_s)

        emails = []
        for index, url_company in enumerate(companies):

            print('number: ', str(index), '::', url_company)
            url_total = url_base + url_company + url_show
            url_customer = get_url_customer(url_total)

            # Переход на сайт с информацией о заказчике
            print('selenium')
            try:
                driver = webdriver.Chrome(service=service, options=chrome_options)
                email = find_customer_email(driver, url_customer)
                if email != 'NOT FOUND':
                    emails.append(email)
                driver.close()
            except Exception as ex:
                print(f'Error: {ex}', ' go to customer_info page')

        result.append(emails)
        print(emails)
        url_id = search_id + 1
        search_name = 'Url_' + str(url_id)
        df_emails = pd.DataFrame({search_name: emails})
        df_emails.to_excel(search_name + '.xlsx')
        print('Загружены адреса поискового запроса: ', url_id)

    except Exception as ex:
        print(f'Error: {ex}', ' Не удалось перейти по ссылке: ', url_s)
        with open('url.error', 'a') as file:
            file.write('\n' + url_s)


#===================== Запись в общий файл =============================

max_len = 0
for r in result:
    r_len = len(r)
    if r_len > max_len:
        max_len = r_len

for r in result:
    for i in range(len(r),max_len):
        r.append(None)

df_emails = pd.DataFrame()
for i,r in enumerate(result):
    col = str(i)
    df_emails[i] = r
df_emails.to_excel('emails.xlsx')
