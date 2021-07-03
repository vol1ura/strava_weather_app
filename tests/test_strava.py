import json
import os
import sqlite3
import time

import pytest
import responses
from dotenv import load_dotenv

import manage_db
import utilities

tested_tokens1 = manage_db.Tokens(1, 'access_token', 'refresh_token', int(time.time()) + 100)
tested_tokens2 = manage_db.Tokens(2, 'access_token', 'refresh_token', int(time.time()) - 100)

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


@pytest.fixture
def database():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    sql_script_path = os.path.dirname(os.path.abspath(__file__)).replace('/tests', '')
    with open(os.path.join(sql_script_path, 'sql_db.sql')) as sql_script:
        db.executescript(sql_script.read())
    cur = db.cursor()
    cur.execute("INSERT INTO subscribers VALUES (?, ?, ?, ?)", tested_tokens1)
    cur.execute("INSERT INTO subscribers VALUES (?, ?, ?, ?)", tested_tokens2)
    db.commit()
    return db


@responses.activate
def test_strava_client_get_activity(database, monkeypatch):
    activity_id = 1
    athlete_id = 1
    responses.add(responses.GET,
                  f'https://www.strava.com/api/v3/activities/{activity_id}',
                  json={'athlete_id': athlete_id})
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    client = utilities.StravaClient(athlete_id, activity_id)
    actitvity = client.get_activity()
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers['Authorization'] == 'Bearer access_token'
    assert actitvity['athlete_id'] == athlete_id


@responses.activate
def test_strava_client_modify_activity(database, monkeypatch):
    activity_id = 1
    athlete_id = 1
    responses.add(responses.PUT, f'https://www.strava.com/api/v3/activities/{activity_id}', body='ok')
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    client = utilities.StravaClient(athlete_id, activity_id)
    client.modify_activity({'description': 'test'})
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers['Authorization'] == 'Bearer access_token'


@responses.activate
def test_strava_client_update_tokens(database, monkeypatch):
    activity_id = 1
    athlete_id = 2
    responses.add(responses.POST, 'https://www.strava.com/oauth/token',
                  body=json.dumps({'access_token': 'new_access_token',
                                   'refresh_token': 'new_refresh_token',
                                   'expires_at': int(time.time()) + 100}))
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    utilities.StravaClient(athlete_id, activity_id)
    assert len(responses.calls) == 1
    cur = database.cursor()
    record = cur.execute(f'SELECT * FROM subscribers WHERE id = {athlete_id}')
    actual_tokens = manage_db.Tokens(*record.fetchone())
    assert actual_tokens.id == athlete_id
    assert actual_tokens.access_token == 'new_access_token'
    assert actual_tokens.refresh_token == 'new_refresh_token'
    assert actual_tokens.expires_at > time.time()
