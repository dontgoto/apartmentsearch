#!/usr/bin/env python
import os
import re
import requests
import pygsheets
from bs4 import BeautifulSoup as Bs
import googlemaps
import datetime
import pytz
from googlemaps.distance_matrix import distance_matrix as gdist
import numpy as np
import pickle as pkl

PATH = "./"
SEARCH_PAGE = "http://www.wg-gesucht.de/wg-zimmer-in-Dortmund.26.0.1.0.html?offer_filter=1&city_id=26&category=0&rent_type=2&sMin=12&rMax=400&dFr=1504242000&dTo=1509512400&ot%5B602%5D=602&ot%5B635%5D=635&wgAge=23"
SEARCH_PAGE = "https://www.wg-gesucht.de/wg-zimmer-in-Dortmund.26.0.1.0.html"
FILTERED_PKL_PATH = './filteredApartments.pkl'
URL_DOMAIN = 'http://www.wg-gesucht.de/'

SPREADSHEET_URL = os.environ['APT_SPREADSHEET_URL'] #customize
GMAPS_API_KEY = os.environ["GMAPS_API_KEY"]

if not os.path.isfile('./filteredApartments.pkl'):
    initialize = []
    pkl.dump(initialize, open('./filteredApartments.pkl', 'ab'))

### search settings
PRICE_LIMIT = 400.0
OLDEST = 30 # agelimits for flatmates
YOUNGEST = 18
AGE = 1 # your age
SEX = 'Mann' # your sex
CITY = "Dortmund" # city to search in
WORK = "Dortmund Otto Hahn Straße 4" # location of university/work
BFFS = "Dortmund Münsterstraße" # location of other important location

PAGINATION_SELECTOR = '.detailansicht'
LISTING_DETAIL_BTN_SELECTOR = '.btn-details'
NEXT_PAGE_SELECTOR = '.next'
PRICE_SELECTOR = '.price'
now = datetime.datetime.now()
depTime = datetime.datetime(now.year,
                            now.month,
                            now.day,
                            8, 1, 1, 1,
                            tzinfo=pytz.utc)
gmaps = googlemaps.Client(key=GMAPS_API_KEY)



def get_scraped_page(url):
    res = requests.get(url)
    return Bs(res.text, 'lxml')


def clean_markup(string):
    string = clean_special_chars(string)
    return re.sub(r'<[^>]*>', '', string)


def process_listings_page(link):
    try:
        dom = get_scraped_page(link)

        details_urls = [URL_DOMAIN + btn.get('href')
                        for btn in dom.select('.btn-details')]

        return [
            process_listing(listing_details_url)
            for listing_details_url in details_urls
        ]

    except Exception as e:
        print('Exception')
        print(e)


def get_transits(street, bffsAddress=bffs, uniAdress=WORK, depTime=depTime, apiType='gmaps'):
    '''
    apiType : string
        choice between gmaps and pyefa (better for the VRR region)
    '''
    address = CITY + " " + street
    if apiType == 'gmaps':
        unibike = gdist(gmaps, origins=address,
                        destinations=workAdress, mode="bicycling")
        bffsbike = gdist(gmaps, origins=address,
                         destinations=bffs, mode="bicycling")
        unitransit = gdist(gmaps, origins=address,
                           destinations=workAdress, mode="transit",
                           departure_time=depTime)
        unitransitTime = get_first_transit(unitransit, 'duration')
        unibikeTime = get_first_transit(unibike, 'duration')
        bffsbikeTime = get_first_transit(bffsbike, 'duration')
        unibikeDist = get_first_transit(unibike, 'distance')
        bffsbikeDist = get_first_transit(bffsbike, 'distance')
    elif apiType == 'pyefa':
        unibike = 1
        # needs to be implemented
    transits = {'unitransitTime': unitransitTime,
                'unibikeTime': unibikeTime,
                'bffsbikeTime': bffsbikeTime,
                'unibikeDist': unibikeDist,
                'bffsbikeDist': bffsbikeDist}
    for key in transits:
        if transits[key] == None:
            transits[key] = ''

    return transits


def get_first_transit(gmapsDict, context='duration'):
    if 'rows' in gmapsDict:
        if len(gmapsDict['rows']) > 0:
            if 'elements' in gmapsDict['rows'][0]:
                if len(gmapsDict['rows'][0]['elements']) > 0:
                    if context in gmapsDict['rows'][0]['elements'][0]:
                        return gmapsDict['rows'][0]['elements'][0][context]['text']
    else:
        print('Route not found')
        return ''


def clean_links(links):
    '''Removes airbnb, affiliate, empty, and other useless urls.'''
    links = list(set(links))
    links = [link for link in links if
             ("airbnb" and "affiliate" and "filter" and "26.0.1.0") not in link]
    links = [link for link in links if not link == '']

    return links


def commute_time_too_long(transits, uniBikeLimit=30., friendsBikeLimit=25.0):
    keys = ['unibikeTime', 'bffsbikeTime']
    for key in keys:
        if type(transits[key]) == type(None):
            transits[key] = '0 mins'
    if transits == '' or not transits:
        return False
    elif ("hour" in transits['unibikeTime']) or ("hour" in transits['bffsbikeTime']):
        return True
    elif get_float(transits['unibikeTime']) > uniBikeLimit:
        return True
    elif get_float(transits['bffsbikeTime']) > firendsBikeLimit:
        return True
    else:
        return False


def process_listing(currentDoms, link, street, transits):
    size = currentDoms.find_all('label', attrs={'class': ['amount']})[1]\
                      .text.split()[0]
    rent = currentDoms.find_all('label', attrs={'class': ['amount']})[2]\
                      .text.split()[0]
    mobile = currentDoms.find_all('span', attrs={'class': ['printonly']})
    if len(mobile) > 0:
        mobile = mobile[0].text
    else:
        mobile = ' '
    name = currentDoms.find(text='Name:').parent.parent.text.split()[1:]
    name = ' '.join(name)
    rentPerSize = np.round(get_float(rent) / get_float(size), decimals=2)
    noOfPeople = float(currentDoms.find_all('li', text=re.compile('er WG*'))[0]
                                  .text.split()[3].split('er')[0])
    totalSize = currentDoms.find_all('li', text=re.compile('Wohnungsgröße:*'))
    if len(totalSize) > 0:
        totalSize = totalSize[0].text.split()[1]
        effectiveRent = (get_float(rent) * noOfPeople /
                            np.max([get_float(totalSize),
                                    get_float(size)*noOfPeople+15]))
        effectiveRent = np.round(effectiveRent, decimals=2)
    else:
        totalSize = ''
        effectiveRent = ''
    os.system(f"notify-send -u critical -a 'New Apartment Listing' -t 0 $'\\n {street}\\n {size}, {rent}\\n uni: {transits['unibikeDist']}, friends: {transits['bffsbikeDist']}'")
    return [' ', street, name, size, rent, rentPerSize,
            noOfPeople, totalSize, effectiveRent, mobile,
            transits['unitransitTime'], transits['unibikeTime'],
            transits['unibikeDist'], transits['bffsbikeTime'],
            transits['bffsbikeDist'], link]


def get_float(string):
    '''Gets the float from a string of either Money: x€ or size: xm²'''
    if type(string) == type(float):
        return string
    if '€' in string:
        return float(string.split('€')[0])
    elif 'm²' in string:
        return float(string.split('m²')[0])
    elif 'mins' in string:
        return float(string.split('mins')[0])
    elif string == '':
        return 0.0


def does_my_age_fit(gesuchtWird):
    index = gesuchtWird.index
    if 'zwischen' in gesuchtWird:
        minAge = int(gesuchtWird[index('zwischen')+1])
        maxAge = int(gesuchtWird[index('zwischen')+3])
    elif 'ab' in gesuchtWird:
        minAge = int(gesuchtWird[index('ab')+1])
        maxAge = 99
    elif 'bis' in gesuchtWird:
        minAge = 1
        maxAge = int(gesuchtWird[index('bis')+1])
    else:
        return True
    if ((AGE > maxAge) or (AGE < minAge)):
        print(f"Not looking for {AGE} year olds.")
        return False
    else:
        return True


def does_their_age_fit(gesuchtWird): # needs implementation
    return True


def domfilters_satisfied(currentDoms):
    '''Returns True if all filters are passed, return False otherwise.'''
    gesuchtWird = currentDoms.find_all('h4', text=re.compile('Gesucht wird'))
    gesuchtWird = gesuchtWird[0].next.next.next.text.split()
    if SEX not in gesuchtWird:
        print(f"Not looking for '{SEX}'")
        return False
    elif not does_my_age_fit(gesuchtWird):
        return False
    elif not does_their_age_fit(gesuchtWird):
        return False
    else:
        return True


def get_listing_links(SEARCH_PAGE):
    dom = get_scraped_page(SEARCH_PAGE)
    doms = [dom for dom in dom.select(PAGINATION_SELECTOR)]
    links = [SEARCH_PAGE] + [
    URL_DOMAIN + a.get('href')
    for a in doms
    ]
    return clean_links(links)


if __name__ == "__main__":
    gc = pygsheets.authorize(service_file='credentials.json')
    sheet = gc.open_by_url(SPREADSHEET_URL).sheet1
    urls_stored = sheet.get_col(16)  #
    filteredApartments = pkl.load(open('/home/fongo/sync/git/apartmentsearch/filteredApartments.pkl', 'rb'))
    links = get_listing_links(SEARCH_PAGE)
    links = [link for link in links if link not in urls_stored[:40]]  # limit because urls get reused by this site
    links = [link for link in links if link not in filteredApartments[-25:]]  # limit because urls get reused by this site
    if len(links) == 0:
        print('No new apartments')
    newFilteredApartments = []
    for link in links:
        currentDoms = get_scraped_page(link)
        print(link)
        if not domfilters_satisfied(currentDoms):
            newFilteredApartments.append(link)
            continue
        street = currentDoms.find_all('h3', text=re.compile('Adresse'))[0]\
                            .next.next.next.text.split('\n')[1].strip()
        print(street)
        transits = get_transits(street)
        if commute_time_too_long(transits):
            newFilteredApartments.append(link)
            continue
        values = process_listing(currentDoms, link, street, transits)
        sheet.insert_rows(row=1, values=values)
    filteredApartments.extend(newFilteredApartments)
    pkl.dump(filteredApartments, open(filteredpklPath , 'wb'))
        # if len(urls_stored) > 0:
                # send_data_via_sms(ls)
