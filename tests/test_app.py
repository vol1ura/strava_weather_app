import json
import os
import urllib.parse

import pytest
from flask import url_for

from utils import weather, manage_db, strava_helpers
from run import app as site, process_webhook_get


@pytest.fixture
def app():
    return site


def test_index_page(client):
    # GIVEN a Flask application configured for testing
    # WHEN the '/' page is requested (GET)
    response = client.get(url_for('index'))
    # THEN check that the response is valid
    assert response.status_code == 200
    assert b'Weather conditions in your activities' in response.data
    assert b'Try it!' in response.data
    assert b'Connect with Strava' in response.data


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
    monkeypatch.setattr(strava_helpers, 'get_tokens', lambda arg: auth_data_mock)
    response = client.get(url_for('auth'), query_string={'code': 1})
    assert response.status_code == 500


def test_auth_page(client, monkeypatch):
    # GIVEN a Flask application configured for testing
    auth_data_mock = {'athlete': {'firstname': 'Test', 'lastname': 'User', 'id': 1},
                      'access_token': 'test_AT', 'refresh_token': 'test_RT', 'expires_at': 'test_EA'}
    monkeypatch.setattr(strava_helpers, 'get_tokens', lambda arg: auth_data_mock)
    monkeypatch.setattr(manage_db, 'add_athlete', lambda arg: print)
    # WHEN the '/authorization_successful' page is requested (GET)
    response = client.get(url_for('auth'), query_string={'code': 1})
    # THEN check that the response is valid
    assert response.status_code == 200
    assert b'Test User' in response.data


def test_features_page(client):
    # GIVEN a Flask application configured for testing
    # WHEN the '/features/' page is requested (GET)
    response = client.get(url_for('features'))
    # THEN check that the response is valid
    assert response.status_code == 200
    assert b'Features' in response.data
    assert b'Main features:' in response.data


def test_contacts_page(client):
    # GIVEN a Flask application configured for testing
    # WHEN the '/contacts/' page is requested (GET)
    response = client.get(url_for('contacts'))
    # THEN check that the response is valid
    assert response.status_code == 200
    assert b'Contacts' in response.data
    assert b'https://www.strava.com/athletes/2843469' in response.data
    assert b'https://www.instagram.com/urka_runner/' in response.data
    assert b'https://github.com/vol1ura' in response.data


def test_webhook_page_post(client, monkeypatch):
    # GIVEN a Flask application configured for testing
    monkeypatch.setattr('run.process_webhook_post', lambda: None)
    # WHEN the '/webhook/' page is requested (POST)
    response = client.post(url_for('webhook'))
    # THEN check that the response is valid
    assert response.status_code == 200
    assert b'webhook ok' in response.data


def test_webhook_page_get(client, monkeypatch):
    # GIVEN a Flask application configured for testing
    payload_to_test = {'message': 'test'}
    monkeypatch.setattr('run.process_webhook_get', lambda: payload_to_test)
    # WHEN the '/webhook/' page is requested (GET)
    response = client.get(url_for('webhook'))
    # THEN check that the response is valid
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    assert json.loads(response.data.decode()) == payload_to_test


def test_process_webhook_get_subscribed(monkeypatch):
    monkeypatch.setattr(strava_helpers, 'is_app_subscribed', lambda: True)
    status = process_webhook_get()
    assert status == {'status': 'You are already subscribed'}


def test_process_webhook_get_subscription(monkeypatch, app):
    # GIVEN a Flask application configured for testing
    monkeypatch.setattr(strava_helpers, 'is_app_subscribed', lambda: False)
    monkeypatch.setenv('STRAVA_WEBHOOK_TOKEN', 'token_for_test')
    params = {'hub.mode': 'subscribe',
              'hub.verify_token': os.environ.get('STRAVA_WEBHOOK_TOKEN'),
              'hub.challenge': 'challenge_for_test'}
    values_url = urllib.parse.urlencode(params)
    # WHEN the '/webhook/?....params....' page is requested (GET)
    with app.test_request_context(f'/webhook/?{values_url}'):
        status = process_webhook_get()
    # THEN check that status for response is valid
    assert status == {'hub.challenge': 'challenge_for_test'}


def test_process_webhook_get_subscription_failed(monkeypatch, app):
    # GIVEN a Flask application configured for testing
    monkeypatch.setattr(strava_helpers, 'is_app_subscribed', lambda: False)
    monkeypatch.setenv('STRAVA_WEBHOOK_TOKEN', 'token_for_test')
    params = {'hub.mode': 'subscribe',
              'hub.verify_token': 'failed_token',
              'hub.challenge': 'challenge_for_test'}
    values_url = urllib.parse.urlencode(params)

    # WHEN the '/webhook/?....params....' page is requested (GET)
    with app.test_request_context(f'/webhook/?{values_url}'):
        status = process_webhook_get()
    # THEN check that status for response is valid
    assert status == {'error': 'verification tokens does not match'}

    # WHEN the '/webhook/' page is requested (GET)
    with app.test_request_context('/webhook/'):
        status = process_webhook_get()
    # THEN check that status for response is valid
    assert status == {'error': 'verification tokens does not match'}


data_to_try = [
    {'aspect_type': 'create', 'object_id': 10,
     'object_type': 'activity', 'owner_id': 1, 'updates': {}},
    {'aspect_type': 'update', 'object_id': 1,
     'object_type': 'athlete', 'owner_id': 1, 'updates': {'authorized': 'false'}},
    {'aspect_type': 'update', 'object_id': 10,
     'object_type': 'activity', 'owner_id': 1, 'updates': {'title': 'Some test'}}
]


@pytest.mark.parametrize('data', data_to_try)
def test_webhook_post(client, monkeypatch, data):
    # GIVEN a Flask application configured for testing
    monkeypatch.setattr(weather, 'add_weather', lambda *args: None)
    monkeypatch.setattr(manage_db, 'delete_athlete', lambda arg: None)
    # WHEN the '/webhook/' page is requested (GET)
    response = client.post(url_for('webhook'),
                           headers={'Content-Type': 'application/json'},
                           data=json.dumps(data))
    # THEN check that the response is valid
    assert response.status_code == 200
    assert response.data == b'webhook ok'


def test_http_404_handler(client):
    # GIVEN a Flask application configured for testing
    # WHEN another page is requested (GET)
    response = client.get('/no_such_page/')
    # THEN check that the response return 404 status code and render error page for it
    assert response.status_code == 404
    assert b'HTTP 404 Error' in response.data


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


def test_robots_txt_page(client):
    # GIVEN a Flask application configured for testing
    # WHEN the '/robots.txt' page is requested (GET)
    response = client.get('/robots.txt')
    # THEN check that the response is valid
    assert response.status_code == 200
    assert b'User-agent: *' in response.data
    assert b'Disallow: ' in response.data


def test_strava_api_errors_handler(client, monkeypatch):
    # GIVEN a Flask application configured for testing
    def exception_mock():
        from utils.exceptions import StravaAPIError
        raise StravaAPIError('error')
    # Suppose that exception raises when we process post request to webhook
    monkeypatch.setattr('run.process_webhook_post', lambda *args: exception_mock())

    # WHEN the '/webhook/' page is requested (POST)
    response = client.post(url_for('webhook'))
    # THEN check that the response is valid
    assert response.status_code == 500
    assert response.data == b'error'


def test_update_server_handler_success(client, monkeypatch):
    # GIVEN a Flask application configured for testing
    from utils import git_helpers

    def mock_is_valid_signature(sign, data):
        return sign == '12345abc' and data == b'test'

    monkeypatch.setattr(git_helpers, 'pull', lambda: None)
    monkeypatch.setattr(git_helpers, 'is_valid_signature', mock_is_valid_signature)
    # WHEN the '/update_server/' page is requested (POST)
    response = client.post(url_for('update_server'), headers={'X-Hub-Signature': '12345abc'}, data='test')
    # THEN check that the response is valid
    assert response.status_code == 202
    assert response.data == b'Server successfully updated'


def test_update_server_handler_wrong(client, monkeypatch):
    # GIVEN a Flask application configured for testing
    from utils import git_helpers

    def mock_is_valid_signature(sign, data):
        return not (sign == '12345abc' and data == b'test')

    monkeypatch.setattr(git_helpers, 'pull', lambda: None)
    monkeypatch.setattr(git_helpers, 'is_valid_signature', mock_is_valid_signature)
    # WHEN the '/update_server/' page is requested (POST)
    response = client.post(url_for('update_server'), headers={'X-Hub-Signature': '12345abc'}, data='test')
    # THEN check that the response is valid
    assert response.status_code == 406
    assert response.data == b'wrong signature'


def test_subscribers_handler(client, monkeypatch):
    # GIVEN a Flask application configured for testing
    monkeypatch.setattr(manage_db, 'get_subscribers_count', lambda: 1)
    # WHEN the '/subscribers' page is requested (GET)
    response = client.get('/subscribers')
    # THEN check that the response is valid
    assert response.status_code == 200
    assert json.loads(response.data.decode('utf-8')) == {'count': 1}
