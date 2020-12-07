import imghdr
import os
import sqlite3
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user, logout_user
from flask import Flask, g, request, render_template, send_from_directory, abort, redirect, url_for
from werkzeug.utils import secure_filename

DATABASE = 'library.db'

app = Flask(__name__)

# config
app.config.update(
    DEBUG=True,
    SECRET_KEY='secret_xxx',
    UPLOAD_PATH='uploads',
    UPLOAD_EXTENSIONS=['.jpg', '.png', '.jpeg']
)

# flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# user model
class User(UserMixin):
    def __init__(self, id):
        find_user = """ SELECT member_name, password FROM members WHERE id = ?; """

        database = get_db()
        cursor = database.cursor()
        cursor.execute(find_user, (id,))
        data = cursor.fetchone()

        self.id = id
        self.name = data[0]
        self.password = data[1]
        self.is_librarian = False

    def __repr__(self):
        return "%d/%s/%s" % (self.id, self.name, self.password)

    def permission_check(self, librarian):
        self.is_librarian = librarian

        if librarian:
            find_user = """ SELECT admin_name, password FROM librarians WHERE id = ?; """

            database = get_db()
            cursor = database.cursor()
            cursor.execute(find_user, (self.id,))
            data = cursor.fetchone()

            self.name = data[0]
            self.password = data[1]



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
            isbn integer not null default(0000000000),
            image text
)''')
    db.commit()


def create_book(title, author, status, quantity, isbn, image):
    create_book_query = """ INSERT INTO books (title, author, status, quantity, isbn, image) VALUES (?, ?, ?, ?, ?, ?) """
    data_tuple = (title, author, status, quantity, isbn, image)

    database = get_db()
    cursor = database.cursor()
    cursor.execute(create_book_query, data_tuple)
    database.commit()
    cursor.close()


def update_book(isbn, image):
    update_book_query = """ UPDATE books SET image = ? where isbn = ?"""
    data_tuple = (image, isbn)

    database = get_db()
    cursor = database.cursor()
    cursor.execute(update_book_query, data_tuple)
    database.commit()
    cursor.close()


def validate_image(stream):
    header = stream.read(512)  # 512 bytes should be enough for a header check
    stream.seek(0)  # reset stream pointer
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')

# Picture uploads only work if you upload a NEW picture. Cannot pick one that exists in the folder with the same name.
@app.route('/upload_image-<title>-<author>-<isbn>-<status>-<quantity>')
def index(title, author, status, isbn, quantity):
    files = os.listdir(app.config['UPLOAD_PATH'])
    return render_template('upload_image.html', title=title, author=author, ibn=isbn, status=status, quantity=quantity, files=files)


@app.route('/upload_image-<title>-<author>-<isbn>-<status>-<quantity>', methods=['POST'])
def upload_files(title, author, status, isbn, quantity):
    uploaded_file = request.files['file']
    filename = secure_filename(uploaded_file.filename)
    if filename != '':
        file_ext = os.path.splitext(filename)[1]
        if file_ext not in app.config['UPLOAD_EXTENSIONS'] or \
                file_ext != validate_image(uploaded_file.stream):
            abort(400)
        uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))

    update_book(isbn=isbn, image=filename)

    return redirect(url_for('book_with_cover', title=title, author=author, isbn=isbn, status=status, quantity=quantity, image=filename))


@app.route('/upload-image-<title>-<author>-<isbn>-<status>-<quantity>-<image>')
def book_with_cover(title, author, status, isbn, quantity, image):
    return render_template('book_information.html',
                           title=title,
                           author=author,
                           quantity=quantity,
                           status=status,
                           isbn=isbn,
                           image=image)


@app.route('/<title>-<author>-<isbn>-<status>-<quantity>')
def book_without_cover(title, author, status, isbn, quantity):
    return render_template('book_information.html',
                           title=title,
                           author=author,
                           quantity=quantity,
                           status=status,
                           isbn=isbn)


# The two app routes below do the following:
# Renders a form where information about a new book can be added, then once the information is submitted it updates
# the book database and then displays the new book information on its own page.
@app.route('/create_book', methods=['GET'])
def render_create_book_form():
    return render_template("add_book.html")


@app.route('/create_book', methods=['POST'])
def get_book_information():
    title = request.form.get('title')
    author = request.form.get('author')
    isbn = request.form.get('isbn')
    quantity = int(request.form.get('copies'))
    image_requested = request.form.get('image_request')

    if quantity > 0:
        status = 'Available'
    else:
        status = 'Unavailable'

    if isbn == "":
        isbn = "0000000000"

    image_blob = None

    create_book(title, author, status, quantity, isbn, image_blob)

    if image_requested == "Yes":
        return redirect(url_for('index', title=title, author=author, isbn=isbn, status=status, quantity=quantity))

    return redirect(url_for('book_without_cover', title=title, author=author, isbn=isbn, status=status, quantity=quantity))


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
    if data is None:
        find_book_query = """ SELECT title, author, quantity, status, image FROM books WHERE author LIKE ?; """
        cursor.execute(find_book_query, (search,))

        data = cursor.fetchone()
    if data is None:
        return redirect(url_for('failed_search'))

    return render_template('book_information.html', title=data[0], author=data[1], quantity=data[2], status=data[3],
                           image=data[4])


@app.route('/search-failed', methods=['GET', 'POST'])
def failed_search():
    return render_template('Homepage.html', found=False)


@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template('Homepage_Authenticated.html', found=True)
    else:
        return render_template('Homepage.html', found=True)


@app.route('/login', methods=['GET', 'POST'])
def login():
    librarian = False

    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['pwd']
            find_user = """ SELECT id, member_name, password FROM members WHERE member_name = ?; """
        except:
            librarian = True
            username = request.form['librarian_id']
            password = request.form['librarian_pwd']
            find_user = """ SELECT id, admin_name, password FROM librarians WHERE admin_name = ?; """

        database = get_db()
        cursor = database.cursor()
        cursor.execute(find_user, (username,))
        data = cursor.fetchone()

        if data is None:
            return abort(401)
        elif password == data[2]:
            id = data[0]
            user = User(id)
            user.permission_check(librarian)

            login_user(user)
            return redirect(url_for('post_login', name=user.name, is_librarian=user.is_librarian))

        '''if password == username + "_secret":
            id = username.split('user')[1]
            user = User(id)
            login_user(user)
            if not librarian:
                return redirect("user-login")
            else:
                return redirect("librarian-login")
        else:
            return abort(401)'''
    else:
        return render_template('Login.html')


@app.route('/login-<name>-<is_librarian>')
@login_required
def post_login(is_librarian, name):
    if is_librarian == 'True':
        return render_template('Librarian-Login.html', user=name)
    else:
        return render_template('User-Login.html', user=name)


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


# callback to reload the user object
@login_manager.user_loader
def load_user(userid):
    return User(userid)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect('/')


if __name__ == '__main__':
    app.run(host='localhost', port='8080', debug=True)
