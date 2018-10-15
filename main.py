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

Online_Users_List = []


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    active = db.Column(db.Boolean)
    # posts = db.relationship('Posts', backref='thread')
    posts = db.relationship(
        'Posts', order_by="desc(Posts.date)", back_populates='user')

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
    posts = db.relationship(
        'Posts', order_by="desc(Posts.date)", back_populates='thread')

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


def Ordered_Post_by(order):
    return Posts.query.order_by(order).all()


def logged_user_name():
    if 'user' in session:
        logged_user = Users.query.filter_by(id=session['user']).first()
        if logged_user:
            return logged_user.name


def register_online_user(username):
    if not username in Online_Users_List:
        Online_Users_List.append(username)


def unregister_online_user(username):
    if username in Online_Users_List:
        Online_Users_List.remove(username)


def unregister_online_user_by_id(user_id):
    user = Users.query.filter_by(id=user_id).first()
    if user:
        unregister_online_user(user.name)


def online_users_count():
    return len(Online_Users_List)


def get_online_user_list():
    return Online_Users_List


def registered_users_count():
    return Users.query.count()


# This will allow me to call these functions from a jinja2 template
app.jinja_env.globals.update(logged_user_name=logged_user_name)
app.jinja_env.globals.update(online_users_count=online_users_count)
app.jinja_env.globals.update(get_online_user_list=get_online_user_list)
app.jinja_env.globals.update(registered_users_count=registered_users_count)


def user_exist(username):
    un = username.strip()
    user = Users.query.filter_by(name=un).first()
    if user:
        return user.id, user.password


def validate_email(email):
    em = email.strip()
    if len(em) > 4:  # like k@m.i
        match = re.search(
            r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', em, re.I)
        if match:
            return match.group()
    # return ""


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
    # Ordered_Post_by("date desc")
    return render_template("index.html", Posts=Posts)


@app.route("/blog", methods=['GET', 'POST'])
def blog():
    if request.method == 'POST':
        # we are about to create a new post, so we start collecting the inputs from the user, but before we check
        # that the user is logged in
        if not logged_user_name():
            return redirect("/login")
        thread_id = int(request.form['threadid'])
        user_id = session['user']
        new_post_text = request.form['newposttext']
        post_id_repplied = int(request.form['postidrepplied'])
        print(
            '\n****************************** repply **************************************')
        print('thread_id            :', thread_id)
        print('user_id              :', user_id)
        print('new_post_text        :', new_post_text[:60])
        print('post_id_repplied     :', post_id_repplied)
        print(
            '****************************************************************************\n')
        # we check if it's a new post and thread or if it's a repply
        if (thread_id == -1) or (post_id_repplied == -1):
            # It's a new post. So we first create the thread and the the post itself, but before we check
            # the lengh of the inputs to be correct.
            new_thread_title = request.form['threadtitle']
            if not new_post_text or len(new_thread_title) <= 3:
                flash(
                    "Empty posts are not allowed and the title must be at least 4 characters long.", "error")
                return redirect('/newpost')
            new_thread = Threads(new_thread_title)
            db.session.add(new_thread)
            db.session.commit()
            thread_id = new_thread.id
            new_post = Posts(thread_id, user_id, new_post_text)
            db.session.add(new_post)
            db.session.commit()
            return redirect('/myposts')
        else:
            # it's a repply to an existing post
            if not new_post_text:
                # this should never happen unless the user is hacking...
                flash("Empty posts are not allowed.", "error")
                return redirect('/blog?repplyto={}'.format(post_id_repplied))
            # check that thread_id and post_id_repplied are valid ids to corresponding records
            if ((thread_id == Threads.query.filter_by(id=thread_id).first().id) and
                    post_id_repplied == Posts.query.filter_by(id=post_id_repplied).first().id):
                new_post = Posts(thread_id, user_id,
                                 new_post_text, repply_id=post_id_repplied)
                db.session.add(new_post)
                db.session.commit()
                return redirect('/myposts')
            else:
                flash("I see you are tricking me, ha ha...!", "error")
            # at this point the post have not been created and we redirect to home

    # read more of that post
    read_full_post_id = request.args.get('rmpostid', '')
    if read_full_post_id:
        post = Posts.query.filter_by(id=read_full_post_id).first()
        if post:
            return render_template("blog.html", post=post)

    # see that author's posts
    posts_from_user_id = request.args.get('userid', '')
    if posts_from_user_id:
        user = Users.query.filter_by(id=posts_from_user_id).first()
        if user:
            return render_template("userblogs.html", user=user)

    # see all the post about that thread
    posts_from_title_id = request.args.get('titleid', '')
    if posts_from_title_id:
        thread = Threads.query.filter_by(id=posts_from_title_id).first()
        if thread:
            return render_template("threads.html", thread=thread)

    # repply to that post
    repply_to_post_id = request.args.get('repplyto', '')
    if repply_to_post_id:
        username = logged_user_name()
        if not username:
            flash("You must log in.", "error")
            return redirect("/login")
        post = Posts.query.filter_by(id=repply_to_post_id).first()
        if post:
            return render_template("newpost.html", post=post, username=username)

    return redirect("/")


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # we are trying to register a new user
        user_name = request.form['username']
        entered_email = request.form['email']
        # check user length
        if len(user_name) < 3:
            flash("User name must be at least 3 characters long.", "error")
            return render_template("signup.html", username_value=user_name, email_value=entered_email)

        # check the user availability
        if user_exist(user_name):
            flash("User name not available.", "msg")
            return render_template("signup.html", username_value=user_name, email_value=entered_email)

        # check the email is valid
        validated_email = validate_email(entered_email)
        if not validated_email:
            flash("Bad email address.", "error")
            return render_template("signup.html", username_value=user_name, email_value=entered_email)

        # check the length of password. It doesnt have to be a complex one
        password = request.form['psw']
        repeated_password = request.form['repsw']
        validated_password = validate_password(password, repeated_password)
        if not validated_password:
            flash("Password must match and must be at least 5 characters long.", "error")
            return render_template("signup.html", username_value=user_name, email_value=entered_email)

        # at this point, all looks good to proceed creating the new user
        new_user = Users(user_name, validated_email, validated_password)
        db.session.add(new_user)
        db.session.commit()
        session['user'] = new_user.id
        register_online_user(user_name)
        return redirect('/')
    else:
        # we are just displaying the form
        return render_template("signup.html")


@app.route('/logout')
def logout():
    unregister_online_user_by_id(session['user'])
    del session['user']
    flash("You're logged out.", "msg")
    return redirect('/')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # we are trying to log in an existing user
        user_name = request.form['username']
        password = request.form['psw']
        validated_password = validate_password(password, password)
        user = user_exist(user_name)
        print(
            '****************************** login ***************************************')
        print('user_name            :', user_name)
        print('password             :', password)
        print('validated_password   :', validated_password)
        print('user                 :', user)
        print(
            '****************************************************************************')

        # check user exists
        if user:
            # check password hashes match
            if user[1] == validated_password:
                session['user'] = user[0]  # that's the user id
                register_online_user(user_name)
                flash("You are logged in", "msg")
                return redirect('/')

        flash("Wrong user/password.", "error")
        # the loggin flag is to indicate it's a log in, not a sign up
        return render_template("signup.html", username_value=user_name, loggin=1)
    else:
        return render_template("signup.html", loggin=1)


@app.route('/myposts')
def myposts():
    if logged_user_name:
        return redirect('/blog?userid={}'.format(session['user']))
    else:
        flash("You must log in to see your posts.", "msg")
        return redirect("/")


@app.route('/newpost')
def newpost():
    username = logged_user_name()
    if username:
        return render_template("newpost.html", username=username)
    else:
        flash("You must log in to see your posts.", "msg")
        return redirect("/")


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == "__main__":
    app.run()

"""
Lessons learned:

1. To make the code maintainable and maybe simpler:
    - make one template per route.
    - make one route per method
    - make one controller per route

2. For serious websites, dont pass clear tags and ids, pass tokens and codes (need to check this)

3. To be able to call my custom function from a jinja2 template, register the function name like this:
    app.jinja_env.globals.update(myfunctionname=myfunctionname)
"""
