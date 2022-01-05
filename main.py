from flask_mail import Mail, Message
import json
import time
import myfirebase
import os
import convertcode
from werkzeug.utils import secure_filename
from calendar import month_name
from flask import Flask, render_template, request, session, url_for, flash, redirect
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_sslify import SSLify
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import BadSignature, SignatureExpired

with open('config.json', 'r') as c:
    params = json.load(c)["params"]
    c.seek(0)
    database = json.load(c)["database"]
    c.seek(0)
    statics = json.load(c)["statics"]

per_page = params['per_page']
app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = statics['upload_folder']
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = params['email']
app.config['MAIL_PASSWORD'] = params['email-password']
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
mail = Mail(app)

s = URLSafeTimedSerializer('my-secret')
sslify = SSLify(app)

# heroku pg:psql postgresql-spherical-80201 --app help4you
app.config['SQLALCHEMY_DATABASE_URI'] = f"{database['app']}://{database['user']}:{database['password']}@{database['host']}/{database['database']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "super-secret-key"
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(sno):
    return login.query.get(sno)


class login(UserMixin, db.Model):
    def get_id(self):
        return (self.sno)
    sno = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(1000), nullable=False)
    birthday = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    profile_pic = db.Column(db.String(), nullable=False)
    time = db.Column(db.String(100), nullable=False)
    about = db.Column(db.String(), nullable=True)


class posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    post = db.Column(db.String(50000), nullable=False)
    user = db.Column(db.Integer, nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    time = db.Column(db.String(100), nullable=False)
    grade = db.Column(db.String(100), nullable=False)


class answers(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    answer = db.Column(db.String(50000), nullable=False)
    user = db.Column(db.Integer, nullable=False)
    question_id = db.Column(db.String(100), nullable=False)
    time = db.Column(db.String(100), nullable=False)


@app.errorhandler(401)
def unauthorized(e):
    return redirect('/login')


@app.errorhandler(404)
def notfound(e):
    return render_template('404.html')

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        msg = Message("Feedback message from Help4You", sender=params['email'], recipients=["ashutoshthakur11sep@gmail.com"])
        msg.html = f'''
        <b>Name: </b>{name}<br>
        <b>Email: </b>{email}<br>
        <b>Phone: </b>{phone}<br>
        <b>Message: </b>{message}
        '''
        mail.send(msg)
    return render_template('index.html', params=params)

@app.route("/login", methods=["GET", "POST"])
def signin():
    if request.method == 'POST':
        username = request.form.get('uid').lower()
        email = request.form.get('uid')
        password = request.form.get('password')
        user = login.query.filter_by(username=username).first()
        user1 = login.query.filter_by(email=email).first()
        if user and convertcode.decodecode(user.password) == password:
            login_user(user, remember=True)
            return redirect('/home')
        elif user1 and convertcode.decodecode(user1.password) == password:
            login_user(user1, remember=True)
            return redirect('/home')
        else:
            flash('Entered Credentials are wrong.', 'danger')
            return render_template('login.html', title='Login', params=params)
    return render_template('login.html', title='Login', params=params)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == 'POST':
        session["username"] = request.form.get('username').lower()
        session["first_name"] = request.form.get('first_name')
        session["last_name"] = request.form.get('last_name')
        session["password"] = request.form.get('password')
        rpassword = request.form.get('rpassword')
        session["birthday"] = request.form.get('birthday')
        session["gender"] = request.form.get('gender')
        session['about'] = request.form.get('about')
        email = request.form.get('email')
        sign_user = login.query.filter_by(
            username=session.get('username')).first()
        sign_email = login.query.filter_by(email=email).first()
        if sign_user:
            flash('Username Used.')
        elif sign_email:
            flash('Already an account with this email.')
        elif session.get('password') != rpassword:
            flash('Password and repeat password are different.')
        else:
            token = s.dumps(email, salt='email-confirm')
            msg = Message('Confirm Email ', sender='factsworld1109@gmail.com', recipients=[email])
            link = url_for('verify', token=token, _external=True)
            msg.body = 'Your link is {} but go on this link(will expire in 1 hr) from the same device and browser used for registration.'.format(
                link)
            mail.send(msg)
            return render_template('box.html', email=email)
    return render_template('signup.html', title=f"{params['title']}: Sign Up for a new account", params=params)


@app.route('/home', methods=["GET", "POST"])
@login_required
def home():
    page=request.args.get('page', 1, type=int)
    questions = posts.query.order_by(posts.sno.desc()).paginate(page=page, per_page=per_page)
    users = login.query.all()
    if request.method == 'POST':
        username = current_user.sno
        post = request.form.get('question')
        subject = request.form.get('subject')
        grade = request.form.get('grade')
        info = posts(user=username, post=post,
                     subject=subject, time=time.time(), grade=grade)
        db.session.add(info)
        db.session.commit()
        return redirect('/home')
    return render_template("home.html", title=f"{params['title']}: Ask and Answer Questions", questions=questions, users=users, time=time.time())


@app.route('/answer/<int:sno>', methods=["GET", "POST"])
@login_required
def answer(sno):
    page=request.args.get('page', 1, type=int)
    users = login.query.all()
    question = posts.query.filter_by(sno=sno).first()
    myanswers = answers.query.filter_by(question_id=sno).order_by(answers.sno.desc()).paginate(page=page, per_page=per_page)
    if request.method == 'POST':
        myanswer = request.form.get('answer')
        answer_info = answers(
            answer=myanswer, user=current_user.sno, question_id=sno, time=time.time())
        db.session.add(answer_info)
        db.session.commit()
        return redirect('/answer/'+str(sno))
    if question:
        return render_template('answer.html', title=f"{params['title']}: Give Answers", question=question, time=time.time(), users=users, sno=sno, answers=myanswers)
    else:
        return redirect('/home')


@app.route('/account/<string:username>')
def account(username):
    page=request.args.get('page', 1, type=int)
    apage=request.args.get('apage', 1, type=int)
    user = login.query.filter_by(username=username).first()
    if user:
        queastions = posts.query.filter_by(user=user.sno).order_by(posts.sno.desc()).paginate(page=page, per_page=per_page)
        tques = len(posts.query.all())
        tans = len(answers.query.all())
        myanswers = answers.query.filter_by(user=user.sno).order_by(answers.sno.desc()).paginate(page=apage, per_page=per_page)
        timep = time.localtime(int(float(user.time)))
        joined = f'{timep.tm_mday} {month_name[timep.tm_mon]}, {timep.tm_year}'
        bday = user.birthday.split('/')
        birthday = f'{bday[0]} {month_name[int(bday[1])]}, {bday[-1]}'
        return render_template('account.html', tques=tques, tans=tans, title=f'Account @ {user.username}', user=user, joined=joined, birthday=birthday, questions=queastions, answers=myanswers, per_page=per_page)
    else:
        return render_template('404.html')


@app.route('/settings', methods=["GET", "POST"])
@login_required
def settings():
    if request.method == 'POST':
        email = request.form.get('email')
        currentp = request.form.get('currentp')
        username = request.form.get('username')
        if email:
            user1 = login.query.filter_by(email=email).first()
            if user1 != None:
                flash('Already an account with this email.', 'danger')
                return redirect('/settings')
            else:
                token = s.dumps(email, salt='email-confirm')
                msg = Message(
                    'Confirm Email ', sender=params['email'], recipients=[email])
                link = url_for('verify2', token=token, _external=True)
                msg.body = 'Your link is {} but go on this linklink(will expire in 1 hr) from the same device and browser used for registration.'.format(
                    link)
                mail.send(msg)
                flash(
                    'A confirmation link has been sent on the email address - '+email, 'success')
                return redirect('/settings')
        elif currentp:
            encpass = convertcode.convertcode(currentp)
            if encpass != current_user.password:
                flash('Current Password is wrong.', 'danger')
                return redirect('/settings')
            else:
                newp = request.form.get('newp')
                rp = request.form.get('rp')
                if newp != rp:
                    flash('New Password and Repeat Password is different.', 'danger')
                    return redirect('/settings')
                else:
                    encpass = convertcode.convertcode(newp)
                    current_user.password = encpass
                    db.session.commit()
                    flash('Password has been changed.', 'success')
                    return redirect('/settings')
        elif username:
            if username != current_user.username and user1 != None:
                flash('Username Used.', 'danger')
            else:
                current_user.username = username
                current_user.first_name = request.form.get('first_name')
                current_user.last_name = request.form.get('last_name')
                current_user.gender = request.form.get('gender')
                current_user.birthday = request.form.get('birthday')
                current_user.about = request.form.get('about')
                db.session.commit()
        else:
            file = request.files['file']
            if file:
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(
                        app.config['UPLOAD_FOLDER'], filename))
                    myfirebase.upload(filename, str(current_user.sno)+'/profile_pic.png')
                    piclink = myfirebase.getfileurl(
                        str(current_user.sno)+'/profile_pic.png')
                    current_user.profile_pic = piclink
                    db.session.commit()
                    return redirect('/settings')
            user1 = login.query.filter_by(username=username).first()
            
            return redirect('/settings')
    return render_template('settings.html', title=f'{params["title"]} : Settings')


@app.route("/verify/<token>")
def verify(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
        username = session.get('username')
        first_name = session.get('first_name')
        last_name = session.get('last_name')
        password = session.get('password')
        birthday = session.get('birthday')
        gender = session.get('gender')
        about = session.get('about')
        encpass = convertcode.convertcode(password)
        profile_pic = statics['profile_pic']
        info = login(username=username, first_name=first_name, last_name=last_name, password=encpass,
                     birthday=birthday, gender=gender, email=email, profile_pic=profile_pic, time=time.time(), about=about)
        db.session.add(info)
        db.session.commit()
        flash('Your account has been created successfully.', 'success')
        return redirect('/login')
    except SignatureExpired:
        return render_template('404.html')
    except BadSignature:
        return render_template('404.html')


@app.route("/verify2/<token>")
@login_required
def verify2(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
        user = login.query.filter_by(username=current_user.username).first()
        user.email = email
        db.session.commit()
        flash('Email address has been changed.', 'success')
        return redirect('/settings')
    except SignatureExpired:
        return render_template('404.html')
    except BadSignature:
        return render_template('404.html')


@app.route("/delete/<type>/<sno>")
@login_required
def delete(type, sno):
    if type == 'question':
        question = posts.query.filter_by(sno=sno).first()
        if question and question.user == current_user.sno:
            answer = answers.query.filter_by(question_id=question.sno).all()
            db.session.delete(question)
            for i in answer:
                db.session.delete(i)
            db.session.commit()
            return redirect('/account/'+current_user.username)
    elif type == 'answer':
        answer = answers.query.filter_by(sno=sno).first()
        if answer and answer.user == current_user.sno:
            db.session.delete(answer)
            db.session.commit()
            return redirect('/account/'+current_user.username)
    return render_template('404.html')


@app.route("/google4a74fd24a326259f.html")
def googlesearchverify():
    return render_template('google4a74fd24a326259f.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You has been logged out successfully. ', 'success')
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)
