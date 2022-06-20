import os
import mysql.connector
from collections import namedtuple

from flask import current_app, g
from flask.cli import with_appcontext

Tokens = namedtuple('Tokens', 'id access_token refresh_token expires_at')
Settings = namedtuple('Settings', 'id units')
DEFAULT_SETTINGS = Settings(0, 'imperial')


def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(
            host=os.getenv('MYSQLHOST'),
            port=os.getenv('MYSQLPORT'),
            database=os.getenv('MYSQLDATABASE'),
            user=os.getenv('MYSQLUSER'),
            password=os.getenv('MYSQLPASSWORD')
        )
    return g.db


def get_athlete(athlete_id: int):
    db = get_db()
    cur = db.cursor()
    cur.execute(f'SELECT * FROM subscribers WHERE id = {athlete_id}')
    record_db = cur.fetchone()
    if record_db:
        return Tokens(*record_db)


def add_athlete(tokens: Tokens):
    tokens_db = get_athlete(tokens.id)
    db = get_db()
    cur = db.cursor()
    if not tokens_db:
        sql = 'INSERT INTO subscribers (id, access_token, refresh_token, expires_at) VALUES (%s, %s, %s, %s)'
        cur.execute(sql, tokens)
    elif tokens.access_token != tokens_db.access_token:
        sql = f'UPDATE subscribers SET access_token = %s, refresh_token = %s, expires_at = %s WHERE id = {tokens.id};'
        cur.execute(sql, tokens[1:])
    else:
        return
    db.commit()


def add_settings(settings: Settings):
    """Write to database preferable metrics of weather description.

    :param settings: named tuple Settings
    """
    db = get_db()
    cur = db.cursor()
    cur.execute(f'SELECT * FROM settings WHERE id = {settings.id}')
    settings_db = cur.fetchone()
    if settings_db:
        if settings == Settings(*settings_db):
            return
        sql = f'UPDATE settings SET units = %s WHERE id = {settings.id};'
        cur.execute(sql, settings[1:])
    else:
        if settings[1:] == DEFAULT_SETTINGS[1:]:
            return
        cur.execute('INSERT INTO settings (id, units) VALUES (%s, %s)', (settings.id, settings.units))
    db.commit()


def get_settings(athlete_id: int):
    """Read database and return weather description settings. If settings not provided function
    returns default set with all metrics.

    :param athlete_id: integer Strava athlete id
    :return: named tuple Settings
    """    
    db = get_db()
    cur = db.cursor()
    cur.execute(f'SELECT id, units FROM settings WHERE id = {athlete_id}')
    sel = cur.fetchone()
    
    if sel:
        return Settings(*sel)
    else:
        return DEFAULT_SETTINGS._replace(id=athlete_id)


def delete_athlete(athlete_id: int):
    """Remove athlete's tokens and settings.

    :param athlete_id: Strava athlete id
    """
    db = get_db()
    cur = db.cursor()
    cur.execute(f'DELETE FROM subscribers WHERE id = {athlete_id}')
    cur.execute(f'DELETE FROM settings WHERE id = {athlete_id}')
    db.commit()


if __name__ == '__main__':  # pragma: no cover
    import os
    from dotenv import load_dotenv

    dotenv_path = os.path.join(os.path.dirname(__file__), '../.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
