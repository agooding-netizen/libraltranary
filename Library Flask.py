import imghdr
import os
import sqlite3
import flask_login as fl
from flask import Flask, g, request, render_template, send_from_directory, abort, flash, redirect, url_for
from werkzeug.utils import secure_filename

login_manager = fl.LoginManager()

DATABASE = 'library.db'

app = Flask(__name__)
app.config['UPLOAD_PATH'] = 'uploads'
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png']

login_manager.init_app(app)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


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


def create_book(title, author, status, quantity, image):
    create_book_query = """ INSERT INTO books (title, author, status, quantity, image) VALUES (?, ?, ?, ?, ?)"""
    data_tuple = (title, author, status, quantity, image)

    database = get_db()
    cursor = database.cursor()
    cursor.execute(create_book_query, data_tuple)
    database.commit()
    cursor.close()


def validate_image(stream):
    header = stream.read(512)  # 512 bytes should be enough for a header check
    stream.seek(0)  # reset stream pointer
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')

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
    image = request.files['img_one']
    image_blob = request.files['img_one'].read()
    filename = secure_filename(image.filename)

    if filename != '':
        file_ext = os.path.splitext(filename)[1]
        if file_ext in app.config['UPLOAD_EXTENSIONS'] or \
                file_ext == validate_image(image.stream):
            image.save(os.path.join(app.config['UPLOAD_PATH'], filename))
        else:
            abort(400)

    if quantity > 0:
        status = 'Available'
    else:
        status = 'Unavailable'

    create_book(title, author, status, quantity, image_blob)

    return render_template('book_information.html',
                           title=title,
                           author=author,
                           quantity=quantity,
                           status=status,
                           image="/uploads/" + filename)


# TODO Need to make this a hyperlink from book information
@app.route('/uploads/<filename>')
def upload(filename):
    return send_from_directory(app.config['UPLOAD_PATH'], filename)


@app.route('/view_book', methods=['POST'])
def find_book_search():
    find_book_query = """ SELECT title, author, quantity, status, image FROM books WHERE title LIKE ?; """
    search = str("%" + request.form.get("search") + "%")

    database = get_db()
    cursor = database.cursor()
    cursor.execute(find_book_query, (search,))

    data = cursor.fetchone()
    if len(data) == 0:
        find_book_query = """ SELECT title, author, quantity, status, image FROM books WHERE author LIKE ?; """
        cursor.execute(find_book_query, (search,))
        data = cursor.fetchone()

    return render_template('book_information.html', title=data[0], author=data[1], quantity=data[2], status=data[3],
                           image=data[4])


@app.route('/')
def home():
    return render_template('Homepage.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = fl.LoginForm()
    if form.validate_on_submit():
        fl.login_user(user)

        flash('Logged in successfully')

        next = request.args.get('next')
        if not fl.is_safe_url(next):
            return abort(400)

        return redirect(next or url_for('index'))
    return render_template('Login.html')


@app.route('/user-login')
@login_required
def user_login():
    return render_template('User-Login.html')


@app.route('/librarian-login')
@login_required
def librarian_login():
    return render_template('Librarian-Login.html')


@app.route('/catalogue')
def catalogue():
    fetch_book_info = """ SELECT title, author, quantity, status from books; """

    database = get_db()
    cursor = database.cursor()
    data = cursor.execute(fetch_book_info)

    return render_template('Catalogue.html', table=data)


if __name__ == '__main__':
    app.run(host='localhost', port='8080', debug=True)
