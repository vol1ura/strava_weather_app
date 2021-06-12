import pytest
from flask import request, session

from run import app


def test_index_page():
    """
    GIVEN a Flask application configured for testing
    WHEN the '/' page is requested (GET)
    THEN check that the response is valid
    """
    app.testing = True
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200
        assert b"Weather conditions in your activities" in response.data
        assert b"Try it!" in response.data
        assert b"Connect with Strava" in response.data


def test_final_page_abort():
    """
    GIVEN a Flask application configured for testing
    WHEN the '/final/' page is requested (POST)
    THEN check that the response will be aborted
    """
    app.testing = True
    with app.test_client() as client:
        response = client.post('/final/')
        assert response.status_code == 500


@pytest.mark.skip
def test_final_page():
    """
    GIVEN a Flask application configured for testing
    WHEN the '/final/' page is requested (POST)
    THEN check that the response will be aborted
    """
    app.testing = True
    with app.test_client() as client:
        session['id'] = 1
        # assert request.args['v'] == '42'
        response = client.post('/final/')
        assert response.status_code == 200


def test_features_page():
    """
    GIVEN a Flask application configured for testing
    WHEN the '/features/' page is requested (GET)
    THEN check that the response is valid
    """
    app.testing = True
    with app.test_client() as client:
        response = client.get('/features/')
        assert response.status_code == 200
        assert b"Features" in response.data
        assert b"Main features:" in response.data


def test_contacts_page():
    """
    GIVEN a Flask application configured for testing
    WHEN the '/contacts/' page is requested (GET)
    THEN check that the response is valid
    """
    app.testing = True
    with app.test_client() as client:
        response = client.get('/contacts/')
        assert response.status_code == 200
        assert b"Contacts" in response.data
        assert b"https://www.strava.com/athletes/2843469" in response.data
        assert b"https://www.instagram.com/urka_runner/" in response.data
        assert b"https://github.com/vol1ura" in response.data
