import sqlite3

import pytest

import manage_db

expected_tokens1 = manage_db.Tokens(1, 'access_token', 'refresh_token', 'expires_at')
expected_tokens2 = manage_db.Tokens(2, 'at2', 'rt2', 'exp2')

expected_settings1 = manage_db.Settings(1, 111, 222, 333, 444, 'en')


@pytest.fixture
def database():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    with open('../sql_db.sql') as sql_script:
        db.executescript(sql_script.read())
    cur = db.cursor()
    cur.execute("INSERT INTO subscribers VALUES (?, ?, ?, ?)", expected_tokens1)
    cur.execute("INSERT INTO settings VALUES (?, ?, ?, ?, ?, ?)", expected_settings1)
    db.commit()
    return db


def test_get_athlete(database, monkeypatch):
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    actual_tokens = manage_db.get_athlete(1)
    assert actual_tokens == expected_tokens1


def test_add_athlete_new(database, monkeypatch):
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    manage_db.add_athlete(expected_tokens2)
    cur = database.cursor()
    record2 = cur.execute("SELECT * FROM subscribers WHERE id = 2")
    actual_token2 = manage_db.Tokens(*record2.fetchone())
    assert expected_tokens2 == actual_token2


def test_add_athlete_no_changes(database, monkeypatch):
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    manage_db.add_athlete(expected_tokens1)
    cur = database.cursor()
    record1 = cur.execute("SELECT * FROM subscribers WHERE id = 1")
    actual_token1 = manage_db.Tokens(*record1.fetchone())
    assert expected_tokens1 == actual_token1


def test_add_athlete_update(database, monkeypatch):
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    updated_expected_tokens1 = expected_tokens1._replace(access_token='updated_at1')
    manage_db.add_athlete(updated_expected_tokens1)
    cur = database.cursor()
    record1 = cur.execute("SELECT * FROM subscribers WHERE id = 1")
    actual_token1 = manage_db.Tokens(*record1.fetchone())
    assert updated_expected_tokens1 == actual_token1


def test_add_settings():
    pass


def test_get_settings(database, monkeypatch):
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    actual_settings1 = manage_db.get_settings(1)
    assert actual_settings1 == expected_settings1


def test_get_settings_default(database, monkeypatch):
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    actual_default_settings = manage_db.get_settings(0)
    assert actual_default_settings == manage_db.DEFAULT_SETTINGS


def test_delete_athlete(database, monkeypatch):
    monkeypatch.setattr(manage_db, 'get_db', lambda: database)
    manage_db.delete_athlete(1)
    cur = database.cursor()
    db_record_subcribers = cur.execute("SELECT * FROM subscribers WHERE id = 1")
    assert db_record_subcribers.fetchone() is None
    db_record_settings = cur.execute("SELECT * FROM settings WHERE id = 1")
    assert db_record_settings.fetchone() is None


