import pytest
from flask import request, session, url_for

import manage_db
from run import app as site


@pytest.fixture
def app():
    return site


def test_index_page(client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/' page is requested (GET)
    THEN check that the response is valid
    """
    response = client.get(url_for('index'))
    assert response.status_code == 200
    assert b"Weather conditions in your activities" in response.data
    assert b"Try it!" in response.data
    assert b"Connect with Strava" in response.data


def test_final_page_abort(client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/final/' page is requested (POST)
    THEN check that the response will be aborted
    """
    response = client.post(url_for('final'))
    assert response.status_code == 500


@pytest.mark.skip
def test_final_page(client, monkeypatch):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/final/' page is requested (POST)
    THEN check that the response will be aborted
    """
    # with app.test_request_context('/final/'):
    # session.modified = False
    session['id'] = 1
    session['athlete'] = 'TestUser'
    print(session, 'id' in session)
    monkeypatch.setattr(manage_db, 'add_settings', lambda arg: None)
    # assert request.args['v'] == '42'
    response = client.post(url_for('final'), data={'icon': 1})
    # print(response.data)
    assert response.status_code == 200
    # assert 'icon' in request.values


def test_auth_page_abort(client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/final/' page is requested (POST)
    THEN check that the response will be aborted
    """
    response = client.get(url_for('auth'))
    assert response.status_code == 500


def test_features_page(client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/features/' page is requested (GET)
    THEN check that the response is valid
    """
    response = client.get(url_for('features'))
    assert response.status_code == 200
    assert b"Features" in response.data
    assert b"Main features:" in response.data


def test_contacts_page(client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/contacts/' page is requested (GET)
    THEN check that the response is valid
    """
    response = client.get(url_for('contacts'))
    assert response.status_code == 200
    assert b"Contacts" in response.data
    assert b"https://www.strava.com/athletes/2843469" in response.data
    assert b"https://www.instagram.com/urka_runner/" in response.data
    assert b"https://github.com/vol1ura" in response.data


def test_http_404_handler(client):
    """
    GIVEN a Flask application configured for testing
    WHEN another page is requested (GET)
    THEN check that the response return 404 status code and render error page for it
    """
    response = client.get('/no_such_page/')
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
