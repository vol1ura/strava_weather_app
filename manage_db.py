import click
from dotenv import load_dotenv
import os
import sqlite3

from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


def get_athlete(athlete_id):
    db = get_db()
    cur = db.cursor()
    return cur.execute(f'SELECT * FROM subscribers WHERE id = {athlete_id};').fetchone()


def add_athlete(data):
    db = get_db()
    cur = db.cursor()
    record_db = cur.execute(f'SELECT * FROM subscribers WHERE id = {data[0]};').fetchone()
    if not record_db:
        sql = f'INSERT INTO subscribers VALUES(?, ?, ?, ?);'
        cur.execute(sql, data)
    elif data[1] != record_db[1]:
        sql = f'UPDATE subscribers SET access_token = ?, refresh_token = ?, expires_at = ? WHERE id = {data[0]}'
        cur.execute(sql, data[1:])
    db.commit()
    return True


def delete_athlete(athlete_id):
    db = get_db()
    cur = db.cursor()
    cur.execute(f'DELETE * FROM subscribers WHERE id = {athlete_id};')
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

