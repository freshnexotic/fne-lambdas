import pydash
import boto3
import datetime
import csv
import re
import requests
import difflib
from requests.exceptions import HTTPError
from retry import retry
from zohobooks.constants import ALCOHOLIC_BEVERAGES_ID, TABLEWARE_SETS_COMPOSTABLE_ID, TABLEWARE_SETS_PORCELAIN_ID
from dateutil import parser

DELUXE_PACKAGE_TOTAL_ITEMS = 8
BASIC_PACKAGE_TOTAL_ITEMS = 5
ADDITIONAL_ITEM_RATE = 3

global TIER

def format_date(date, format='%d-%b-%Y %H:%M:%S'):
    return datetime.datetime.strptime(date, format).date()

def convert_date_format(date_str, format='%Y-%m-%d %H:%M'):
    dt = parser.isoparse(date_str)
    output_date_str = dt.strftime(format)
    
    return output_date_str
    
def log(data):
    name = data.get('name')
    event_type = data.get('event_type')
    guests = data.get('guests')
    # current_date = datetime.date.today().strftime('%Y-%m-%d')
    print('======================')
    print('| FNE EST GEN v2.0.0 |')
    print('======================')
    print(f'New Request: Name: *{name}* Type: *{event_type}* Guests: *{guests}*')
    

def filter_products_by_status(products, status):
    return pydash.filter_(products, lambda x: x['status'] == status)


def get_all_fne_products():
    s3 = boto3.client(
        's3',
        aws_access_key_id='AKIAVHKMPUFEFFEGNJ2E',
        aws_secret_access_key='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',
        region_name='us-east-1'
    )
    data = s3.get_object(Bucket='fne-misc', Key='fne-products.csv')
    data = data['Body'].read().decode('utf-8').splitlines()
    products = list(csv.DictReader(data))
    return filter_products_by_status(products, status='active')

def getItemRate(current_item, items, guests_count):
    total_items = len(items)
    guests_count = int(guests_count)
    price_per_person = determine_price_per_person(total_items, guests_count)

    for item in items:
        if(item == current_item):
            index = items.index(item)
            if(index + 1 <= BASIC_PACKAGE_TOTAL_ITEMS):
                return price_per_person / BASIC_PACKAGE_TOTAL_ITEMS
            else:
                return ADDITIONAL_ITEM_RATE

def getPremiumItemRate(item):
    return 1 * item.get('cf_premium').count('*')

def isPremiumItem(item):
    return '*' in item.get('cf_premium')
    

def create_csv_file(fields, data, filename):
    with open(filename, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)

def filter_requested_items(dict, not_allowed):
    pattern = r"hosts will provide"
    arr = []
    
    def cb(value, key): 
        if(key not in not_allowed): 
            if(not pydash.is_empty(value) and not value == '[]'):
                for x in value.split(','):
                    match = re.search(pattern, x, re.IGNORECASE)
                    if(x != '' and not match):
                        arr.append(x.strip())
    pydash.for_in(dict, cb)
    return pydash.flatten_deep(arr)

def find_matching_products(products, requested_items):
    matching_products = []
    for requested_item in requested_items:
        best_match = max(products, key=lambda x: difflib.SequenceMatcher(None, x['name'], requested_item).ratio())
        matching_products.append({
            'item_id':best_match.get('item_id'),
            'item_name':best_match.get('item_name'),
            'cf_premium': best_match.get('cf_premium'),
            'cf_category': best_match.get('cf_category'),
        })
    return matching_products

def flattened_list(items):
    flattened_list = []
    for value in items.values():
        flattened_list.extend(value)
    return flattened_list

def determine_price_per_person(guests_count):
    global TIER

    if(guests_count >= 20 and guests_count < 50):
        TIER = 1
        return 21
    elif(guests_count >= 50 and guests_count < 100):
        TIER = 2
        return 19
    else:
        TIER = 3
        return 17


def foodItemsTranslator(guests_count, items):
    
    if(pydash.is_empty(items)):
        return []
    
    newFoodItems = []
    total_items = len(items)
    guests_count = int(guests_count)
    price_per_person = determine_price_per_person(guests_count)
    additioanal_field = {'header_name': 'Menu', 'quantity': guests_count}
    
    for index, item in enumerate(items):
        rate = 0
        if(index + 1 <= BASIC_PACKAGE_TOTAL_ITEMS):
            rate = 0
        else:
            rate = ADDITIONAL_ITEM_RATE            
                 
        if(isPremiumItem(item)): 
            rate = getPremiumItemRate(item)

        additioanal_field.update({'rate': rate})    
        newFoodItems.append({**item, **additioanal_field})

    if(not pydash.is_empty(newFoodItems)):
        newFoodItems[0].update({'rate': price_per_person})
    
    return newFoodItems


def beveragesItemsTranslator(guests_count, items):
    if(pydash.is_empty(items)):
        return []
    
    global TIER
    newItems = []
    guests_count = int(guests_count)
    additioanal_field = { 'header_name': 'Beverages', 'quantity': guests_count }

    for item in items:
        rate = 0
        if(not item.get('item_id') == ALCOHOLIC_BEVERAGES_ID):
            rate = 4 if TIER == 1 else 3 if TIER == 2 else 2.5
        
        additioanal_field.update({'rate': rate})
        newItems.append({**item, **additioanal_field})

    return newItems 


def miscItemsTranslator(guests_count, items):
    if(pydash.is_empty(items)):
        return []
    
    newItems = []
    guests_count = int(guests_count)
    additioanal_field = {'header_name': 'Equipment Rentals'}

    for item in items:
        rate = 0
        quantity = 0
        if(item.get('item_id') == TABLEWARE_SETS_COMPOSTABLE_ID):
            quantity = guests_count
            rate = 3 if TIER == 1 else 2.5 if TIER == 2 else 2

        if(item.get('item_id') == TABLEWARE_SETS_PORCELAIN_ID):
            quantity = guests_count
            rate = 4 if TIER == 1 else 3.5 if TIER == 2 else 3
        
        additioanal_field.update({'rate': rate})
        additioanal_field.update({'quantity': quantity})
        newItems.append({**item, **additioanal_field})

    return newItems


def make_request(auth, url, params, headers, data=None, method='GET'):
        try:
            response = requests.request(
                method=method, 
                url=url, 
                params=params, 
                headers=headers, 
                data=data
            )
            response.raise_for_status()
            return response
        except HTTPError as http_err:
            if(http_err.response.status_code == 401):
                auth.refresh_token()
                raise
        except Exception as err:
            raise

def getServiceFees(services):
    services_description = None
    fee = 0
    services_description = None
    DELIVERY_SERVICE_KEY = 'delivery'

    if(pydash.is_empty(services)):
        return fee, services_description
    

    global TIER
    
    if('Pickup' in services):
        services_description = ''
        fee = 10 if TIER == 1 else 10 if TIER == 2 else 10
        
    if('Buffet-Style Setup' in services):
        services_description = f'{DELIVERY_SERVICE_KEY}, buffet setup'
        fee = 20 if TIER == 1 else 18 if TIER == 2 else 15

    if('Serve' in services):
        services_description = f'{DELIVERY_SERVICE_KEY}, buffet setup, clean-up'
        fee = 35 if TIER == 1 else 35 if TIER == 2 else 30

    if('Plated' in services):
        services_description = f'{DELIVERY_SERVICE_KEY}, plated service, clean-up'
        fee = 35 if TIER == 1 else 35 if TIER == 2 else 30

    return fee, services_description


def getItemsTotalAmount(items):
    total = 0
    for item in items:
        total += float(item['rate']) * float(item['quantity'])
    return total


def reorder_food_items(food_list):
    seafoods = ['shrimp', 'lobster', 'salmon', 'cod', 'Red Snapper', 'Conch', 'fish', 'crab', 'clam', 'oyster', 'mussel', 'calamari', 'octopus', 'squid', 'scallop', 'tuna', 'sardine', 'anchovy', 'herring', 'mackerel', 'trout', 'bass', 'halibut', 'swordfish', 'snapper', 'tilapia', 'catfish', 'mahi-mahi', 'grouper', 'perch', 'pike', 'pollock', 'whitefish', 'eel', 'sturgeon', 'caviar', 'shellfish', 'crustacean', 'mollusk', 'cephalopod', 'bivalve', 'gastropod']
    additional_items = ['Charcuterie Board']
    items = seafoods + additional_items   
    seafood = [item.lower() for item in items]
    
    non_seafood = []
    seafood_items = []

    for item in food_list:
        if any(seafood_item in item.lower() for seafood_item in seafood):
            seafood_items.append(item)
        else:
            non_seafood.append(item)
    
    return non_seafood + seafood_items


def parse_requested_menu_items(body):
    items = body.split('||')
    x = [re.sub(r'[\[\]]', '', item).split(',') for item in items if item != '[]']
    return pydash.flatten_deep(x)


def reorder_premium_items(items):
    def premium_sort_key(item):
        return '*' in item['cf_premium']
    
    items.sort(key=premium_sort_key)
    return items

def parse_services(service_string):
    stripped = service_string.strip("[]")
    services = [s.strip().strip("'\"") for s in stripped.split(",")]
    return services

