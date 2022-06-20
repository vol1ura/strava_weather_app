import calendar
import os
import time

import requests
from dotenv import load_dotenv

from utils import manage_db
from utils.strava_client import StravaClient

dotenv_path = os.path.join(os.path.dirname(__file__), '../.env')
load_dotenv(dotenv_path)

WIND_ARROWS = "↓↙←↖↑↗→↘↓"

def add_weather(athlete_id: int, activity_id: int):
    """Add weather conditions to description of Strava activity

    :param athlete_id: integer Strava athlete ID
    :param activity_id: Strava activity ID
    :return: status code
    """
    strava = StravaClient(athlete_id, activity_id)
    print('add_weather:strava:', strava)
    activity = strava.get_activity()
    print('add_weather:activity:', activity)

    # Activity type checking. Skip processing if activity is manual or indoor.
    if activity.get('manual', False) or activity.get('trainer', False) or activity.get('type', '') == 'VirtualRide':
        print(f"Activity with ID{activity_id} is manual created or indoor. Can't add weather info for it.")
        return  # ok, but no processing

    # Description of activity checking. Don't format this activity if it contains a weather data.
    description = activity.get('description')
    description = '' if description is None else description.rstrip() + '\n'
    if '°C' in description:
        print(f'Weather description for activity ID={activity_id} is already set.')
        return  # ok, but no processing

    # Check starting time of activity. Convert time to integer Unix time, GMT
    try:
        time_tuple = time.strptime(activity['start_date'], '%Y-%m-%dT%H:%M:%SZ')
        start_time = int(calendar.timegm(time_tuple))
    except (KeyError, ValueError):
        print(f'WARNING: {int(time.time())} - Bad date format for activity ID={activity_id}. Use current time.')
        start_time = int(time.time()) - 3600  # if some problems with activity start time let's use time a hour ago
    elapsed_time = activity.get('elapsed_time', 0)
    activity_time = start_time + elapsed_time // 2

    lat, lon = activity.get('start_latlng', [None, None])

    if not (lat and lon):
        print(f'WARNING: {int(time.time())} - No start geo position for ID={activity_id}, T={start_time}')
        return  # ok, but no processing

    settings = manage_db.get_settings(athlete_id)
    weather_description = get_weather_description(lat, lon, activity_time, settings)
    payload = {'description': description + weather_description}
    strava.modify_activity(payload)


def get_weather_description(lat, lon, w_time, s) -> str:
    """Get weather data using https://openweathermap.org/ API.

    :param lat: latitude
    :param lon: longitude
    :param w_time: time of requested weather data
    :param s: settings as named tuple with hum, wind and lan fields
    :return: string with history weather data
    """
    weather_api_key = os.environ.get('API_WEATHER_KEY')
    base_url = (
            f"http://api.openweathermap.org/data/2.5/onecall/timemachine?"
            f"lat={lat}&lon={lon}&dt={w_time}&appid={weather_api_key}&units={s.units}"
            "&only_current={true}"
    )
    response = requests.get(base_url)
    try:
        w = response.json()['current']
    except(KeyError, ValueError):
        print(f'Error! Weather request failed. User ID-{s.id} in ({lat},{lon}) at {w_time}.')
        print(f'OpenApiWeather response - code: {response.status_code}, body: {response.text}')
        return ''

    gust = lambda x: f"({x:0.1f} gust) "
    return (
        f"{w['temp']:0.1f}º{'F' if s.units=='imperial' else 'C'}"
        f", clouds: {w['clouds']}%"
        f", humidity: {w['humidity']}%"
        f", wind: {w['wind_speed']:0.1f}"
        f" {gust(w.get('wind_gust')) if w.get('wind_gust', None) != None else ''}"
        f"{'mph' if s.units=='imperial' else 'km/h'}"
        " " + WIND_ARROWS[round(w['wind_deg'] / 45)]
    )
