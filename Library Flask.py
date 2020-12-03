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


def convertToBinaryData(filename):
    # Convert digital data to binary format
    with open(filename, 'rb') as file:
        blobData = file.read()
    return blobData


# The two app routes below do the following:
# Renders a form where information about a new book can be added, then once the information is submitted it updates
# the book database and then displays the new book information on its own page.
@app.route('/create_book', methods=['GET'])
def render_create_book_form():
    return render_template("add_edit_book.html")


@app.route('/create_book', methods=['POST'])
def get_book_information():
    title = request.form.get('title')
    author = request.form.get('author')
    quantity = int(request.form.get('copies'))

    if quantity > 0:
        status = 'Available'
    else:
        status = 'Unavailable'

    create_book(title, author, status, quantity)
    return render_template('book_information.html', title=title, author=author, quantity=quantity, status=status)


@app.route('/books', methods=['GET'])
def get_book_info():
    fetch_book_info = """ SELECT title, author, quantity, status from books; """

    database = get_db()
    cursor = database.cursor()
    cursor.execute(fetch_book_info)

    data = cursor.fetchone()

    return render_template('book_information.html', title=data[0], author=data[1], quantity=data[2], status=data[3])


@app.route('/')
def home():
    return render_template('Homepage.html')


@app.route('/login')
def login():
    return render_template('Login.html')


@app.route('/catalogue')
def catalogue():
    return render_template('Catalogue.html')


if __name__ == '__main__':
    app.run(host='localhost', port='8080', debug=True)
