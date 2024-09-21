# import pydash
# import json
# from collections import OrderedDict
# from zoho_books import ZohoBooks
# from zoho_auth import ZohoAuth
# from utils import log, get_all_fne_products, filter_requested_items
# from exceptions import EstimateIDNotFound, ZCRMPotentialIDMissing
# from constants import ESTIMATE_DEFAULT_FILTER

# def lambda_handler(event, context):
#     requested_items = OrderedDict()
#     NOT_ALLOWED = [
#         'name', 
#         'email',
#         'zcrm_potential_id',
#         'event_type', 
#         'guests', 
#         'created_at', 
#         'location', 
#         'allergies',
#         'beverages',
#         'equipments',
#         'event_datetime'
#     ]

#     log(event)

    # zcrm_potential_id = event.get('zcrm_potential_id')
    # zhbooks = ZohoBooks(auth=ZohoAuth(), products=get_all_fne_products())

    # print(f'zcrm deal ID: {zcrm_potential_id}')
    # if( not zcrm_potential_id): 
    #     raise ZCRMPotentialIDMissing('Zoho CRM Potential ID is missing')
    
    # eid = zhbooks.get_estimate_id(zcrm_potential_id, filter=ESTIMATE_DEFAULT_FILTER)
    # print(f'estimate ID: {eid}')

    # if(not eid):
    #     raise EstimateIDNotFound('Estimate ID Not Found')

#     requested_items['Food'] = filter_requested_items(event, NOT_ALLOWED)
#     requested_items['Beverages'] = filter_requested_items({"beverages": event.get('beverages')}, [])
#     requested_items['Miscellaneous'] = filter_requested_items({"equipments": event.get('equipments')}, [])
    
#     data = {
#         'estimate_id': eid,
#         'guests_count': event.get('guests'),
#         'event_type': event.get('event_type'),
#         'location': event.get('location'),
#         'allergies': event.get('allergies'),
#         'event_datetime': event.get('event_datetime'),
#         'requested_items': requested_items
#     }

#     response = None
#     try:
#         response = zhbooks.update_estimate(**data)
#         response = {
#             'message': pydash.get(response.json(), 'message'),
#             'code': pydash.get(response.json(), 'code')
#         }
#         print(f'response: {response}')
#     except Exception as err:
#         print(f'An unexpected error occurred while updating estimate: {err}')
#         print(f'payload received: {json.dumps(response)}')




import pydash
import json
from collections import OrderedDict
from zohobooks.books import ZohoBooks
from zohobooks.auth import ZohoAuth
from zohobooks.utils import log, get_all_fne_products, filter_requested_items, create_csv_file, parse_requested_menu_items, parse_services
from zohobooks.exceptions import CustomerIDNotFound
from zohobooks.constants import ESTIMATE_DEFAULT_FILTER


def lambda_handler(event, context):
    requested_items = OrderedDict()
    customer_id = None
    response = None
    zcrm_potential_id = event.get('zcrm_potential_id', "")
    zcrm_contact_id = event.get('zcrm_contact_id', "")
    name = event.get('name')
    email = event.get('email')
    zhbooks = ZohoBooks(auth=ZohoAuth(), products=get_all_fne_products())

    log(event)
    
    try:
        print(f'Fetching customer: {email}')
        customer_id = zhbooks.fetch_customer(email)
        print(f'Customer contact ID: {customer_id}')
    except CustomerIDNotFound as err:
        customer_contact = {
            'contact_name': name,
            'customer_email': email,
            'contact_email': email,
            'phone': event.get('phone'),
            'contact_type': 'customer',
            'customer_sub_type': 'individual',
        }
        print(f'Creating new contact: {name}')
        customer_id = zhbooks.create_customer(
            zcrm_contact_id=zcrm_contact_id,
            customer_contact=customer_contact
        )
        print(f'New contact created successfully: {customer_id}')
    except Exception as err:
        return {
            "statusCode": 500,
            "errorMessage": f'An unexpected error occurred: {err}',
        }
        
    requested_items['Food'] =  parse_requested_menu_items(event.get('menu'))
    requested_items['Beverages'] = filter_requested_items({"beverages": event.get('beverages')}, [])
    requested_items['Miscellaneous'] = filter_requested_items({"equipments": event.get('equipments')}, [])
    
    data = {
        'customer_id': customer_id,
        'guests_count': event.get('guests'),
        'event_type': event.get('event_type').lower(),
        'location': event.get('location'),
        'allergies': event.get('allergies'),
        'event_datetime': event.get('event_datetime'),
        'requested_items': requested_items,
        'zcrm_potential_id': zcrm_potential_id,
        'services': parse_services(event.get('services'))
    }
    
    try:
        response = zhbooks.create_estimate(**data)
        response = {
            'message': pydash.get(response.json(), 'message'),
            'code': pydash.get(response.json(), 'code')
        }
        return {
            "statusCode": 200,
            "response": response
        }
    except Exception as err:
        return {
            "statusCode": 500,
            "errorMessage": f'An unexpected error occurred: {err}',
        }
