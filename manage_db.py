import os
import sqlite3
from collections import namedtuple

import click
from dotenv import load_dotenv
from flask import current_app, g
from flask.cli import with_appcontext


Settings = namedtuple('Settings', 'id hum wind aqi lan')
Tokens = namedtuple('Tokens', 'id access_token refresh_token expires_at')


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


def get_athlete(athlete_id: int):
    db = get_db()
    cur = db.cursor()
    record_db = cur.execute(f'SELECT * FROM subscribers WHERE id = {athlete_id};').fetchone()
    if record_db:
        return Tokens(*record_db)
    else:
        return None


def add_athlete(tokens: Tokens):
    tokens_db = get_athlete(tokens.id)
    db = get_db()
    cur = db.cursor()
    if not tokens_db:
        sql = 'INSERT INTO subscribers VALUES(?, ?, ?, ?);'
        cur.execute(sql, tokens)
    elif tokens.access_token != tokens_db.access_token:
        sql = f'UPDATE subscribers SET access_token = ?, refresh_token = ?, expires_at = ? WHERE id = {tokens.id};'
        cur.execute(sql, tokens[1:])
    else:
        return
    db.commit()


def add_settings(athlete_id: int, hum: int, wind: int, aqi: int, lan: str):
    record_db = get_settings(athlete_id)
    if record_db.hum != hum or record_db.wind != wind or record_db.aqi != aqi or record_db.lan != lan:
        db = get_db()
        cur = db.cursor()
        sql = f'UPDATE settings SET humidity = ?, wind = ?, aqi = ?, lan = ? WHERE id = {athlete_id};'
        cur.execute(sql, (hum, wind, aqi, lan))
        db.commit()


def get_settings(athlete_id: int):
    db = get_db()
    cur = db.cursor()
    sel = cur.execute(f'SELECT * FROM settings WHERE id = {athlete_id};').fetchone()
    if sel:
        return Settings(*sel)
    else:
        return Settings(athlete_id, 1, 1, 1, 'ru')


def delete_athlete(athlete_id: int):
    db = get_db()
    cur = db.cursor()
    cur.execute(f'DELETE FROM subscribers WHERE id = {athlete_id};')
    cur.execute(f'DELETE FROM settings WHERE id = {athlete_id};')
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


def init_db():
    """Initial function for database creation"""
    db = get_db()
    with current_app.open_resource('sql_db.sql') as f:
        db.executescript(f.read().decode('utf8'))


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear existing database and create new table."""
    init_db()
    click.echo('Initialized database.')


if __name__ == '__main__':
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
