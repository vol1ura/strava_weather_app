import os
import requests

from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from urllib.parse import urlencode

from utils import manage_db
from utils.strava_client import StravaClient

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))


BASE_URL = 'https://api.weatherapi.com/v1'
API_KEY = os.environ.get('API_WEATHER_KEY')
PHRASES = {
    'ru': ['по ощущениям', 'км/ч', 'с'],
    'en': ['feels like', 'kph', 'from']
}
ICONS = {
    1000: '☀️', 1003: '🌤', 1006: '☁', 1006: '☁', 1030: '😶‍🌫️', 1135: '☁️', 1147: '☁️', 1066: '🌨',
    1069: '🌨', 1063: '🌦', 1072: '🌨', 1150: '🌧', 1153: '🌧', 1168: '🌧', 1169: '🌧', 1087: '🌩',
    1114: '🌨', 1117: '🌨', 1180: '🌦', 1183: '🌦', 1186: '🌦', 1189: '🌧', 1192: '🌧', 1195: '🌧',
    1198: '🌧', 1201: '🌧', 1204: '🌨', 1207: '🌨', 1210: '🌨', 1213: '🌨', 1216: '🌨', 1219: '🌨',
    1222: '🌨', 1237: '🌨', 1240: '🌧', 1243: '🌧', 1246: '🌧', 1249: '🌧', 1252: '🌨', 1255: '🌨',
    1258: '🌨', 1261: '🌨', 1264: '🌨', 1273: '🌩', 1276: '⛈️', 1279: '🌨', 1282: '🌨'
}


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
    activity = strava.get_activity

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
        start_time = datetime.strptime(activity['start_date_local'], '%Y-%m-%dT%H:%M:%SZ')
    except (KeyError, ValueError):
        print(f'WARNING: Bad date format for activity ID={activity_id}. Use current time.')
        # if some problems with activity start time let's use time a hour ago
        start_time = datetime.now() - timedelta(hours=1)
    elapsed_time = timedelta(seconds=activity.get('elapsed_time', 0))
    activity_time = start_time + elapsed_time // 2  # in the middle of activity

    try:
        lat, lon = activity['start_latlng']
    except (KeyError, ValueError):
        print(f'WARNING: No start geo position for activity ID={activity_id}, T={start_time}')
        return  # ok, but no processing

    settings = manage_db.get_settings(athlete_id)

    if settings.icon:
        activity_title = activity.get('name')
        icon = get_weather_icon(lat, lon, activity_time)
        if not icon or activity_title.startswith(icon):
            return  # maybe ok, no processing
        payload = {'name': icon + ' ' + activity_title}
    else:
        weather_description = get_weather_description(lat, lon, activity_time, settings)
        # Add air quality only if user set this option and time of activity uploading is appropriate!
        appropriate_time = \
            datetime.strptime(activity['start_date'], '%Y-%m-%dT%H:%M:%SZ') + elapsed_time + timedelta(hours=2)
        if settings.aqi and (appropriate_time > datetime.now(timezone.utc).replace(tzinfo=None)):
            air_conditions = get_air_description(lat, lon, settings.lan)
        else:
            air_conditions = ''
        payload = {'description': description + weather_description + air_conditions}
    strava.modify_activity(payload)


def weather_info(params: dict) -> dict:
    params['key'] = API_KEY
    response = requests.get(f"{BASE_URL}/history.json?{urlencode(params)}")
    return response.json()['forecast']['forecastday'][0]['hour'][0]


def air_info(params: dict) -> dict:
    params['key'] = API_KEY
    params['aqi'] = 'yes'
    response = requests.get(f"{BASE_URL}/current.json?{urlencode(params)}")
    return response.json()['current']['air_quality']


def get_weather_description(lat, lon, timestamp, s) -> str:
    """Get weather data using https://www.weatherapi.com/ API.

    :param lat: latitude
    :param lon: longitude
    :param timestamp: time of requested weather
    :param s: settings as named tuple with hum, wind and lan fields
    :return: string with history weather data
    """
    try:
        w = weather_info(
            {
                'q': f"{lat},{lon}",
                'dt': timestamp.strftime('%Y-%m-%d'),
                'hour': timestamp.hour,
                'lang': s.lan
            }
        )
    except (KeyError, ValueError):
        print(f'Error! Weather request failed. User ID-{s.id} in ({lat},{lon}) at {timestamp}.')
        return ''
    t = PHRASES[s.lan]
    feels_like = format(w['feelslike_c'], '.0f')
    description = f"{w['condition']['text'].capitalize()}, " \
                  f"🌡\xa0{w['temp_c']:.0f}°C ({t[0]} {'0' if feels_like == '-0' else feels_like}°C)"
    description += f", 💦\xa0{w['humidity']}%" if s.hum else ""
    if s.wind:
        description += f", 💨\xa0{w['wind_kph']:.0f}{t[1]}"
        if f"{w['wind_kph']:.0f}" != '0':
            description += f" ({t[2]} {compass_direction(w['wind_degree'], s.lan)})."
        else:
            description += '.'
    return description


def get_air_description(lat, lon, lan='en') -> str:
    """Get air quality data using https://openweathermap.org/ API.
    It gives only current AQ and appropriate only if activity synced not too late.

    :param lat: latitude
    :param lon: longitude
    :param lan: language 'ru' or 'en' by default
    :return: string with air quality data
    """
    try:
        aq = air_info({'q': f'{lat},{lon}', 'lang': lan})
    except KeyError:
        print(f'ERROR: failed to GET air info at ({lat},{lon})')
        return ''
    # Air Quality Index: 1 = Good, 2 = Moderate, 3 = Unhealthy for sensitive, 4 = Unhealthy, 5 = Very Poor, 6 = Hazardous
    aqi = ['😃', '🙂', '😐', '🙁', '😨', '🤢'][aq['us-epa-index'] - 1]
    air = {'ru': 'Воздух', 'en': 'Air'}
    return f"\n{air[lan]} {aqi} {aq['pm2_5']:.1f}(PM2.5), " \
           f"{aq['so2']:.0f}(SO₂), {aq['no2']:.0f}(NO₂), " \
           f"{aq['o3']:.0f}(O₃), {aq['co']:.0f}(CO)."


def get_weather_icon(lat, lon, timestamp):
    """Get weather icon using https://openweathermap.org/ API.
    See icon codes on https://openweathermap.org/weather-conditions

    :param lat: latitude
    :param lon: longitude
    :param timestamp: time of requested weather data
    :return: emoji with weather
    """
    try:
        icon_code = weather_info(
            {
                'q': f'{lat},{lon}',
                'dt': timestamp.strftime('%Y-%m-%d'),
                'hour': timestamp.hour
            }
        )['condition']['code']
        return ICONS[icon_code]
    except (KeyError, ValueError):
        print(f'ERROR: failed to GET weather in ({lat},{lon}) at {timestamp}.')
        return
