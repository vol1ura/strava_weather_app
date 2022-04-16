import re
import time
from abc import abstractmethod, ABC

import pytest
import responses

from utils import weather, manage_db
from utils.exceptions import StravaAPIError

LAT = 55.752388  # Moscow latitude default
LNG = 37.716457  # Moscow longitude default
TIME = int(time.time()) - 3600

directions_to_try = [(0, 'N', 'С'), (7, 'N', 'С'), (11, 'N', 'С'), (12, 'NNE', 'ССВ'),
                     (33, 'NNE', 'ССВ'), (85, 'E', 'В'), (358, 'N', 'С'), (722, 'N', 'С')]
directions_ids = [f'{d[0]:<3}: {d[1]:>3}' for d in directions_to_try]


class MockResponse:
    """Class to mock http responses"""
    def __init__(self, ok=True):
        self.ok = ok

    @staticmethod
    def json():
        return {'current': {'weather': [{'description': 'weather description'}],
                            'temp': -15.34,  # to check sign
                            'feels_like': 22.63,  # to check roundness
                            'humidity': 64,
                            'wind_speed': 0.46,  # to test description with zero wind
                            'wind_deg': 241}
                }


class StravaClientMock(ABC):
    """Class to mock StravaClient class from utilities module"""
    def __init__(self, athlete_id, activity_id):
        self.athlete_id = athlete_id
        self.activity_id = activity_id

    @abstractmethod
    def get_activity(self):  # pragma: no cover
        pass

    @staticmethod
    def modify_activity(payload):
        return MockResponse(True) if isinstance(payload, dict) else MockResponse(False)


activities_to_try = [{'manual': True}, {'trainer': True}, {'type': 'VirtualRide'},
                     {'description': '0°C'}, {'description': ''}, {'start_latlng': [0, LNG]}, {'start_latlng': [LAT, 0]},
                     {'start_latlng': [LAT, LNG], 'start_date': '2021-06-03T12:48:06Z', 'name': 'icon'}]


@pytest.fixture(params=activities_to_try)
def strava_client_mock(request):
    class StravaClient(StravaClientMock):
        def get_activity(self):
            return request.param

    return StravaClient


@pytest.mark.parametrize('degree, direction_en, direction_ru', directions_to_try, ids=directions_ids)
def test_compass_direction(degree, direction_en, direction_ru):
    """Should return correct direction in english and russian"""
    assert weather.compass_direction(degree) == direction_en
    assert weather.compass_direction(degree, 'ru') == direction_ru


def test_get_weather_icon():
    icon = weather.get_weather_icon(LAT, LNG, TIME)
    print(icon)
    assert isinstance(icon, str)
    assert len(icon) == 1


def test_get_weather_icon_fail():
    assert weather.get_weather_icon(LAT, LNG, TIME - 6 * 25 * 3600) is None


def test_get_weather_description():
    settings = manage_db.DEFAULT_SETTINGS
    descr = weather.get_weather_description(LAT, LNG, TIME, settings)
    print(descr)
    assert re.fullmatch(r'(\w+\s?){1,3}, 🌡.-?\d{1,2}°C \(по ощущениям -?\d{1,2}°C\), '
                        r'💦.\d{1,3}%, 💨.\d{1,2}м/с \(с \w{1,3}\).', descr)


def test_get_weather_description_no_wind(monkeypatch):
    monkeypatch.setattr('requests.get', lambda *args: MockResponse())
    settings = manage_db.DEFAULT_SETTINGS
    descr = weather.get_weather_description(LAT, LNG, TIME, settings)
    print(descr)
    assert re.fullmatch(r'Weather description, 🌡.-15°C \(по ощущениям 23°C\), 💦.64%, 💨.0м/с.', descr)


def test_get_weather_description_failed():
    """openweatherapi supply only last 5 days weather data for free account, in other case we get exception"""
    settings = manage_db.DEFAULT_SETTINGS
    assert '' == weather.get_weather_description(LAT, LNG, TIME - 6 * 24 * 3600, settings)


@responses.activate
def test_get_weather_description_bad_response():
    """Case when something wrong with openweatherapi response"""
    responses.add(responses.GET, re.compile(r'http://api\.openweathermap\.org/data/2\.5/onecall/.*'), body='error')
    settings = manage_db.DEFAULT_SETTINGS
    assert '' == weather.get_weather_description(LAT, LNG, TIME, settings)


def test_get_air_description():
    description = weather.get_air_description(LAT, LNG, lan='ru')
    print(description)
    assert re.fullmatch(r'\nВоздух . \d+\(PM2\.5\), \d+\(SO₂\), \d+\(NO₂\), \d+(\.\d)?\(NH₃\)\.', description)


def test_add_weather_bad_activity(strava_client_mock, monkeypatch):
    """Run method for next cases:

    - activity is manual, trainer, VirtualRider;
    - description is already set;
    - absence of start coordinates;
    - icon in activity name is already set.
    In all this cases there is no needed to add the weather information to this activity."""

    monkeypatch.setattr(weather, 'StravaClient', strava_client_mock)
    monkeypatch.setattr(manage_db, 'get_settings', lambda *args: manage_db.DEFAULT_SETTINGS._replace(icon=1))
    monkeypatch.setattr(weather, 'get_weather_description', lambda *args: '')
    monkeypatch.setattr(weather, 'get_weather_icon', lambda *args: 'icon')
    assert weather.add_weather(0, 0) is None


@responses.activate
def test_add_weather_bad_response(monkeypatch, db_token, database):
    activity_id = 1
    athlete_tokens = db_token[0]
    responses.add(responses.GET, f'https://www.strava.com/api/v3/activities/{activity_id}', body='')
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)

    with pytest.raises(StravaAPIError):
        weather.add_weather(athlete_tokens.id, activity_id)
    assert len(responses.calls) == 1


settings_to_try = [manage_db.DEFAULT_SETTINGS._replace(icon=1), manage_db.DEFAULT_SETTINGS._replace(icon=0),
                   manage_db.DEFAULT_SETTINGS._replace(icon=0, aqi=0)]


@pytest.mark.parametrize('output_settings', settings_to_try)
def test_add_weather_success(monkeypatch, output_settings):
    """Run method for next cases:

    - activity is manual, trainer, VirtualRider;
    - description is already set;
    - absence of start coordinates;
    - icon in activity name is already set.
    In all this cases weather was successfully added."""

    class StravaClient(StravaClientMock):
        def get_activity(self):
            return {'start_latlng': [LAT, LNG], 'elapsed_time': 1,
                    'start_date': time.strftime('%Y-%m-%dT%H:%M:%SZ'), 'name': 'Activity name'}

    monkeypatch.setattr(weather, 'StravaClient', StravaClient)
    monkeypatch.setattr(manage_db, 'get_settings', lambda *args: output_settings)
    monkeypatch.setattr(weather, 'get_weather_description', lambda *args: '')
    monkeypatch.setattr(weather, 'get_air_description', lambda *args: '')
    monkeypatch.setattr(weather, 'get_weather_icon', lambda *args: 'icon')
    assert weather.add_weather(0, 0) is None
