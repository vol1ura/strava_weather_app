from pprint import pprint

from dotenv import load_dotenv
import requests
import os
import urllib.parse


dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


def get_tokens(code):
    params = {
        "client_id": os.environ.get('STRAVA_CLIENT_ID'),
        "client_secret": os.environ.get('STRAVA_CLIENT_SECRET'),
        "code": code,
        "grant_type": "authorization_code"
    }
    token_response = requests.post("https://www.strava.com/oauth/token", data=params).json()
    print('resp', token_response)  # TODO save to database
    return token_response


def make_link_to_get_code(redirect_url):
    params_oauth = {
        "response_type": "code",
        "client_id": os.environ.get('STRAVA_CLIENT_ID'),
        "scope": "read,activity:write,activity:read_all",
        "approval_prompt": "auto",  # force
        "redirect_uri": redirect_url
    }
    values_url = urllib.parse.urlencode(params_oauth)
    return 'https://www.strava.com/oauth/authorize?' + values_url


def view_subscription():
    """A GET request to the push subscription endpoint can be used to view subscription details.

    :return:
    """
    payload = {
        'client_id': os.environ.get('STRAVA_CLIENT_ID'),
        'client_secret': os.environ.get('STRAVA_CLIENT_SECRET')
    }
    resp = requests.get('https://www.strava.com/api/v3/push_subscriptions', data=payload)
    pprint(resp.json())
    return resp


def db_add_athlete(token):
    pass
