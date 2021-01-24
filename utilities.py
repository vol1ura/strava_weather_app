import os
import time
import urllib.parse

import requests
from dotenv import load_dotenv

import manage_db

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


def get_headers(athlete_id):
    tokens = manage_db.get_athlete(athlete_id)
    tokens = update_tokens(tokens)
    manage_db.add_athlete(tokens)
    return {'Authorization': f"Bearer {tokens[1]}"}


def get_tokens(code):
    params = {
        "client_id": os.environ.get('STRAVA_CLIENT_ID'),
        "client_secret": os.environ.get('STRAVA_CLIENT_SECRET'),
        "code": code,
        "grant_type": "authorization_code"
    }
    return requests.post("https://www.strava.com/oauth/token", data=params).json()


def update_tokens(tokens):
    client_id = os.environ.get('STRAVA_CLIENT_ID')
    client_secret = os.environ.get('STRAVA_CLIENT_SECRET')
    if tokens[3] < time.time():
        params = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": tokens[2],
            "grant_type": "refresh_token"
        }
        refresh_response = requests.post("https://www.strava.com/oauth/token", data=params).json()
        try:
            return tokens[0], refresh_response['access_token'], \
                   refresh_response['refresh_token'], refresh_response['expires_at']
        except KeyError:
            print('Token refresh is failed.')
    return tokens


def make_link_to_get_code(redirect_url) -> str:
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
        return 'id' in response.json()[0]
    except (IndexError, KeyError):
        return False


def get_activity(athlete_id, activity_id):
    """Get information about activity

    :param athlete_id: integer Strava athlete ID
    :param activity_id: integer or string is a number
    :return: dictionary with activity data
    """
    url = f'https://www.strava.com/api/v3/activities/{activity_id}'
    return requests.get(url, headers=get_headers(athlete_id)).json()


def modify_activity(athlete_id, activity_id, payload: dict):
    """
    Method can change UpdatableActivity parameters such that description, name, type, gear_id.
    See https://developers.strava.com/docs/reference/#api-models-UpdatableActivity

    :param athlete_id: integer Strava athlete ID
    :param activity_id: integer Strava activity ID
    :param payload: dictionary with keys description, name, type, gear_id, trainer, commute
    :return: dictionary with updated activity parameters
    """
    url = f'https://www.strava.com/api/v3/activities/{activity_id}'
    return requests.put(url, headers=get_headers(athlete_id), data=payload)


def compass_direction(degree: int, lan='en') -> str:
    compass_arr = {'ru': ["С", "ССВ", "СВ", "ВСВ", "В", "ВЮВ", "ЮВ", "ЮЮВ",
                          "Ю", "ЮЮЗ", "ЮЗ", "ЗЮЗ", "З", "ЗСЗ", "СЗ", "ССЗ", "С"],
                   'en': ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]}
    return compass_arr[lan][int((degree % 360) / 22.5 + 0.5)]


def add_weather(athlete_id, activity_id):
    """Add weather conditions to description of Strava activity

    :param athlete_id: integer Strava athlete ID
    :param activity_id: Strava activity ID
    :return: status code
    """
    activity = get_activity(athlete_id, activity_id)

    # Activity type checking. Skip processing if activity is manual.
    try:
        if activity['manual']:
            print(f"Activity with ID{activity_id} is manual created. Can't add weather info for it.")
            return 3  # code 3 - ok, but no processing
    except KeyError:
        print(f'ERROR: - {time.time()} - No manual key for activity ID{activity_id}, athlete ID{athlete_id}')
        return 1  # code 1 - error

    # Description of activity checking. Don't format this activity if it contains a weather data.
    description = activity.get('description', '')
    description = '' if description is None else description.rstrip() + '\n'
    if ('Погода:' in description) or ('Weather:' in description):
        print(f'Weather description for activity ID{activity_id} is already set.')
        return 3  # code 3 - ok, but no processing

    # Check starting time of activity. Convert time to integer Unix time, GMT
    try:
        time_tuple = time.strptime(activity['start_date'], '%Y-%m-%dT%H:%M:%SZ')
        start_time = int(time.mktime(time_tuple))
    except (KeyError, ValueError):
        print(f'ERROR - {time.time()} - Bad data format for activity ID{activity_id}. Use current time.')
        start_time = int(time.time()) - 3600  # if some problems with activity start time les's use time a hour ago

    lat = activity.get('start_latitude', None)
    lon = activity.get('start_longitude', None)

    settings = manage_db.get_settings(athlete_id)

    if lat and lon:
        weather_description = get_weather_description(lat, lon, start_time, settings)
    else:
        print(f'WARNING - {time.time()} - No geo position for ID{activity_id}, ({lat}, {lon}), T={start_time}')
        return 3  # code 3 - ok, but no processing

    # Add air quality only if user set this option and time of activity uploading is appropriate!
    if settings.aqi and (start_time + activity['elapsed_time'] + 7200 > time.time()):
        air_conditions = get_air_description(lat, lon, settings.lan)
    else:
        air_conditions = ''
    payload = {'description': description + weather_description + air_conditions}
    result = modify_activity(athlete_id, activity_id, payload)
    return 0 if result.ok else 1


def get_weather_description(lat, lon, w_time: int, s):
    """Get weather data using https://openweathermap.org/ API.

    :param lat: latitude
    :param lon: longitude
    :param w_time: time of requested weather data
    :param s: settings as named tuple with hum, wind and lan fields
    :return: dictionary with history weather data
    """
    weather_api_key = os.environ.get('API_WEATHER_KEY')
    base_url = f"https://api.openweathermap.org/data/2.5/onecall/timemachine?" \
               f"lat={lat}&lon={lon}&dt={w_time}&appid={weather_api_key}&units=metric&lang={s.lan}"
    w = requests.get(base_url).json()['current']
    trnsl = {'ru': ['Погода', 'по ощущениям', 'влажность', 'ветер', 'м/с', 'с'],
             'en': ['Weather', 'feels like', 'humidity', 'wind', 'm/s', 'from']}
    description = f"{trnsl[s.lan][0]}: 🌡\xa0{w['temp']:.1f}°C ({trnsl[s.lan][1]} {w['feels_like']:.0f}°C), "
    description += f"💦\xa0{w['humidity']}%, " if s.hum else ""
    description += f"💨\xa0{w['wind_speed']:.1f}{trnsl[s.lan][4]} " \
                   f"({trnsl[s.lan][5]} {compass_direction(w['wind_deg'], s.lan)}), " if s.wind else ""
    description += f"{w['weather'][0]['description']}."
    return description


def get_air_description(lat, lon, lan='en'):
    """Get air quality data using https://openweathermap.org/ API.
    It gives only current AQ and appropriate only if activity synced not too late.

    :param lat: latitude
    :param lon: longitude
    :param lan: language 'ru' or 'en' by default
    :return: dictionary with air quality data
    """
    weather_api_key = os.environ.get('API_WEATHER_KEY')
    base_url = f"http://api.openweathermap.org/data/2.5/air_pollution?" \
               f"lat={lat}&lon={lon}&appid={weather_api_key}"
    aq = requests.get(base_url).json()
    # Air Quality Index: 1 = Good, 2 = Fair, 3 = Moderate, 4 = Poor, 5 = Very Poor
    aqi = ['😃', '🙂', '😐', '🙁', '😨'][aq['list'][0]['main']['aqi'] - 1]
    air = {'ru': 'Воздух', 'en': 'Air'}
    return f"\n{air[lan]} {aqi} {aq['list'][0]['components']['so2']}(PM2.5), " \
           f"{aq['list'][0]['components']['so2']}(SO₂), {aq['list'][0]['components']['no2']}(NO₂), " \
           f"{aq['list'][0]['components']['nh3']}(NH₃)."


# if __name__ == '__main__':
    # asub = is_app_subscribed()
    # print(asub)
    # lan = 'ru'
    # weather_api_key = os.environ.get('API_WEATHER_KEY')
    # lat = 55.75222  # Moscow latitude default
    # lon = 37.61556  # Moscow longitude default
    # start_time = int(time.time()) - 6000
    # base_url = f"https://api.openweathermap.org/data/2.5/onecall/timemachine?" \
    #            f"lat={lat}&lon={lon}&dt={start_time}&appid={weather_api_key}&units=metric&lang={lan}"
    # w = requests.get(base_url).json()['current']
    # pprint(w)
