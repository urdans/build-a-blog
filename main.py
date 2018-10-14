from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import re
import hashlib

#
username = 'build-a-blog'
password = 'urdans'
host = 'localhost:8889'
databasename = 'build-a-blog'

app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://{}:{}@localhost:8889/{}'.format(
    username, password, databasename)
app.config['SQLALCHEMY_ECHO'] = False
app.secret_key = 'ab44ad479fbc554617359163faad52bef2bf622b'
db = SQLAlchemy(app)


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    active = db.Column(db.Boolean)
    # posts = db.relationship('Posts', backref='thread')
    posts = db.relationship('Posts', back_populates='user')

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = password
        self.active = True

    def __repr__(self):
        return '<User: {}>'.format(self.name)


class Threads(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), unique=True, nullable=False)
    active = db.Column(db.Boolean)
    posts = db.relationship('Posts', back_populates='thread')

    def __init__(self, title):
        self.title = title
        self.active = True

    def __repr__(self):
        return '<Thread: {}>'.format(self.title)


class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('threads.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow(), nullable=False)
    repply_id = db.Column(db.Integer)
    thread = db.relationship('Threads', back_populates='posts')
    user = db.relationship('Users', back_populates='posts')

    def repplies_count(self):
        # TODO this function should use the sql count function for better performance
        return Posts.query.filter_by(repply_id=self.id).count()

    def __init__(self, thread_id, user_id, text, date=None, repply_id=None):
        self.thread_id = thread_id
        self.user_id = user_id
        self.text = text
        self.date = date
        self.repply_id = repply_id

    def __repr__(self):
        return '<Post:  {}>'.format(self.text[0:100])

# some helper functions


def logged_user_name():
    if 'user' in session:
        logged_user = Users.query.filter_by(id=session['user']).first()
        if logged_user:
            return logged_user.name

# This will allow me to call this function from a jinja2 template
app.jinja_env.globals.update(logged_user_name=logged_user_name)

def user_exist(username):
    if len(username.strip()) > 3:
        user = Users.query.filter_by(name=username).first()
        if user:
            return user.id, user.password


def validate_email(email):
    if len(email.strip) > 4: # like k@m.i
        match = re.search(
            r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', email, re.I)
        if match:
            return match.group()


def validate_password(password, repeated_password):
    if (password == repeated_password) and (len(password) >= 5):
        return hashlib.sha1(password.encode('utf-8')).hexdigest()

# This will redirect bad enpoints to the home page


@app.before_request
def filter_bad_endpoints():
    allowed_routes = ['main', 'blog', 'myposts', 'newpost',
                      'register', 'login', 'logout', 'about', 'static']
    if request.endpoint not in allowed_routes:
        return redirect('/')


@app.route("/")
def main():
    return render_template("index.html", Posts=Posts)


@app.route("/blog", methods=['GET', 'POST'])
def blog():
    if request.method == 'POST':
        if not logged_user_name():
            return redirect("/login")
        thread_id = int(request.form['threadid'])
        user_id = session['user']
        new_post_text = request.form['newposttext']
        post_id_repplied = int(request.form['postidrepplied'])
        print('\n****************************** repply **************************************')
        print('thread_id            :', thread_id)
        print('user_id              :', user_id)
        print('new_post_text        :', new_post_text[:60])
        print('post_id_repplied     :', post_id_repplied)
        print('****************************************************************************\n')
        # quede aqui. need threadid, *userid, *text, *date in format "2018-01-24", repply_id=1
        # create the post and save it to the db
        if (thread_id == -1) or (post_id_repplied == -1):  # it's a new post
            new_thread_title = request.form['threadtitle']
            if not new_post_text or len(new_thread_title) <= 3:
                # TODO flash a message indicating that empty posts are not allowed and the title must be at least 4 letters long
                return redirect('/newpost')
            # need to create the thread first, so i need to request the thread title first
            new_thread = Threads(new_thread_title)
            db.session.add(new_thread)
            db.session.commit()
            thread_id = new_thread.id
            new_post = Posts(thread_id, user_id, new_post_text)
            db.session.add(new_post)
            db.session.commit()
            return redirect('/myposts')
            # then use the thread.id for creating the new post
            pass
        else:  # it's a repply to an existing post
            if not new_post_text:
                # TODO flash a message indicating that empty posts are not allowed
                return redirect('/blog?repplyto={}'.format(post_id_repplied))
            # check that thread_id and post_id_repplied are actual ids to corresponding records
            if ((thread_id == Threads.query.filter_by(id=thread_id).first().id) and
                    post_id_repplied == Posts.query.filter_by(id=post_id_repplied).first().id):
                new_post = Posts(thread_id, user_id, new_post_text, repply_id=post_id_repplied)
                db.session.add(new_post)
                db.session.commit()
                return redirect('/myposts')
            # at this point the post have not been created and we redirect to home

    read_full_post_id = request.args.get('rmpostid', '')
    if read_full_post_id:
        post = Posts.query.filter_by(id=read_full_post_id).first()
        if post:
            return render_template("blog.html", post=post)
        else:
            return redirect("/")

    posts_from_user_id = request.args.get('userid', '')
    if posts_from_user_id:
        user = Users.query.filter_by(id=posts_from_user_id).first()
        if user:
            return render_template("userblogs.html", user=user)
        else:
            return redirect("/")

    posts_from_title_id = request.args.get('titleid', '')
    if posts_from_title_id:
        thread = Threads.query.filter_by(id=posts_from_title_id).first()
        if thread:
            return render_template("threads.html", thread=thread)
        else:
            return redirect("/")

    repply_to_post_id = request.args.get('repplyto', '')
    if repply_to_post_id:
        username = logged_user_name()
        if not username:
            # TODO flash a message indicating "you must be logged in, please log in"
            return redirect("/login")
        post = Posts.query.filter_by(id=repply_to_post_id).first()
        if post:
            return render_template("newpost.html", post=post, username=username)
        else: # TODO i can get rid of this....
            return redirect("/")

    return redirect("/")


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_name = request.form['username']
        if user_exist(user_name):
            # TODO use flash messages
            return render_template("signup.html", username_value=user_name, baduser="User name not available")

        entered_email = request.form['email']
        validated_email = validate_email(entered_email)
        if not validate_email:
            # TODO use flash messages
            return render_template("signup.html", email_value=entered_email, bademail="Bad email address")

        password = request.form['psw']
        repeated_password = request.form['repsw']
        validated_password = validate_password(password, repeated_password)
        if not validated_password:
            # TODO use flash messages
            return render_template("signup.html", badpassword="Password must match and must be at least 5 characters long")

        new_user = Users(user_name, validated_email, validated_password)
        db.session.add(new_user)
        db.session.commit()
        session['user'] = new_user.id
        return redirect('/')
    else:
        return render_template("signup.html")


@app.route('/logout')
def logout():
    del session['user']
    # TODO flash a logout message
    return redirect('/')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_name = request.form['username']
        password = request.form['psw']
        validated_password = validate_password(password, password)
        user = user_exist(user_name)
        print('****************************** login ***************************************')
        print('user_name            :',user_name)
        print('password             :',password)
        print('validated_password   :',validated_password)
        print('user                 :',user)
        print('****************************************************************************')

        if user:
            if user[1] == validated_password:
                session['user'] = user[0]
                return redirect('/')

        # TODO use flash messages
        return render_template("signup.html", username_value=user_name, baduser="Wrong user/password", loggin=1)
    else:
        return render_template("signup.html", loggin=1)


@app.route('/myposts')
def myposts():
    if logged_user_name:
        return redirect('/blog?userid={}'.format(session['user']))
    else:
        # TODO flash a message like you must be logged in
        return redirect("/")

@app.route('/newpost')
def newpost():
    username = logged_user_name()
    if username:
        return render_template("newpost.html", username=username)
    else:
        # TODO flash a message like you must be logged in
        return redirect("/")


if __name__ == "__main__":
    app.run()
