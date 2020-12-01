import sqlite3
from flask import Flask, g, request

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


def create_book(title, author, ISBN, quantity):
    create_book_query = """ INSERT INTO books (title, author, ISBN, quantity) VALUES (?, ?, ?, ?)"""
    data_tuple = (title, author, ISBN, quantity)

    database = get_db()
    cursor = database.cursor()
    cursor.execute(create_book_query, data_tuple)
    database.commit()
    cursor.close()


@app.route('/create_book', methods=['GET'])
def render_create_book_form():
    return '''
    <form action='/create_book' method='post' />
        Title: <input name='title' type='varchar'/>
        Author: <input name='author' type='varchar'/>
        ISBN: <input name='isbn' type='int'/>
        Quantity: <input name='quantity' type='int'/>
        <input value='Create' type='submit' />
    </form>
    '''


@app.route('/create_book', methods=['POST'])
def get_book_information():
    title = request.form.get('title')
    author = request.form.get('author')
    isbn = request.form.get('isbn')
    quantity = request.form.get('quantity')

    create_book(title, author, isbn, quantity)
    return f'Book added to catalogue'


if __name__ == '__main__':
    app.run(host='localhost', port='8080', debug=True)

