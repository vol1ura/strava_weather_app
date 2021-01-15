from dotenv import load_dotenv
import manage_db
import os
import requests
import time
import urllib.parse


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
    exp_time = tokens[3] - int(time.time())  # TODO remove this is only for debug
    hours = exp_time // 3600
    mins = (exp_time - 3600 * hours) // 60
    s = f"{hours}h " if hours != 0 else ""
    print(f"Token expires after {s}{mins} min")
    return tokens


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


def is_app_subscribed():
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


def add_weather(athlete_id, activity_id, lan='en'):  # TODO split function into two: get_weather and add_description
    """Add weather conditions to description of Strava activity

    :param athlete_id: integer Strava athlete ID
    :param activity_id: Strava activity ID
    :param lan: language 'ru' or 'en' by default
    :return: status code
    """
    weather_api_key = os.environ.get('API_WEATHER_KEY')
    activity = get_activity(athlete_id, activity_id)
    if activity['manual']:
        print(f"Activity with ID{activity_id} is manual created. Can't add weather info for it.")
        return 3  # code 3 - ok, but no processing
    description = activity.get('description', '')
    description = '' if description is None else description
    if ('Погода:' in description) or ('Weather:' in description):
        print(f'Weather description for activity ID{activity_id} is already set.')
        return 3
    try:
        lat = activity['start_latitude']
        lon = activity['start_longitude']
    except KeyError:
        lat = 55.75222  # Moscow latitude default
        lon = 37.61556  # Moscow longitude default
    try:
        time_tuple = time.strptime(activity['start_date'], '%Y-%m-%dT%H:%M:%SZ')
        start_time = int(time.mktime(time_tuple))
    except (KeyError, ValueError):
        print(f'Bad data format for activity ID{activity_id}. Use current time.')  # TODO: remove after debugging
        start_time = int(time.time()) - 3 * 3600
    base_url = f"https://api.openweathermap.org/data/2.5/onecall/timemachine?" \
               f"lat={lat}&lon={lon}&dt={start_time}&appid={weather_api_key}&units=metric&lang={lan}"
    w = requests.get(base_url).json()['current']
    base_url = f"http://api.openweathermap.org/data/2.5/air_pollution?" \
               f"lat={lat}&lon={lon}&appid={weather_api_key}"
    aq = requests.get(base_url).json()  # it gives only current AQ and appropriate only if activity synced not too late
    if start_time + activity['elapsed_time'] + 7200 > aq['list'][0]['dt']:  # Add air quality only if time appropriate!
        # Air Quality Index: 1 = Good, 2 = Fair, 3 = Moderate, 4 = Poor, 5 = Very Poor
        aqi = ['😃', '🙂', '😐', '🙁', '😨'][aq['list'][0]['main']['aqi'] - 1]
        air = {'ru': 'Воздух', 'en': 'Air'}
        air_conditions = f"{air[lan]} {aqi} {aq['list'][0]['components']['so2']}(PM2.5), " \
                         f"{aq['list'][0]['components']['so2']}(SO₂), {aq['list'][0]['components']['no2']}(NO₂), " \
                         f"{aq['list'][0]['components']['nh3']}(NH₃).\n"
    else:
        air_conditions = ''
    trnsl = {'ru': ['Погода', 'по ощущениям', 'влажность', 'ветер', 'м/с', 'с'],
             'en': ['Weather', 'feels like', 'humidity', 'wind', 'm/s', 'from']}
    weather_desc = f"{trnsl[lan][0]}: 🌡 {w['temp']:.1f}°C ({trnsl[lan][1]} {w['feels_like']:.0f}°C), " \
                   f"💦 {w['humidity']}%, 💨 {w['wind_speed']:.1f}{trnsl[lan][4]} " \
                   f"({trnsl[lan][5]} {compass_direction(w['wind_deg'], lan)}), {w['weather'][0]['description']}.\n"
    payload = {'description': weather_desc + air_conditions + description}
    result = modify_activity(athlete_id, activity_id, payload)
    return 0 if result.ok else 1
