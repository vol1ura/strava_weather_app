from dotenv import load_dotenv
import os
import sqlite3


def get_athlete(athlete_id):
    with sqlite3.connect(get_base_path()) as conn:
        cur = conn. cursor()
        return cur.execute(f'SELECT * FROM subscribers WHERE id = {athlete_id};').fetchone()


def get_base_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, os.environ.get('DATABASE'))


def add_athlete(data):
    with sqlite3.connect(get_base_path()) as conn:
        cur = conn.cursor()
        record_db = cur.execute(f'SELECT * FROM subscribers WHERE id = {data[0]};').fetchone()
        if not record_db:
            sql = f'INSERT INTO subscribers VALUES(?, ?, ?, ?);'
            cur.execute(sql, data)
        elif data[1] != record_db[1]:
            sql = f'UPDATE subscribers SET access_token = ?, refresh_token = ?, expires_at = ? WHERE id = {data[0]}'
            cur.execute(sql, data[1:])
        conn.commit()
        return True


def delete_athlete(athlete_id):
    with sqlite3.connect(get_base_path()) as conn:
        cur = conn.cursor()
        cur.execute(f'DELETE * FROM subscribers WHERE id = {athlete_id};')
        conn.commit()


def create_db():
    """Initial function for database creation"""
    with sqlite3.connect(get_base_path()) as conn, open('sql_db.sql', 'r') as f:
        conn.cursor().executescript(f.read())
        conn.commit()


if __name__ == '__main__':
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)

    # create_db()  # TODO remove after debugging
    # tok = {'token_type': 'Bearer', 'expires_at': 1610123457, 'expires_in': 7431,
    #        'refresh_token': '393ab0db081334a3909a05b99947df6566c631ef',
    #        'access_token': '295e2287e1c3a3ad7db6aafbcec608ba407f8b82',
    #        'athlete': {'id': 2843469}}
    # add_athlete(tok)
