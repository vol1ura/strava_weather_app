import re
import time
from abc import abstractmethod, ABC

import pytest

import manage_db
import utilities

LAT = 55.752388  # Moscow latitude default
LON = 37.716457  # Moscow longitude default
TIME = int(time.time() - 3600)

directions_to_try = [(0, 'N', 'С'), (7, 'N', 'С'), (11, 'N', 'С'), (12, 'NNE', 'ССВ'),
                     (33, 'NNE', 'ССВ'), (85, 'E', 'В'), (358, 'N', 'С'), (722, 'N', 'С')]
directions_ids = [f'{d[0]:<3}: {d[1]:>3}' for d in directions_to_try]


class Result:
    """Class to mock http requests"""
    def __init__(self, ok):
        self.ok = ok

    def json(self):
        return


class StravaClientMock(ABC):
    """Class to mock StravaClient class from utilities module"""
    def __init__(self, athlete_id, activity_id):
        self.athlete_id = athlete_id
        self.activity_id = activity_id

    @abstractmethod
    def get_activity(self):
        return

    @staticmethod
    def modify_activity(payload):
        return Result(True) if isinstance(payload, dict) else Result(False)


activities_to_try = [{'manual': True}, {'trainer': True}, {'type': 'VirtualRide'},
                     {'description': '0°C'}, {'description': ''}, {'start_latitude': 0}, {'start_longitude': 0},
                     {'start_latitude': LAT, 'start_longitude': LON,
                      'start_date': '2021-06-03T12:48:06Z', 'name': 'icon'}]


@pytest.fixture(params=activities_to_try)
def strava_client_mock(request):
    class StravaClient(StravaClientMock):
        def get_activity(self):
            return request.param

    return StravaClient


@pytest.mark.parametrize('degree, direction_en, direction_ru', directions_to_try, ids=directions_ids)
def test_compass_direction(degree, direction_en, direction_ru):
    """Should return correct direction in english and russian"""
    assert utilities.compass_direction(degree) == direction_en
    assert utilities.compass_direction(degree, 'ru') == direction_ru


def test_is_app_subscribed():
    """Should return boolean"""
    check_supscription = utilities.is_app_subscribed()
    assert isinstance(check_supscription, bool)


def test_get_weather_icon():
    icon = utilities.get_weather_icon(LAT, LON, TIME)
    print(icon)
    assert isinstance(icon, str)
    assert len(icon) == 1


def test_get_weather_description():
    settings = manage_db.DEFAULT_SETTINGS
    descr = utilities.get_weather_description(LAT, LON, TIME, settings)
    print(descr)
    assert re.fullmatch(r'(\w+\s?){1,3}, 🌡.-?\d{1,2}°C \(по ощущениям -?\d{1,2}°C\), '
                        r'💦.\d{1,3}%, 💨.\d{1,2}м/с \(с \w{1,3}\).', descr)


def test_get_weather_description_fail():
    """openweatherapi supply only last 5 days weather data for free account"""
    settings = manage_db.DEFAULT_SETTINGS
    descr = utilities.get_weather_description(LAT, LON, TIME - 6 * 24 * 3600, settings)
    assert descr == ''


def test_get_air_description():
    description = utilities.get_air_description(LAT, LON, lan='ru')
    print(description)
    assert re.fullmatch(r'\nВоздух . \d+\(PM2\.5\), \d+\(SO₂\), \d+\(NO₂\), \d+(\.\d)?\(NH₃\)\.', description)


def test_add_weather_bad_activity(strava_client_mock, monkeypatch):
    """Return 3 if:

    - activity is manual, trainer, VirtualRider;
    - description is already set;
    - absence of start coordinates;
    - icon in activity name is already set.
    In all this cases there is no needed to add the weather information to this activity."""

    monkeypatch.setattr(utilities, 'StravaClient', strava_client_mock)
    monkeypatch.setattr(manage_db, 'get_settings', lambda *args: manage_db.DEFAULT_SETTINGS._replace(icon=1))
    monkeypatch.setattr(utilities, 'get_weather_description', lambda *args: '')
    monkeypatch.setattr(utilities, 'get_weather_icon', lambda *args: 'icon')
    assert utilities.add_weather(0, 0) == 3


settings_to_try = [manage_db.DEFAULT_SETTINGS._replace(icon=1), manage_db.DEFAULT_SETTINGS._replace(icon=0),
                   manage_db.DEFAULT_SETTINGS._replace(icon=0, aqi=0)]


@pytest.mark.parametrize('output_settings', settings_to_try)
def test_add_weather_success(monkeypatch, output_settings):
    """Return 0 if:

    - activity is manual, trainer, VirtualRider;
    - description is already set;
    - absence of start coordinates;
    - icon in activity name is already set.
    In all this cases all is OK."""
    class StravaClient(StravaClientMock):
        def get_activity(self):
            return {'start_latitude': LAT, 'start_longitude': LON, 'elapsed_time': 1,
                    'start_date': time.strftime('%Y-%m-%dT%H:%M:%SZ'), 'name': 'Activity name'}

    monkeypatch.setattr(utilities, 'StravaClient', StravaClient)
    monkeypatch.setattr(manage_db, 'get_settings', lambda *args: output_settings)
    monkeypatch.setattr(utilities, 'get_weather_description', lambda *args: '')
    monkeypatch.setattr(utilities, 'get_air_description', lambda *args: '')
    monkeypatch.setattr(utilities, 'get_weather_icon', lambda *args: 'icon')
    assert utilities.add_weather(0, 0) == 0
