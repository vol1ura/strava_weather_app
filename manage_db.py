import os
import sqlite3


class FDataBase:
    def __init__(self, db):
        self.__db = db
        self.__cur = db.cursor()

    def add_athlete_db(self, token):
        pass

    def get_token(self, user_id):
        sql = f'''SELECT * FROM subscribers WHERE id = {user_id}'''
        try:
            self.__cur.execute(sql)
            res = self.__cur.fetchall()
            if res:
                return res
        except:
            print('Read DB failed')
            return []

    def save_token(self, user_id, token):
        sql = f''''''
        try:
            self.__cur.execute(sql)
            return 0
        except:
            print('Write DB failed')
            return 1


def connect_db():
    conn = sqlite3.connect(os.environ.get('DATABASE'))
    conn.row_factory = sqlite3.Row
    return conn


if __name__ == '__main__':
    def create_db():
        db = connect_db()
        with open('sql_db.sql', 'r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        db.close()
