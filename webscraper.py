import re
import time
import traceback
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from discount import Discount


def parse_price(price):
    """ parse price from string '159,99 RON' or '159,99 LEI' or '159,99 lei' """
    price = str(price).lower()
    price = re.sub(r'\.', '', price)
    price = re.sub(r'\s+ron', '', price)
    price = re.sub(r'\s+lei', '', price)
    price = re.sub(r',', '.', price)
    return float(price)


def get_discount_pct(discount_price, regular_price):
    if regular_price <= 0:
        return 0
    return (1 - discount_price / regular_price) * 100


def discounts_reserved(url, threshold):
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    articles = soup.find_all('article', class_='es-product')
    for article in articles:
        discount_price = parse_price(article.section.contents[0].text)
        regular_price = parse_price(article.section.contents[1].text)
        discount_pct = get_discount_pct(discount_price, regular_price)
        if discount_pct > threshold:
            name = article.figure.a.img['alt']
            uri = article.figure.a['href']
            discounts.append(Discount(discount_pct, discount_price, name, uri))


def get_name_mango_outlet(divs):
    name = ''
    if len(divs) == 5:
        name_div = divs[3]
    else:
        name_div = divs[4]
    if name_div is not None:
        spans = name_div.find_all('span')
        for span in spans:
            name += span.text + ' '
    return name


def get_prices_mango_outlet(divs):
    if len(divs) == 5:
        price_div = divs[4]
    else:
        price_div = divs[5]
    if price_div is not None:
        spans = price_div.find_all('span')
        if len(spans) == 0:
            print('divs:' + str(divs))
            print('price_div:' + str(price_div))
        regular_price = parse_price(spans[0].text)
        discount_price = parse_price(spans[len(spans) - 1].text)
        return regular_price, discount_price


def get_name_mango(divs):
    name = ''
    for div in divs:
        spans = div.find_all('span', class_='product-name')
        if len(spans) > 0:
            for span in spans:
                name += span.text + ' '
            return name


def get_prices_mango(divs):
    for div in divs:
        if 'prices-container' in div['class']:
            spans = div.find_all('span')
            regular_price = parse_price(spans[0].text)
            discount_price = parse_price(spans[len(spans) - 1].text)
            return regular_price, discount_price
    return None, None


def discounts_mango(url, scroll_pages, threshold, sleep_time):
    browser = Chrome()
    browser.get(url)
    for i in range(scroll_pages):
        time.sleep(sleep_time)
        browser.find_element_by_tag_name('body').send_keys(Keys.END)
    soup = BeautifulSoup(browser.execute_script('return document.documentElement.outerHTML'), 'html.parser')
    main = soup.find('div', class_='main-vertical-body')
    pages = main.find_all('ul', class_='page--hidden')
    if len(pages) == 0:
        pages = main.find_all('div', class_='page')
    for page in pages:
        items = page.find_all('li')
        for item in items:
            divs = item.find_all('div')
            if 'outlet' in url:
                name = get_name_mango_outlet(divs)
                regular_price, discount_price = get_prices_mango_outlet(divs)
            else:
                name = get_name_mango(divs)
                get_prices_mango(divs)
                regular_price, discount_price = get_prices_mango(divs)
            discount_pct = get_discount_pct(discount_price, regular_price)
            if discount_pct > threshold:
                uri = '{uri.scheme}://{uri.netloc}'.format(uri=(urlparse(url))) + item.a['href']
                discounts.append(Discount(discount_pct, discount_price, name, uri))
    browser.close()


def discounts_zara(url, threshold):
    soup = BeautifulSoup(requests.get(url).content, 'html.parser')
    items = soup.find_all('li', class_='_product')
    for item in items:
        prices = item.find('div', class_='_product-price')
        if prices is not None:
            regular_price_span = prices.find('span', class_='main-price')
            if regular_price_span is None:
                regular_price_span = prices.find('span', class_='line-through')
            regular_price = parse_price(regular_price_span['data-price'])
            discount_price_span = prices.find('span', class_='sale')
            if discount_price_span is not None:
                discount_price = parse_price(discount_price_span['data-price'])
                discount_pct = get_discount_pct(discount_price, regular_price)
                if discount_pct > threshold:
                    name_div = item.find('div', class_='product-info-item-name')
                    name = name_div.a.text
                    uri = name_div.a['href']
                    discounts.append(Discount(discount_pct, discount_price, name, uri))


def discounts_hm(url, threshold_pct, sleep=1):
    browser = Chrome()
    browser.get(url)

    try:
        for x in range(100):
            more = browser.find_element(By.CSS_SELECTOR, 'button.js-load-more')
            if more.is_displayed():
                more.click()
                browser.find_element_by_tag_name('body').send_keys(Keys.END)
                time.sleep(sleep)

        soup = BeautifulSoup(browser.execute_script('return document.documentElement.outerHTML'), 'html.parser')
        items = soup.find_all('li', class_='product-item')
        for item in items:
            prices = item.find('strong', class_='item-price')
            discount = parse_price(prices.find('span', class_='sale').text)
            regular = parse_price(prices.find('span', class_='regular').text)
            article = item.find('h3', class_='item-heading')
            uri = '{uri.scheme}://{uri.netloc}'.format(uri=(urlparse(url))) + article.a['href']
            if get_discount_pct(discount, regular) > threshold_pct:
                discounts.append(Discount(get_discount_pct(discount, regular), discount, article.a.text, uri))
    except ElementClickInterceptedException as e:
        print(traceback.format_exc())
    browser.close()


if __name__ == "__main__":

    threshold_pct = 40
    scrolling_pages = 20
    sleep = 1.5
    discounts = []
    URLs_men = [
        'https://www.reserved.com/ro/ro/sale2-ro/men/bestsellers-ro/sb/0',
        # 'https://www.mangooutlet.com/ro/barbati/haine_c16912476?sort=asc',
        # 'https://shop.mango.com/ro/barbati/recomandate/sale_d14332139?sort=asc',
        # 'https://www.zara.com/ro/ro/barbat-outerwear-l715.html',
        # 'https://www.zara.com/ro/ro/barbat-jachete-l640.html',
        # 'https://www.zara.com/ro/ro/barbat-blugi-l659.html',
        # 'https://www.zara.com/ro/ro/barbat-pantaloni-l838.html',
        # 'https://www.zara.com/ro/ro/barbat-bermude-l592.html',
        # 'https://www.zara.com/ro/ro/barbat-tricouri-l855.html',
        # 'https://www.zara.com/ro/ro/barbat-hanorace-l821.html',
        # 'https://www.zara.com/ro/ro/barbat-sacouri-l608.html',
        # 'https://www.zara.com/ro/ro/barbat-camasi-l737.html',
        # 'https://www.zara.com/ro/ro/barbat-beachwear-l590.html',
        # 'https://www.zara.com/ro/ro/barbat-pantofi-l769.html',
        # 'https://www.zara.com/ro/ro/barbat-genti-l563.html',
        # 'https://www2.hm.com/ro_ro/reduceri/barbati/view-all.html',
    ]
    URLs_women = [
        # 'https://www.reserved.com/ro/ro/sale2-ro/woman/bestsellers-ro/sb/0',
        # 'https://www.mangooutlet.com/ro/femei/haine_c16402742?sort=asc',
        # 'https://shop.mango.com/ro/femei/recomandate/sale_d14760544?sort=asc',
        # 'https://www.zara.com/ro/ro/dama-sacouri-l1055.html',
        # 'https://www.zara.com/ro/ro/dama-rochii-l1066.html',
        # 'https://www.zara.com/ro/ro/dama-camasi-l1217.html',
        # 'https://www.zara.com/ro/ro/dama-tricouri-l1362.html',
        # 'https://www.zara.com/ro/ro/dama-tricot-l1152.html',
        # 'https://www.zara.com/ro/ro/dama-pantaloni-l1335.html',
        # 'https://www.zara.com/ro/ro/dama-blugi-l1119.html',
        # 'https://www.zara.com/ro/ro/dama-pantaloni-scurti-l1355.html',
        # 'https://www.zara.com/ro/ro/dama-fuste-l1299.html',
        # 'https://www.zara.com/ro/ro/dama-hanorace-l1320.html',
        # 'https://www.zara.com/ro/ro/dama-jachete-l1114.html',
        # 'https://www.zara.com/ro/ro/dama-outerwear-l1184.html',
        # 'https://www.zara.com/ro/ro/dama-pantofi-l1251.html',
        # 'https://www.zara.com/ro/ro/dama-genti-l1024.html',
        # 'https://www.zara.com/ro/ro/dama-accesorii-l1003.html',
        # 'https://www2.hm.com/ro_ro/reduceri/femei/view-all.html',
        # 'https://www2.hm.com/ro_ro/reduceri/home/view-all.html',
    ]
    URLs_girls = [
        # 'https://www.reserved.com/ro/ro/sale2-ro/kids-girl/bestsellers-ro/sb/0',
        # 'https://www.mangooutlet.com/ro/fete/haine_c80999254?sort=asc',
        # 'https://shop.mango.com/ro/fete/recomandate/sale_d16168230?sort=asc',
        'https://www2.hm.com/ro_ro/reduceri/copii/girls-size18m-10y.html',
    ]
    URLs = [
        URLs_men,
        # URLs_women,
        # URLs_girls,
    ]

    for url in [item for sublist in URLs for item in sublist]:
        if 'reserved' in url:
            discounts_reserved(url, threshold_pct)
        elif 'mango' in url:
            discounts_mango(url, scrolling_pages, threshold_pct, sleep)
        elif 'zara' in url:
            discounts_zara(url, threshold_pct)
        elif 'hm.com' in url:
            discounts_hm(url, threshold_pct)

    for discount in sorted(discounts, reverse=True):
        print(discount)
