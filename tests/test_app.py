import pytest
from flask import url_for

import manage_db
import utilities
from run import app as site


@pytest.fixture
def app():
    return site


def test_index_page(client):
    # GIVEN a Flask application configured for testing
    # WHEN the '/' page is requested (GET)
    response = client.get(url_for('index'))
    # THEN check that the response is valid
    assert response.status_code == 200
    assert b"Weather conditions in your activities" in response.data
    assert b"Try it!" in response.data
    assert b"Connect with Strava" in response.data


def test_final_page_abort(client):
    # GIVEN a Flask application configured for testing
    # WHEN the '/final/' page is requested (POST)
    response = client.post(url_for('final'))
    # THEN check that the response will be aborted
    assert response.status_code == 500


parameters_to_try = [
    {'icon': 1}, {'icon': 1, 'lan': 'en'}, {'wind': 2, 'humidity': 3, 'aqi': 4},
    {'wind': 2, 'humidity': 3, 'aqi': 4, 'lan': 'en'},
    {'icon': 1, 'wind': 2, 'humidity': 3, 'aqi': 4, 'lan': 'ru'},
    {'lan': 'en', 'wind': 1, 'aqi': 2, 'humidity': 3},
    {'humidity': 1}, {'aqi': 1, 'humidity': 2, 'lan': 'en'}, {'aqi': 4, 'lan': 'test'}
]


@pytest.mark.parametrize('params_from_auth', parameters_to_try)
def test_final_page(client, monkeypatch, capsys, params_from_auth):
    # GIVEN a Flask application configured for testing
    with client.session_transaction() as session:
        session['id'] = 1
        session['athlete'] = 'Test User'
    monkeypatch.setattr(manage_db, 'add_settings', print)
    # WHEN the '/final/' page is requested (POST)
    response = client.post(url_for('final'), data=params_from_auth)
    out, err = capsys.readouterr()
    # THEN check that the response is valid and settings are correct
    assert out == "Settings(id=1, " \
                  f"icon={1 if 'icon' in params_from_auth else 0}, " \
                  f"hum={1 if 'humidity' in params_from_auth else 0}, " \
                  f"wind={1 if 'wind' in params_from_auth else 0}, " \
                  f"aqi={1 if 'aqi' in params_from_auth else 0}, " \
                  f"lan='{'ru' if 'lan' not in params_from_auth else params_from_auth['lan']}')\n"
    assert response.status_code == 200
    assert b'Test User' in response.data
    assert b'Success!!!' in response.data


def test_auth_page_abort(client):
    # GIVEN a Flask application configured for testing
    # WHEN the '/final/' page is requested (POST)
    response = client.get(url_for('auth'))
    # THEN check that the response will be aborted
    assert response.status_code == 500


def test_auth_page_wrong_keys(client, monkeypatch):
    auth_data_mock = {}
    monkeypatch.setattr(utilities, 'get_tokens', lambda arg: auth_data_mock)
    response = client.get(url_for('auth'), query_string={'code': 1})
    # assert request.args['code'] == 1
    assert response.status_code == 500


def test_auth_page(client, monkeypatch):
    # GIVEN a Flask application configured for testing
    auth_data_mock = {'athlete': {'firstname': 'Test', 'lastname': 'User', 'id': 1},
                      'access_token': 'test_AT', 'refresh_token': 'test_RT', 'expires_at': 'test_EA'}
    monkeypatch.setattr(utilities, 'get_tokens', lambda arg: auth_data_mock)
    monkeypatch.setattr(manage_db, 'add_athlete', lambda arg: print)
    # WHEN the '/authorization_successful' page is requested (GET)
    response = client.get(url_for('auth'), query_string={'code': 1})
    # assert request.args['code'] == 1
    # THEN check that the response is valid
    assert response.status_code == 200
    assert b'Test User' in response.data


def test_features_page(client):
    # GIVEN a Flask application configured for testing
    # WHEN the '/features/' page is requested (GET)
    response = client.get(url_for('features'))
    # THEN check that the response is valid
    assert response.status_code == 200
    assert b"Features" in response.data
    assert b"Main features:" in response.data


def test_contacts_page(client):
    # GIVEN a Flask application configured for testing
    # WHEN the '/contacts/' page is requested (GET)
    response = client.get(url_for('contacts'))
    # THEN check that the response is valid
    assert response.status_code == 200
    assert b"Contacts" in response.data
    assert b"https://www.strava.com/athletes/2843469" in response.data
    assert b"https://www.instagram.com/urka_runner/" in response.data
    assert b"https://github.com/vol1ura" in response.data


def test_http_404_handler(client):
    # GIVEN a Flask application configured for testing
    # WHEN another page is requested (GET)
    response = client.get('/no_such_page/')
    # THEN check that the response return 404 status code and render error page for it
    assert response.status_code == 404
    assert b"HTTP 404 Error" in response.data


def test_http_405_handler(client):
    """
    GIVEN a Flask application configured for testing
    WHEN unallowed method is requested
    THEN check that the response will be redirected with status code 302
    """
    response = client.post(url_for('index'))  # POST when allowed only GET
    assert response.status_code == 302
    response = client.get(url_for('final'))  # GET when allowed only POST
    assert response.status_code == 302
