import sqlite3
from flask import Flask, g, request, render_template

DATABASE = 'library.db'

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
            quantity integer not null,
            status varchar(255) not null default('Available'),
            image blob
)''')
    db.commit()


def create_book(title, author, status, quantity):
    create_book_query = """ INSERT INTO books (title, author, status, quantity) VALUES (?, ?, ?, ?)"""
    data_tuple = (title, author, status, quantity)

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
        Status: <input name='status' type='int'/>
        Quantity: <input name='quantity' type='int'/>
        <input value='Create' type='submit' />
    </form>
    '''


@app.route('/create_book', methods=['POST'])
def get_book_information():
    fetch_book_info = """ SELECT title, author, status, quantity from books; """

    database = get_db()
    cursor = database.cursor()
    cursor.execute(fetch_book_info)

    title = request.cursor.get('title')
    author = request.cursor.get('author')
    status = request.cursor.get('status')
    quantity = request.cursor.get('quantity')

    create_book(title, author, status, quantity)
    return f'Book added to catalogue'


@app.route('/books', methods=['GET'])
def get_book_info(title):
    fetch_book_info = """ SELECT title, author, quantity, status from books where title = """ + str(title) + """; """

    database = get_db()
    cursor = database.cursor()
    cursor.execute(fetch_book_info)

    data = cursor.fetchone()

    return render_template('book_information.html', title=data[0], author=data[1], quantity=data[2], status=data[3])


@app.route('/')
def home():
    return render_template('Homepage.html')


if __name__ == '__main__':
    app.run(host='localhost', port='8080', debug=True)


