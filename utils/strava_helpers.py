import os
import urllib.parse

import requests


def get_tokens(code):
    params = {
        "client_id": os.environ.get('STRAVA_CLIENT_ID'),
        "client_secret": os.environ.get('STRAVA_CLIENT_SECRET'),
        "code": code,
        "grant_type": "authorization_code"
    }
    return requests.post("https://www.strava.com/oauth/token", data=params).json()


def make_link_to_get_code(redirect_url: str) -> str:
    params_oauth = {
        "response_type": "code",
        "client_id": os.environ.get('STRAVA_CLIENT_ID'),
        "scope": "read,activity:write,activity:read_all",
        "approval_prompt": "auto",  # force
        "redirect_uri": redirect_url
    }
    values_url = urllib.parse.urlencode(params_oauth)
    return 'https://www.strava.com/oauth/authorize?' + values_url


def is_app_subscribed() -> bool:
    """A GET request to the push subscription endpoint to check Strava Webhook status of APP.

    :return: boolean
    """
    payload = {
        'client_id': os.environ.get('STRAVA_CLIENT_ID'),
        'client_secret': os.environ.get('STRAVA_CLIENT_SECRET')
    }
    response = requests.get('https://www.strava.com/api/v3/push_subscriptions', data=payload)
    try:
        print(response.json())
        return 'id' in response.json()[0]
    except (IndexError, KeyError, ValueError):
        return False
