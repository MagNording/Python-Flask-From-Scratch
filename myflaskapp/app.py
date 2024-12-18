from functools import wraps
from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
#from data import Articles
from config import Config
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt

app = Flask(__name__)
app.config.from_object(Config)

# init mysql
mysql = MySQL(app)

#Articles = Articles()

# index
@app.route('/')
def index():
    return render_template('home.html')

# about
@app.route('/about')
def about():
    return render_template('about.html')

# articles
@app.route('/articles')
def articles():
    with mysql.connection.cursor() as cur:
        # get articles
        result = cur.execute("SELECT * FROM articles")
        articles = cur.fetchall()

        if result > 0:
            return render_template('articles.html', articles=articles)
        else:
            msg = 'No articles found'
            return render_template('articles.html', msg=msg)
    

# single article
@app.route('/article/<string:id>/')
def article(id):
    # create cursor
    with mysql.connection.cursor() as cur:
        # get article by id
        cur.execute("SELECT * FROM articles WHERE id = %s", [id])
        article = cur.fetchone()

        if article is None:
            flash('Article not found', 'danger')
            return redirect(url_for('dashboard'))
        
    return render_template('article.html', article=article)


# register form class
class RegisterForm(Form):
    name = StringField('Name', validators=[validators.Length(min=1, max=50)])
    username = StringField('Username', validators=[validators.Length(min=4, max=25)])
    email = StringField('Email', validators=[validators.Length(min=6, max=50)])
    password = PasswordField('Password', validators=[
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# user register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.hash(str(form.password.data))

        # create cursor
        with mysql.connection.cursor() as cur:

            # Kontrollera om användarnamn eller e-post redan finns
            cur.execute("SELECT * FROM users WHERE email = %s OR username = %s", (email, username))
            existing_user = cur.fetchone()

            if existing_user:
                flash('User with that email or username already exists', 'danger')
                return render_template('register.html', form=form)

            # execute query
            cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)",
                        (name, email, username, password))
            
            # commit to db
            mysql.connection.commit()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form = form)


# user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form fields
        username = request.form['username']
        password_candidate = request.form['password']

        if not username or not password_candidate:
            error = 'Both fields are required'
            return render_template('login.html', error=error)

        # create cursor
        with mysql.connection.cursor() as cur:

            # get user by username
            result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

            if result > 0:
                # get stored hash
                data = cur.fetchone()
                password = data['password']

                # compare passwords
                if sha256_crypt.verify(password_candidate,  password):
                    # passed
                    session['logged_in'] = True
                    session['username'] = username

                    flash('You are now logged in', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    error = 'Invalid username or password'
                    return render_template('login.html', error=error)
                
            else:
                error = 'Invalid username or password'
                return render_template('login.html', error=error)

    return render_template('login.html')


# check if user logged in 
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else: 
            flash('Unauthorized, please log in', 'danger')
            return redirect(url_for('login'))
    return wrap


# logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))


# dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # create cursor
    with mysql.connection.cursor() as cur:

        # get articles
        result = cur.execute("SELECT * FROM articles")

        articles = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No articles found'
        return render_template('dashboard.html', msg=msg)
    
    
# article form class
class ArticleForm(Form):
    title = StringField('Title', validators=[validators.Length(min=1, max=200)])
    body = TextAreaField('Body', validators=[validators.Length(min=6)])


# add article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # create cursor
        with mysql.connection.cursor() as cur:

            # execute
            cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, session['username']))

            # commit
            mysql.connection.commit()

        flash('Article created', 'success')

        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)


# edit article
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    try:
        # create cursor
        cur = mysql.connection.cursor()

        # get article by id
        cur.execute("SELECT * FROM articles WHERE id = %s", [id])
        article = cur.fetchone()

        # Kontrollera om artikeln finns
        if not article:
            flash('Article not found', 'danger')
            return redirect(url_for('dashboard'))

        # get form
        form = ArticleForm(request.form)

        # populate article form fields
        if request.method == 'GET':
            form.title.data = article['title']
            form.body.data = article['body']

        if request.method == 'POST' and form.validate():
            title = form.title.data
            body = form.body.data

            # execute update query
            cur.execute(
                "UPDATE articles SET title=%s, body=%s WHERE id=%s",
                (title, body, id)
            )
            # commit
            mysql.connection.commit()

            flash('Article updated', 'success')
            return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'An error occurred: {e}', 'danger')
    finally:
        cur.close()

    return render_template('edit_article.html', form=form)


# delete article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    try:
        # create cursor
        with mysql.connection.cursor() as cur:

            # execute
            cur.execute("DELETE FROM articles WHERE id = %s", [id])

            # commit
            mysql.connection.commit()

        flash('Article deleted', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'An error occurred: {e}', 'danger')
        return redirect(url_for('dashboard'))
    

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])
            