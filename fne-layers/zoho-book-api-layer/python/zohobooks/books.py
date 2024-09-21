
import pydash
import json
from requests.exceptions import HTTPError
from retry import retry

from zohobooks.constants import (
    ORGANIZATION_ID, 
    ITEM_NOT_FOUND_ID, 
    ZOHO_BOOK_ENDPOINTS
)

from zohobooks.utils import (
    foodItemsTranslator, 
    beveragesItemsTranslator,
    miscItemsTranslator,
    make_request, 
    find_matching_products,
    convert_date_format,
    getItemsTotalAmount, 
    getServiceFees, 
    reorder_premium_items
)

from zohobooks.exceptions import (
    EmptyProductListError, 
    CustomerIDNotFound,
    ZCRMInvalidID
)

class ZohoBooks:
    def __init__(self, auth, products=None):
        self.fne_products = products
        self.zh_auth = auth
    
    def get_auth_header(self):
        return { 'Authorization': f'Zoho-oauthtoken {self.zh_auth.oauthtoken}'}
    
    
    def _construct_items(self, guests_count, requested_items):
        print('Constructing items...')
        requested_food_items = find_matching_products(self.fne_products, requested_items.get('Food'))
        requested_food_items = reorder_premium_items(requested_food_items)
        requested_beverages_items = find_matching_products(self.fne_products, requested_items.get('Beverages'))
        requested_misc_items = find_matching_products(self.fne_products, requested_items.get('Miscellaneous'))
        
        requested_food_items = foodItemsTranslator(guests_count, requested_food_items)
        requested_beverages_items = beveragesItemsTranslator(guests_count, requested_beverages_items)
        requested_misc_items = miscItemsTranslator(guests_count, requested_misc_items)
        
        print('Requested Food Items: ', requested_food_items)
        print('Requested Beverages Items: ', requested_beverages_items)
        print('Requested Miscellaneous Items: ', requested_misc_items)

        items = requested_food_items + requested_beverages_items + requested_misc_items
        return items

    
    @retry(HTTPError, tries=2, delay=2)
    def get_estimate_id(self, zcrm_potential_id, filter = {}):
        http_request = {
            'auth': self.zh_auth,
            'url': ZOHO_BOOK_ENDPOINTS.ESTIMATE.value, 
            'headers': self.get_auth_header(),
            'method': 'GET',
            'params': { 
                'organization_id': ORGANIZATION_ID,
                'zcrm_potential_id': zcrm_potential_id
            },
        }

        response = make_request(**http_request)
        estimates = pydash.get(response.json(), 'estimates')

        if(pydash.is_empty(estimates)):
            return None

        estimates = pydash.find(estimates, filter)
        return pydash.get(estimates, 'estimate_id')

    
    @retry(HTTPError, tries=2, delay=2)
    def fetch_customer(self, customer_email):
        http_request = {
            'auth': self.zh_auth,
            'url': ZOHO_BOOK_ENDPOINTS.CONTACTS.value, 
            'headers': self.get_auth_header(),
            'method': 'GET',
            'params': { 
                'organization_id': ORGANIZATION_ID,
                'email': customer_email
            },
        }

        response = make_request(**http_request)
        contacts = pydash.get(response.json(), 'contacts')
        if(pydash.is_empty(contacts)):
            raise CustomerIDNotFound(f'Customer ID not found for: {customer_email}')
        
        return contacts[0].get('contact_id')


    @retry(HTTPError, tries=2, delay=2)
    def create_customer_contact(self, customer_contact):
        data = json.dumps({
            'contact_name': customer_contact.get('contact_name'),
            'contact_type': customer_contact.get('contact_type'),
            'phone': customer_contact.get('phone'),
            'customer_sub_type': customer_contact.get('customer_sub_type'),
            'is_portal_enabled': False,
            'contact_persons': [{
                'email': customer_contact.get('contact_email'),
                'phone': customer_contact.get('phone'),
                'first_name': customer_contact.get('contact_name').split(' ')[0],
                'last_name': customer_contact.get('contact_name').split(' ')[1],
            }],
        })

        http_request = {
            'auth': self.zh_auth,
            'url': ZOHO_BOOK_ENDPOINTS.CONTACTS.value, 
            'headers': self.get_auth_header(),
            'method': 'POST',
            'params': { 'organization_id': ORGANIZATION_ID },
            'data': data
        }

        response = make_request(**http_request)
        contact = pydash.get(response.json(), 'contact')
        return contact.get('contact_id')
    

    @retry(HTTPError, tries=2, delay=2)
    def sync_customer_from_zcrm_id(self, zcrm_contact_id):
        if(not zcrm_contact_id):
            return None
        
        url = f'{ZOHO_BOOK_ENDPOINTS.CRM_CONTACT.value}/{zcrm_contact_id}/import'
        http_request = {
            'auth': self.zh_auth,
            'url': url, 
            'headers': self.get_auth_header(),
            'method': 'POST',
            'params': { 'organization_id': ORGANIZATION_ID },
            'data': {'contact_id': zcrm_contact_id}
        }

        response = make_request(**http_request)
        
        if(response is None):
            raise ZCRMInvalidID(f'Invalid ZCRM ID: {zcrm_contact_id}')
        
        contact = pydash.get(response.json(), 'data')
        return contact.get('customer_id')
    

    def create_customer(self, zcrm_contact_id, customer_contact):
        if(zcrm_contact_id):
            try:
                return self.sync_customer_from_zcrm_id(zcrm_contact_id)
            except ZCRMInvalidID as e:
                return self.create_customer_contact(customer_contact)
        return self.create_customer_contact(customer_contact)
    

    @retry(HTTPError, tries=2, delay=2)
    def _create_estimate(self, **kwargs):
        customer_id = kwargs.get('customer_id')
        guests_count = kwargs.get('guests_count')
        location = kwargs.get('location', '')
        allergies = kwargs.get('allergies')
        event_type = kwargs.get('event_type')
        items = kwargs.get('items')
        zcrm_potential_id = kwargs.get('zcrm_potential_id')
        event_datetime_unformatted = kwargs.get('event_datetime')
        event_datetime = convert_date_format(event_datetime_unformatted)
        fee, services_description = getServiceFees(kwargs.get('services'))
        total = getItemsTotalAmount(items)
        data = json.dumps({
            "customer_id": customer_id,
            "line_items": items,
            "zcrm_potential_id": zcrm_potential_id,
            "adjustment": fee / 100 * total,
            "adjustment_description": f'{fee}% Service Fees: ({services_description})',
            "custom_fields": [
                {
                    "value": allergies,
                    "label": "Allergies & Dietary Restrictions",
                    "placeholder":"cf_food_allergies"
                },
                {
                    "value": location,
                    "label": "Event Location",
                    "placeholder":"cf_location"
                },
                {
                    "value": event_datetime,
                    "label": "Event DateTime",
                    "placeholder":"cf_event_datetime"
                }
            ],
            "subject_content": f'Catering service for a(n) {event_type} of {guests_count} people',
        })

        http_request = {
            'auth': self.zh_auth,
            'url': ZOHO_BOOK_ENDPOINTS.ESTIMATE.value,
            'headers': self.get_auth_header(),
            'method': 'POST',
            'params':  { 'organization_id': ORGANIZATION_ID },
            'data': data
        }

        return make_request(**http_request)
    
    
    def create_estimate(self, **kwargs):
        data = {
            'customer_id': kwargs.get('customer_id'),
            'guests_count': kwargs.get('guests_count'),
            'event_type': kwargs.get('event_type'),
            'items': self._construct_items(kwargs.get('guests_count'), kwargs.get('requested_items')),
            'location': kwargs.get('location'),
            'allergies': kwargs.get('allergies'),
            'event_datetime': kwargs.get('event_datetime'),
            'zcrm_potential_id': kwargs.get('zcrm_potential_id'),
            'services': kwargs.get('services')
        }

        return self._create_estimate(**data)
    
    
    @retry(HTTPError, tries=2, delay=2)
    def _update_estimate(self, **kwargs):
        estimate_id = kwargs.get('estimate_id')
        guests_count = kwargs.get('guests_count')
        location = kwargs.get('location')
        allergies = kwargs.get('allergies')
        event_type = kwargs.get('event_type')
        items = kwargs.get('items')
        event_datetime = kwargs.get('event_datetime')

        url = f"{ZOHO_BOOK_ENDPOINTS.ESTIMATE.value}/{estimate_id}"
        data = json.dumps({
            "line_items": items,
            "custom_fields": [
                {
                    "value": allergies,
                    "label": "Allergies & Dietary Restrictions",
                    "placeholder":"cf_food_allergies"
                },
                {
                    "value": location,
                    "label": "Event Location",
                    "placeholder":"cf_location"
                },
                {
                    "value": event_datetime,
                    "label": "Event Date",
                    "placeholder":"cf_event_datetime"
                }
            ],
            "subject_content": f'Catering service for a(n) {event_type} of {guests_count} people',
        })

        http_request = {
            'auth': self.zh_auth,
            'url': url,
            'headers': self.get_auth_header(),
            'method': 'PUT',
            'params':  { 'organization_id': ORGANIZATION_ID },
            'data': data
        }

        return make_request(**http_request)

    
    def update_estimate(self, **kwargs):
        data = {
            'estimate_id': kwargs.get('estimate_id'),
            'guests_count': kwargs.get('guests_count'),
            'event_type': kwargs.get('event_type'),
            'items': self._construct_items(kwargs.get('guests_count'), kwargs.get('requested_items')),
            'location': kwargs.get('location'),
            'allergies': kwargs.get('allergies'),
            'event_datetime': kwargs.get('event_datetime')
        }
        return self._update_estimate(**data)
    
    @retry(HTTPError, tries=2, delay=2)
    def _get_all_products_items(self, page=1):
        url = ZOHO_BOOK_ENDPOINTS.PRODUCTS.value
        http_request = {
            'auth': self.zh_auth,
            'url': url,
            'headers': self.get_auth_header(),
            'method': 'GET',
            'params': { 
                'organization_id': ORGANIZATION_ID,
                'page': page
            }
        }

        response = make_request(**http_request)
        has_more_page = response.json().get('page_context').get('has_more_page')
        page = response.json().get('page_context').get('page')
        items = pydash.get(response.json(), 'items')
        return (items, page, has_more_page)
    

    def get_all_items(self):
        products = []
        page = 0

        while(True): 
            items, page, has_more_page = self._get_all_products_items(page + 1)
            if(not pydash.is_empty(items)): 
                products.append(items)
            if(has_more_page == False): 
                break

        return pydash.flatten_deep(products)
    