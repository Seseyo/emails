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


user_path = ''

urls_file_name = 'urls_base.xlsx'
urls_base = pd.read_excel(urls_file_name)

user_search_urls = urls_base['url'].tolist()
user_search_names = urls_base['name'].tolist()

print(user_search_urls)
print(user_search_names)

url_search = user_search_urls


service = Service(executable_path='/usr/lib/chromium-browser/chromedriver')
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")

url_base = 'https://clearspending.ru'
url_show = '#contracts'
url_gov = 'https://zakupki.gov.ru'


result = []
#searchs = []
for url_id,url_s in enumerate(url_search):

# ================================ Сбор ссылок на компании =====================

    response = requests.get(url_s)
    soup = BeautifulSoup(response.text, 'lxml')

    # Вычисление количества страниц
    count = soup.find("div", {"id": "content"}).find("div", class_ = "wrap clearfix")
    count = count.find("div", class_ = "col-12").find("p").text
    print(count)
    word_list = count.split()
    num_list = []
    for word in word_list:
        if word.isnumeric():
            num_list.append(int(word))
    print(num_list)

    number = int(num_list[0] // 25) + 1
    print('количество страниц:', number)

    company_urls = []
    for page in range(1,number + 1):
        try:
            url_pagination = url_s + '&page=' + str(page)
            print('page: ', str(page))
            response = requests.get(url_pagination)

            soup = BeautifulSoup(response.text, 'lxml')

            table = soup.find("table", {"id": "table"})
            tbody = table.find("tbody").find_all("tr")

            for tr in tbody:
                tds = tr.find_all("td")
                orders = re.sub('\D', '', tds[3].text)
                url_current = tds[0].find("a")
                if (orders != '') and (url_current is not None):
                    company_urls.append(url_current['href'])
        except Exception as ex:
            print(f'Error: {ex}', ' response переход на карточку организации')
    # добавляем к списку поисков адреса соттветствующих ему компаний
    #searchs.append(company_urls)

# =================== Обработка ссылок и сбор емаилов ======================

    with open('temp.txt', 'a') as f:
         f.write(user_search_names[url_id] + '\n')

    companies = company_urls
    emails = []
# Проходим по всем компаниям поискового запроса
    for index, company in enumerate(companies):
        # Ссылка на текущую компанию
        url_company = company
        print('number: ', str(index), '::', company)
        url_total = url_base + url_company + url_show

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
            print(f'Error: {ex}', ' response переход на карточку контракта')

        try:
            table = soup.find("div", class_ = "col-6 col-m-12 left").find("table", class_ = "table")
            url_customer = table.find("a")['href']
            print(url_customer)
        except Exception as ex:
            print(f'Error: {ex}', ' soup переход на карточку контракта')

        print('selenium')


        # Переход на сайт с информацией о заказчике
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 5)
        try:
            driver.get(url_customer)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "footer.footer")))
        except Exception as ex:
            print(f'Error: {ex}')

        try:
            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            url_info = soup.find("div", {"id": "ajax-group"}).find("span", class_ = "section__info").find("a")['href']
            url_zakupki_info = url_gov + url_info
            print('url_info: ', url_zakupki_info)

                # Переход по ссылке на карточку подробной информацией о заказчике

            try:
                driver.get(url_zakupki_info)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.cardHeaderBlock")))
            except Exception as ex:
                print(f'Error: {ex}')

            try:
                html = driver.page_source
                soup = BeautifulSoup(html, 'lxml')
                url_add = soup.find("div", class_ = "page-svr").find("a")['href']
                url_add_total = url_gov + url_add
                print(url_add)

                # Переход на вкладку дополнительная информация

                try:
                    driver.get(url_add_total)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h2.blockInfo__title")))
                except Exception as ex:
                    print(f'Error: {ex}')

                try:
                    html = driver.page_source
                    soup = BeautifulSoup(html, 'lxml')
                    cards = soup.find("div", class_ = "cardWrapper outerWrapper").find("div", class_ = "tabs-container")
                    cards = cards.find("div", {"id": "tab-other"}).find_all("div", class_ = "container")
                    card = cards[-1].find_all("span")
                    email_new = card[7].text
                    if email_new.find('@') >= 0:
                        emails.append(email_new)
                        with open('temp.txt', 'a') as f:
                            f.write(email_new + '\n')
                        print('EMAIL: ', email_new)
                except Exception as ex:
                    print(f'Error: {ex}', '; soup на вкладку с дополнительной информацией')

            except Exception as ex:
                print(f'Error: {ex}', '; soup на карточку с подробной информацией')

        except Exception as ex:
            print(f'Error: {ex}', '; soup на сайт с информацией о заказчике')
        driver.quit()
    result.append(emails)
    print(emails)

    search_name = user_search_names[url_id]
    df_emails = pd.DataFrame({search_name: emails})
    df_emails.to_excel(user_path + search_name + '.xlsx')
    print('Загружены адреса поискового запроса: ', search_name)


# Финальная обработка и запись в файл

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
