import sqlite3
from flask import Flask, g

DATABASE = r'C:\libraltranary\library.db'

app = Flask(__name__)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


with app.app_context():
    db = get_db()
    db.cursor().execute('''
        create table if not exists books (
            id integer primary key autoincrement not null,
            title varchar(255) not null,
            author varchar(255) not null,
            ISBN integer not null,
            quantity integer not null,
            status varchar(255) not null default('Available'),
            image blob
)''')
    db.commit()


@app.route('/create_book/<string:title>/<string:author>/<int:ISBN>/<int:quantity>')
def create_book(title, author, ISBN, quantity):
    create_book_query = """ INSERT INTO books (title, author, ISBN, quantity) VALUES (?, ?, ?, ?)"""
    data_tuple = (title, author, ISBN, quantity)

    database = get_db()
    cursor = database.cursor()
    cursor.execute(create_book_query, data_tuple)
    database.commit()
    cursor.close()
    return f'Book added to catalogue'


if __name__ == '__main__':
    app.run(host='localhost', port='8080', debug=True)

