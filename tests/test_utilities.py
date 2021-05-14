import re
import time

import manage_db
import utilities

LAT = 55.752388  # Moscow latitude default
LON = 37.716457  # Moscow longitude default
TIME = int(time.time()-3600)


def test_compass_direction():
    args_degree = [0, 7, 11, 12, 33, 85, 358, 722]
    expected = ['N', 'N', 'N', 'NNE', 'NNE', 'E', 'N', 'N']
    real_values = list(map(utilities.compass_direction, args_degree))
    assert real_values == expected


def test_is_app_subscribed():
    check_supscription = utilities.is_app_subscribed()
    assert isinstance(check_supscription, bool)


def test_get_weather_pictogram():
    icon = utilities.get_weather_icon(LAT, LON, TIME)
    assert isinstance(icon, str) and len(icon) == 1


def test_get_weather_description():
    settings = manage_db.DEFAULT_SETTINGS
    descr = utilities.get_weather_description(LAT, LON, TIME, settings)
    assert re.fullmatch(r'(\w+\s?){1,2}, 🌡.-?\d{1,2}°C \(по ощущениям -?\d{1,2}°C\), '
                        r'💦.\d{1,3}%, 💨.\d{1,2}м/с \(с \w{1,3}\).', descr)


def test_get_air_description():
    description = utilities.get_air_description(LAT, LON, lan='ru')
    assert re.fullmatch(r'\nВоздух . \d+\(PM2\.5\), \d+\(SO₂\), \d+\(NO₂\), \d+(\.\d)?\(NH₃\)\.', description)

