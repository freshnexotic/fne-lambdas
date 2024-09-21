import requests
from requests.exceptions import HTTPError

class ZohoAuth:

    def __init__(self):
        self.oauthtoken = '1000.bdfcd0e45375abcd18288f439b528edf.1207d837c9e732f5aad4d8e277dde36a'

    def getToken():
        url = 'https://accounts.zoho.com/oauth/v2/token'
        try:
            response = requests.post(
                url, 
                data= {
                    'code': '1000.be55cffabc6b033bfac8bb547708b662.150dc79cf80ccc13827b0837393a468e',
                    'client_id': '1000.X7JQMGVCN0OIG2AN9L34Y2VZWR6RIJ',
                    'client_secret': '3125cff29f8f062038b87aba494b0626d58a9769e7',
                    'grant_type': 'authorization_code',
                    'scope':'ZohoBooks.fullaccess.all',
                    'redirect_uri':'https://www.example.com/callback',
                }
            )

            # If the response was successful, no Exception will be raised
            print(response.status_code)
            print(response.content)
            response.raise_for_status()
            
        except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
        except Exception as err:
            print(f'Other error occurred: {err}')
        else:
            print('Success!')

    def refresh_token(self):
        refresh_token_url = 'https://accounts.zoho.com/oauth/v2/token?grant_type=refresh_token'

        params = {
            'refresh_token': '1000.a820f08edeea6e156a51b5e4059af0b6.2ce4e53061312edb730dc3aede2af034',
            'client_id': '1000.X7JQMGVCN0OIG2AN9L34Y2VZWR6RIJ',
            'client_secret': '3125cff29f8f062038b87aba494b0626d58a9769e7'
        }

        try:
            print(f'Refreshing token...') 
            response = requests.post(url=refresh_token_url, params=params)
            response.raise_for_status()
            data = response.json()
            self.oauthtoken = data.get('access_token')
            print(self.oauthtoken)
        except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}') 
        except Exception as err:
            print(f'Other error occurred: {err}')