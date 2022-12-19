import requests
from requests.auth import HTTPProxyAuth
from bs4 import BeautifulSoup
import pandas as pd
import random
import re
import time
import datetime
import csv
from multiprocessing import Pool
import logging

# получение пользовательского логгера и установка уровня логирования
py_logger = logging.getLogger(__name__)
py_logger.setLevel(logging.INFO)
# настройка обработчика и форматировщика в соответствии с нашими нуждами
py_handler = logging.FileHandler(f"{__name__}.log", mode='w')
py_formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")
# добавление форматировщика к обработчику
py_handler.setFormatter(py_formatter)
# добавление обработчика к логгеру
py_logger.addHandler(py_handler)
py_logger.info(f"Testing the custom logger for module {__name__}...")

# Вывод логов в консоль и файл
def print_log(text):
    print(text)
    py_logger.info(text)

from selenium import webdriver
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Загружаем ссылки и названия запросов из файла
urls_file_name = 'urls_base.xlsx'
emails_file_name = 'all_emails.xlsx'
count_company_file = 'count_company.csv'
count_proxy_file = 'count_proxy.csv'

df_urls_base = pd.read_excel(urls_file_name, index_col=0)
user_search_urls = df_urls_base['url'].tolist()


current_file_name = 'emails.csv'
all_emails = []
try:
    df_emails = pd.read_excel(emails_file_name, index_col=0)
    all_emails = df_emails['email'].tolist()
except Exception as ex:
    print(f"Error: {ex}")
    py_logger.info(f"Error: {ex}")

company_count = 0
proxies = []
proxy_count = 0

url_base = 'https://clearspending.ru'
url_show = '#contracts'
url_gov = 'https://zakupki.gov.ru'



def load_proxies(file_name):
    proxies = []
    with open(file_name, 'r') as f:
        proxies = [proxy.rstrip() for proxy in f.readlines()]
    with open(count_proxy_file,'w') as f:
        f.write(str(len(proxies)-1))
    return proxies


def get_proxy():
    global proxies
    global proxy_count
    try:
        with open(count_proxy_file,'r') as f:
            txt = f.read().rstrip()
            N = int(txt)
        current_proxy = N
        if current_proxy < proxy_count:
            N += 1
        else:
            N = 0
        with open(count_proxy_file,'w') as f:
            f.write(str(N))
        return proxies[current_proxy]
    except Exception as ex:
        print_log(f'Error: {ex} in get_proxy')
    return proxies[random.randint(0,proxy_count)]


def company_increment():
    global company_count
    try:
        with open(count_company_file,'r') as f:
            txt = f.read().rstrip()
            if txt != '':
                N = int(txt)
                company_count = N
            else:
                N = company_count
        N+=1
        print_log(f'Обрабатываю карточку компании номер: {N}')
        with open('count_company','w') as f:
            f.write(str(N))
    except Exception as ex:
        print_log(f'Error: {ex} in company_increment')

# Инициализация драйвера селениум хром
def new_driver(proxy):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    #chrome_options.add_argument("--no-sandbox")
    #chrome_options.add_argument(f"--proxy-server={get_proxy()}")
    chrome_options.add_argument("--window-size=1400,2000")
    options = {
        'proxy': {
            'https': f'https://{proxy}',
        }
    }
    print_log(f'Create driver with proxy: {proxy}')
    return webdriver.Chrome(ChromeDriverManager().install(), options = chrome_options
                            ,seleniumwire_options = options)


def init_session(proxy):
    session = requests.Session()
    txt = proxy.split('@')
    login = txt[0].split(':')[0]
    pwd = txt[0].split(':')[1]

    session.proxies = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    }
    session.auth = HTTPProxyAuth(login, pwd)
    return session

# Функция, которая забирает емаил со страницы заказчика
# tab = 'common' - вкладка общая информация, 'add' - вкладка дополнительно
def email_parse(soup, tab='common'):
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
    print_log(f'FIND EMAIL: {email}')
    return email

# Функция поиска емаила заказчика
def find_customer_email(url_customer, driver):
    try:
        driver.get(url_customer)
        print_log(f'SEARCH CUSTOMER... ID : {url_customer[-9:-1]}')
        driver.implicitly_wait(3)
        customer = driver.find_element(By.XPATH, "//span[contains(text(),'Полное наименование заказчика')]/following::span[1]/a")
        ActionChains(driver).click(customer).perform()
        driver.implicitly_wait(1)
        driver.switch_to.window(driver.window_handles[1])
        try:
            print_log('SEARCH ADD_INFO...')
            add_info = driver.find_element(By.XPATH, "//a[contains(text(),'ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ')]")
            ActionChains(driver).click(add_info).perform()
            try:
                print_log('SEARCH EMAIL ON ADD_INFO TAB')
                xpath_email = "//span[contains(text(),'Контактный адрес электронной почты')]/following::span[1]"
                email = driver.find_element(By.XPATH, xpath_email)
                soup = BeautifulSoup(driver.page_source, 'lxml')
                return email_parse(soup, 'add')
            except Exception as ex:
                print_log(f'Error: {ex} Email not found on add_info tab')
        except Exception as ex:
            print(f'Error: {ex}', '// ER // Add_info tab not found')
            py_logger.info(f"Error: {ex} : Add_info tab not found")
            try:
                print_log('SEARCH EMAIL ON COMMON TAB')
                email = driver.find_element(By.XPATH, "//span[contains(text(),'Контактный адрес электронной почты')]/following::span[1]")
                soup = BeautifulSoup(driver.page_source, 'lxml')
                return email_parse(soup)
            except Exception as ex:
                print_log(f'Error: {ex} Email not found on common tab')

    except Exception as ex:
        print_log(f'Error: {ex} Full_name of customer not found')

    return 'NOT FOUND'


# ================================ Сбор ссылок ================================

# Функция подсчета количества страниц в запросе
def pages_count(url):
    try:
        proxy = get_proxy()
        print_log(f'Start pages count with proxy: {proxy}')
        response = init_session(proxy).get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        count = soup.find("div", {"id": "content"}).find("div", class_ = "wrap clearfix")
        count = count.find("div", class_ = "col-12").find("p").text

        print_log(f"{count}") # Вывод строки 'Найдено организаций: 13 (максимум 500)'

        word_list = count.split()
        num_list = []
        for word in word_list:
            if word.isnumeric():
                num_list.append(int(word))
        number = int(num_list[0] // 25)
        if num_list[0] % 25 != 0:
            number +=1
        print_log(f'Количество страниц: {number}')
        return number
    except Exception as ex:
        print_log(f'Error: {ex} __pages_count__ Not response : {url}')
        return 0

# Фунция, которая забирает ссылку на одну компанию с одной страницы
def get_company_urls_from_page(search_url, page):
    try:
        url_pagination = search_url + '&page=' + str(page)
        print_log(f'Обработана страница: {page}')

        response = init_session(get_proxy()).get(url_pagination)
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
        print_log(f'Error: {ex} __get_company_urls__ Не удалось перейти : {url_pagination}')
    return None

# Функция, которая собирает ссылки на все компании из одного поискового запроса
def search_url_parse(url):
    print_log(f"Start parse: {url}")
    try:
        number = pages_count(url)

        company_urls = []
        for page in range(1,number + 1):
            current_page_urls = get_company_urls_from_page(url, page)
            if current_page_urls is not None:
                company_urls.extend(current_page_urls)
        # добавляем к списку поисков адреса соттветствующих ему компаний
        #print('Отладка: ', company_urls)
        return company_urls
    except Exception as ex:
        print_log(f'Error: {ex} __searc_url_parse__ Не удалось перейти : {url}')
    return None

# Функция получения ссылки на заказчика по ссылке на компанию
def get_url_customer(url_company,proxy):
    # Переход на карточку организации
    try:
        url_total = url_base + url_company + url_show
        time.sleep(1)
        print_log(f'OPEN COMPANY PAGE : {url_company}')

        response = init_session(proxy).get(url_total)
        soup = BeautifulSoup(response.text, 'lxml')

        table = soup.find("div", class_ = "tab-pane active clearfix").find("table", class_ = "table")
        url_contract = table.find("a")['href']
        url_total = url_base + url_contract
    except Exception as ex:
        print_log(f'Error: {ex} : не удалось перейти на карточку организации')
    # Переход на карточку контракта
    try:
        time.sleep(1)
        response = init_session(proxy).get(url_total)
        print_log(f'OPEN CONTRACT PAGE : {url_company}')

        soup = BeautifulSoup(response.text, 'lxml')

        table = soup.find("div", class_ = "col-6 col-m-12 left").find("table", class_ = "table")
        url_customer = table.find("a")['href']
        return url_customer
        #print(url_customer)
    except Exception as ex:
        print_log(f'Error: {ex} : не удалось перейти на карточку контракта')
    return None


def write_search_file(data):
    global current_file_name
    global company_count
    with open(current_file_name, 'a') as f:
        f.write(f"{data}\n")


def make_all(url_company):
    global company_count
    try:
        company_increment()
        proxy = get_proxy()
        url_customer = get_url_customer(url_company, proxy)
        driver = new_driver(proxy)
        print_log(f'Start selenium with: {url_company}')
        try:
            email = find_customer_email(url_customer, driver)
            #print('Отладка 3:', email)
            if email != 'NOT FOUND':
                write_search_file(email)
        except Exception as ex:
            print_log(f'Error: {ex} from make_all(inner) function message')
        finally:
            driver.quit()

    except Exception as ex:
        print_log(f'Error: {ex} from make_all(outer) function message')


# =============================== Основная программа =========================
def main_pool():
    global proxies
    global proxy_count
    global all_emails
    global user_search_urls
    global df_urls_base
    # Загружаем адреса прокси серверов из файла
    proxies = load_proxies('proxy.csv')
    proxy_count = len(proxies)-1
    print_log(f'Всего прокси : {proxy_count+1}')
    # Запоминаем время начала работы скрипта
    time1 = datetime.datetime.now()
    print_log(f"Begin at: {time1.strftime('%X')}")

    for search_id,url_s in enumerate(user_search_urls):
        # Сбор ссылок на компании на открывшейся странице
        try:
            companies = search_url_parse(url_s)
            comp_count = len(companies)
            print_log(f'Есть контракты у {comp_count} компаний')
            if comp_count > 0:
                # Обнуляем счетчик компаний в файле
                with open(count_company_file,'w') as f:
                    f.write(str(0))
                print_log('Счетчик компаний инициализирован')
                # Обнуляем файл с емаилами
                with open(current_file_name, 'w') as f:
                    f.write('')
                print_log('Создан файл сбора адресов')

                emails = []
                company_count = 0

                with Pool(proxy_count+1) as p:
                    p.map(make_all, companies)

                with open(current_file_name, 'r') as f:
                    emails = [email.rstrip() for email in f.readlines()]

                all_emails.extend(emails)

                df_urls_base = df_urls_base[1:]
                df_urls_base.to_excel(urls_file_name)
                df_emails = pd.DataFrame({'email': all_emails})
                df_emails.to_excel(emails_file_name)
                print_log(f'Загружены адреса поискового запроса номер: {search_id}')
            else:
                print_log(f'По данному запросу нет компаний, переходим дальше')

        except Exception as ex:
            print_log(f'Error: {ex} in main_pool')


        time2 = datetime.datetime.now()
        print_log(f"End at: {time2.strftime('%X')}")
        time3 = time2 - time1
        time3 = round(time3.total_seconds()/60, 2)
        print_log(f"All time: {time3} minutes")


if __name__ == '__main__':
    main_pool()
