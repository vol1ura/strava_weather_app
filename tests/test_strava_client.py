import json
import time

import pytest
import responses

from utils import manage_db, strava_client
from utils.exceptions import StravaAPIError


@responses.activate
def test_strava_client_get_activity(database, db_token, monkeypatch):
    activity_id = 1
    athlete_tokens = db_token[0]
    responses.add(responses.GET,
                  f'https://www.strava.com/api/v3/activities/{activity_id}',
                  json={'athlete_id': athlete_tokens.id})
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    client = strava_client.StravaClient(athlete_tokens.id, activity_id)
    activity = client.get_activity
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers['Authorization'] == f'Bearer {athlete_tokens.access_token}'
    assert activity['athlete_id'] == athlete_tokens.id


@responses.activate
def test_strava_client_get_activity_failed(database, db_token, monkeypatch):
    activity_id = 1
    athlete_tokens = db_token[0]
    responses.add(responses.GET, f'https://www.strava.com/api/v3/activities/{activity_id}', body='')
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    client = strava_client.StravaClient(athlete_tokens.id, activity_id)
    with pytest.raises(StravaAPIError):
        client.get_activity
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers['Authorization'] == f'Bearer {athlete_tokens.access_token}'


@responses.activate
def test_strava_client_modify_activity(database, db_token, monkeypatch):
    activity_id = 1
    athlete_tokens = db_token[0]
    responses.add(responses.PUT, f'https://www.strava.com/api/v3/activities/{activity_id}', body='ok')
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    client = strava_client.StravaClient(athlete_tokens.id, activity_id)
    client.modify_activity({'description': 'test'})
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers['Authorization'] == f'Bearer {athlete_tokens.access_token}'


@responses.activate
def test_strava_client_modify_activity_failed(database, db_token, monkeypatch):
    activity_id = 1
    athlete_tokens = db_token[0]
    responses.add(responses.PUT, f'https://www.strava.com/api/v3/activities/{activity_id}', status=500)
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    client = strava_client.StravaClient(athlete_tokens.id, activity_id)
    with pytest.raises(StravaAPIError):
        client.modify_activity({'description': 'test'})
    assert len(responses.calls) == 1


@responses.activate
def test_strava_client_update_tokens(database, monkeypatch):
    activity_id = 1
    athlete_id = 2
    responses.add(responses.POST, 'https://www.strava.com/oauth/token',
                  body=json.dumps({'access_token': 'new_access_token',
                                   'refresh_token': 'new_refresh_token',
                                   'expires_at': int(time.time()) + 100}))
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    strava_client.StravaClient(athlete_id, activity_id)
    assert len(responses.calls) == 1
    cur = database.cursor()
    record = cur.execute(f'SELECT * FROM subscribers WHERE id = {athlete_id}')
    actual_tokens = manage_db.Tokens(*record.fetchone())
    assert actual_tokens.id == athlete_id
    assert actual_tokens.access_token == 'new_access_token'
    assert actual_tokens.refresh_token == 'new_refresh_token'
    assert actual_tokens.expires_at > time.time()


@responses.activate
def test_strava_client_update_tokens_failed(database, db_token, monkeypatch):
    activity_id = 1
    athlete_id = 2
    responses.add(responses.POST, 'https://www.strava.com/oauth/token',
                  body=json.dumps({'response': 'bad response'}))
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    # Try to update tokens
    with pytest.raises(StravaAPIError):
        strava_client.StravaClient(athlete_id, activity_id)
    # Check that tokens has not modified
    assert len(responses.calls) == 1
    cur = database.cursor()
    record = cur.execute(f'SELECT * FROM subscribers WHERE id = {athlete_id}')
    actual_tokens = manage_db.Tokens(*record.fetchone())
    assert actual_tokens == db_token[1]
