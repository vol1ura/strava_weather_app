import time
from pprint import pprint

from dotenv import load_dotenv
import requests
import os
import urllib.parse


dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


def get_headers(user_id):
    access_token = ''
    return {'Authorization': f"Bearer {access_token}"}


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


def is_subscribed():
    """A GET request to the push subscription endpoint can be used to view subscription details.

    :return: boolean
    """
    payload = {
        'client_id': os.environ.get('STRAVA_CLIENT_ID'),
        'client_secret': os.environ.get('STRAVA_CLIENT_SECRET')
    }
    response = requests.get('https://www.strava.com/api/v3/push_subscriptions', data=payload)
    return response.ok and 'id' in response.json()[0]


def get_activity(user_id, activity_id):
    """Get information about activity

    :param user_id:
    :param activity_id: integer or string is a number
    :return: dictionary with activity data
    """
    url = f'https://www.strava.com/api/v3/activities/{activity_id}'
    return requests.get(url, headers=get_headers(user_id)).json()


def modify_activity(user_id, activity_id, payload: dict):
    """
    Method can change UpdatableActivity parameters such that description, name, type, gear_id.
    See https://developers.strava.com/docs/reference/#api-models-UpdatableActivity

    :param user_id:
    :param activity_id: integer Strava activity ID
    :param payload: dictionary with keys description, name, type, gear_id, trainer, commute
    :return: dictionary with updated activity parameters
    """
    url = f'https://www.strava.com/api/v3/activities/{activity_id}'
    return requests.put(url, headers=get_headers(user_id), data=payload).json()


def compass_direction(degree: int, lan='en') -> str:
    compass_arr = {'ru': ["С", "ССВ", "СВ", "ВСВ", "В", "ВЮВ", "ЮВ", "ЮЮВ",
                          "Ю", "ЮЮЗ", "ЮЗ", "ЗЮЗ", "З", "ЗСЗ", "СЗ", "ССЗ", "С"],
                   'en': ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]}
    return compass_arr[lan][int((degree % 360) / 22.5 + 0.5)]


def add_weather(user_id, activity_id, lan='en'):
    weather_api_key = os.environ.get('API_WEATHER_KEY')
    activity = get_activity(user_id, activity_id)
    if activity['manual']:
        print(f"Activity with ID{activity_id} is manual created. Can't add weather info for it.")
        return
    description = activity.get('description', '')
    description = '' if description is None else description
    if description.startswith('Погода:'):
        print(f'Weather description for activity ID{activity_id} is already set.')
        return
    lat = activity['start_latitude']
    lon = activity['start_longitude']
    time_tuple = time.strptime(activity['start_date'], '%Y-%m-%dT%H:%M:%SZ')
    start_time = int(time.mktime(time_tuple))
    base_url = f"https://api.openweathermap.org/data/2.5/onecall/timemachine?" \
               f"lat={lat}&lon={lon}&dt={start_time}&appid={weather_api_key}&units=metric&lang={lan}"
    w = requests.get(base_url).json()['current']
    base_url = f"http://api.openweathermap.org/data/2.5/air_pollution?" \
               f"lat={lat}&lon={lon}&appid={weather_api_key}"
    aq = requests.get(base_url).json()
    print(aq)
    print(start_time + 7200 > aq['list'][0]['dt'])
    air_conditions = f"Воздух: {aq['list'][0]['components']['so2']}(PM2.5), " \
                     f"{aq['list'][0]['components']['so2']}(SO₂), {aq['list'][0]['components']['no2']}(NO₂), " \
                     f"{aq['list'][0]['components']['nh3']}(NH₃).\n"
    print(air_conditions)
    trnsl = {'ru': ['Погода', 'по ощущениям', 'влажность', 'ветер', 'м/с', 'с'],
             'en': ['Weather', 'feels like', 'humidity', 'wind', 'm/s', 'from']}
    weather_desc = f"{trnsl[lan][0]}: {w['temp']:.1f}°C ({trnsl[lan][1]} {w['feels_like']:.0f}°C), " \
                   f"{trnsl[lan][2]} {w['humidity']}%, {trnsl[lan][3]} {w['wind_speed']:.1f}{trnsl[lan][4]} " \
                   f"({trnsl[lan][5]} {compass_direction(w['wind_deg'], lan)}), {w['weather'][0]['description']}.\n"
    payload = {'description': weather_desc + air_conditions + description}
    url = f'https://www.strava.com/api/v3/activities/{activity_id}'
    return requests.put(url, headers=get_headers(user_id), data=payload).json()


def db_add_athlete(token):
    pass
