import os
import time
import urllib.parse

import requests
from dotenv import load_dotenv

import manage_db

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


class StravaClient:
    def __init__(self, athlete_id, activity_id):
        self.__athlete_id = athlete_id
        self.__activity_id = activity_id
        self.__session = requests.Session()
        tokens = manage_db.get_athlete(athlete_id)
        tokens = self._update_tokens(tokens)
        manage_db.add_athlete(tokens)
        self.__headers = {'Authorization': f"Bearer {tokens.access_token}"}

    def _update_tokens(self, tokens):
        if tokens.expires_at < time.time():
            params = {
                "client_id": os.environ.get('STRAVA_CLIENT_ID'),
                "client_secret": os.environ.get('STRAVA_CLIENT_SECRET'),
                "refresh_token": tokens.refresh_token,
                "grant_type": "refresh_token"
            }
            refresh_response = self.__session.post("https://www.strava.com/oauth/token", data=params).json()
            try:
                return manage_db.Tokens(tokens.id, refresh_response['access_token'],
                                        refresh_response['refresh_token'], refresh_response['expires_at'])
            except KeyError:
                print('Token refresh is failed.')
        return tokens

    def get_activity(self):
        """Get information about activity

        :return: dictionary with activity data
        """
        url = f'https://www.strava.com/api/v3/activities/{self.__activity_id}'
        return self.__session.get(url, headers=self.__headers).json()

    def modify_activity(self, payload: dict):
        """Method can change UpdatableActivity parameters such that description, name, type, gear_id.
        See https://developers.strava.com/docs/reference/#api-models-UpdatableActivity

        :param payload: dictionary with keys description, name, type, gear_id, trainer, commute
        :return: dictionary with updated activity parameters
        """
        url = f'https://www.strava.com/api/v3/activities/{self.__activity_id}'
        return self.__session.put(url, headers=self.__headers, data=payload)


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
        return 'id' in response.json()[0]
    except (IndexError, KeyError):
        return False


def compass_direction(degree: int, lan='en') -> str:
    compass_arr = {'ru': ["С", "ССВ", "СВ", "ВСВ", "В", "ВЮВ", "ЮВ", "ЮЮВ",
                          "Ю", "ЮЮЗ", "ЮЗ", "ЗЮЗ", "З", "ЗСЗ", "СЗ", "ССЗ", "С"],
                   'en': ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]}
    return compass_arr[lan][int((degree % 360) / 22.5 + 0.5)]


def add_weather(athlete_id: int, activity_id: int):
    """Add weather conditions to description of Strava activity

    :param athlete_id: integer Strava athlete ID
    :param activity_id: Strava activity ID
    :return: status code
    """
    strava = StravaClient(athlete_id, activity_id)
    activity = strava.get_activity()

    # Activity type checking. Skip processing if activity is manual or indoor.
    if activity.get('manual', False) or activity.get('trainer', False) or activity.get('type', '') == 'VirtualRide':
        print(f"Activity with ID{activity_id} is manual created or indoor. Can't add weather info for it.")
        return 3  # code 3 - ok, but no processing

    # Description of activity checking. Don't format this activity if it contains a weather data.
    description = activity.get('description', '')
    description = '' if description is None else description.rstrip() + '\n'
    if '°C' in description:
        print(f'Weather description for activity ID{activity_id} is already set.')
        return 3  # code 3 - ok, but no processing

    # Check starting time of activity. Convert time to integer Unix time, GMT
    try:
        time_tuple = time.strptime(activity['start_date'], '%Y-%m-%dT%H:%M:%SZ')
        start_time = int(time.mktime(time_tuple))
    except (KeyError, ValueError):
        print(f'WARNING - {int(time.time())} - Bad date format for activity ID{activity_id}. Use current time.')
        start_time = int(time.time()) - 3600  # if some problems with activity start time let's use time a hour ago
    elapsed_time = activity.get('elapsed_time', 0)
    activity_time = start_time + elapsed_time // 2

    lat = activity.get('start_latitude', None)
    lon = activity.get('start_longitude', None)

    if not (lat and lon):
        print(f'WARNING - {int(time.time())} - No geo position for ID{activity_id}, ({lat}, {lon}), T={start_time}')
        return 3  # code 3 - ok, but no processing

    settings = manage_db.get_settings(athlete_id)

    if settings.icon:
        activity_title = activity.get('name')
        icon = get_weather_icon(lat, lon, activity_time)
        if activity_title.startswith(icon):
            return 3
        payload = {'name': icon + ' ' + activity_title}
        result = strava.modify_activity(payload)
        return 0 if result.ok else 1

    weather_description = get_weather_description(lat, lon, activity_time, settings)

    # Add air quality only if user set this option and time of activity uploading is appropriate!
    if settings.aqi and (start_time + activity['elapsed_time'] + 7200 > time.time()):
        air_conditions = get_air_description(lat, lon, settings.lan)
    else:
        air_conditions = ''
    payload = {'description': description + weather_description + air_conditions}
    result = strava.modify_activity(payload)
    return 0 if result.ok else 1


def get_weather_description(lat, lon, w_time, s) -> str:
    """Get weather data using https://openweathermap.org/ API.

    :param lat: latitude
    :param lon: longitude
    :param w_time: time of requested weather data
    :param s: settings as named tuple with hum, wind and lan fields
    :return: string with history weather data
    """
    weather_api_key = os.environ.get('API_WEATHER_KEY')
    base_url = "https://api.openweathermap.org/data/2.5/onecall/timemachine?" \
               f"lat={lat}&lon={lon}&dt={w_time}&appid={weather_api_key}&units=metric&lang={s.lan}"
    try:
        w = requests.get(base_url).json()['current']
    except KeyError:
        print(f'ERROR - {time.time()} - Weather request failed. User ID-{s.id} in ({lat},{lon}) at {w_time}.')
        return ''
    trnsl = {'ru': ['Погода', 'по ощущениям', 'влажность', 'ветер', 'м/с', 'с'],
             'en': ['Weather', 'feels like', 'humidity', 'wind', 'm/s', 'from']}
    description = f"{w['weather'][0]['description'].capitalize()}, " \
                  f"🌡\xa0{w['temp']:.0f}°C ({trnsl[s.lan][1]} {w['feels_like']:.0f}°C)"
    description += f", 💦\xa0{w['humidity']}%" if s.hum else ""
    description += f", 💨\xa0{w['wind_speed']:.0f}{trnsl[s.lan][4]} " \
                   f"({trnsl[s.lan][5]} {compass_direction(w['wind_deg'], s.lan)})." if s.wind else "."
    return description


def get_air_description(lat, lon, lan='en') -> str:
    """Get air quality data using https://openweathermap.org/ API.
    It gives only current AQ and appropriate only if activity synced not too late.

    :param lat: latitude
    :param lon: longitude
    :param lan: language 'ru' or 'en' by default
    :return: string with air quality data
    """
    weather_api_key = os.environ.get('API_WEATHER_KEY')
    base_url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={weather_api_key}"
    aq = requests.get(base_url).json()
    # Air Quality Index: 1 = Good, 2 = Fair, 3 = Moderate, 4 = Poor, 5 = Very Poor
    aqi = ['😃', '🙂', '😐', '🙁', '😨'][aq['list'][0]['main']['aqi'] - 1]
    air = {'ru': 'Воздух', 'en': 'Air'}
    return f"\n{air[lan]} {aqi} {aq['list'][0]['components']['pm2_5']:.0f}(PM2.5), " \
           f"{aq['list'][0]['components']['so2']:.0f}(SO₂), {aq['list'][0]['components']['no2']:.0f}(NO₂), " \
           f"{aq['list'][0]['components']['nh3']:.1f}(NH₃)."


def get_weather_icon(lat, lon, w_time):
    """Get weather icon using https://openweathermap.org/ API.
    See icon codes on https://openweathermap.org/weather-conditions

    :param lat: latitude
    :param lon: longitude
    :param w_time: time of requested weather data
    :return: emoji with weather
    """
    icons = {'01d': '🌄', '01n': '🌙', '02d': '🌤', '02n': '☁', '03d': '☁', '03n': '☁',
             '04d': '🌥', '04n': '🌥', '50d': '🌫', '50n': '🌫', '13d': '🌨', '13n': '🌨',
             '10n': '🌧', '10d': '🌦', '09d': '🌧', '09n': '🌧', '11d': '⛈', '11n': '⛈'}
    weather_api_key = os.environ.get('API_WEATHER_KEY')
    base_url = "https://api.openweathermap.org/data/2.5/onecall/timemachine?" \
               f"lat={lat}&lon={lon}&dt={w_time}&appid={weather_api_key}&units=metric&lang=en"
    try:
        icon_code = requests.get(base_url).json()['current']['weather'][0]['icon']
        return icons[icon_code]
    except KeyError:
        print(f'ERROR - {time.time()} - Weather request failed in ({lat},{lon}) at {w_time}.')
        return ''
