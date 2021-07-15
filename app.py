from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, render_template, make_response, redirect, url_for, session
from flask_cors import CORS, cross_origin
import os
import psycopg2
import sys
import base64
import cv2
import io
from imageio import imread
from PIL import Image
import numpy as np
import dlib
from scipy.spatial import distance
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from string import Template
from geopy.geocoders import Nominatim
from random import randint
from sqlalchemy.orm import relation

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Set up our own email address
MY_ADDRESS = 'stayawakeorbital@outlook.com'
MY_PASSWORD = "StayAwake123"

s = smtplib.SMTP(host='smtp-mail.outlook.com', port=587)
s.starttls()
s.login(MY_ADDRESS, MY_PASSWORD)


# set up connection to the database
DATABASE_URL = os.environ['DATABASE_URL']
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL?sslmode=require')
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
uri = os.getenv("DATABASE_URL")  # or other relevant config var
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
db = SQLAlchemy(app)


# Dictionary to store the calibration collection for each user
calibration_collection = {}

# Dictionary to store the number of times fallen asleep


# set up the functions used for facial detection
hog_face_detector = dlib.get_frontal_face_detector()

dlib_facelandmark = dlib.shape_predictor(
    'shape_predictor_68_face_landmarks.dat')


ear_collection = {}

geocoder = Nominatim(user_agent='app')

threshold = 0.32

# Function to decode base64 data to an image in numpy array form

# Function to get an address from an input latitude and longitude


def get_address(lat, long):
    return str(geocoder.reverse((lat, long)))

# function to reconnect to the smtp server


def smtp_connect():
    s = smtplib.SMTP(host='smtp-mail.outlook.com', port=587)
    s.starttls()
    s.login(MY_ADDRESS, MY_PASSWORD)
    return s

# Function to convert a base64 string to an image in array form


def readb64(base64_string):
    sbuf = io.BytesIO()
    sbuf.write(base64.b64decode(base64_string))
    pimg = Image.open(sbuf)
    return cv2.cvtColor(np.array(pimg), cv2.COLOR_RGB2BGR)


# Function to calculate the eye aspect ratio given a list containing points of the eye
def calculate_ear(eye):
    a = distance.euclidean(eye[1], eye[5])
    b = distance.euclidean(eye[2], eye[4])
    c = distance.euclidean(eye[0], eye[3])
    ear = (a + b) / (2 * c)
    return ear

# function to calculate the mean value of a list (assumed to contain numeric data)


def mean(lst):
    if len(lst) == 0:
        return 0
    final = 0
    for i in lst:
        final += i
    return final / len(lst)


def read_template(filename):
    with open(filename, 'r', encoding='utf-8') as template_file:
        template_file_content = template_file.read()
    return Template(template_file_content)


#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/facialdetection'

# consumer.py for rabbitmq

# create a user class

# A user class for the database
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(320), unique=True, nullable=False)
    password = db.Column(db.String(64), nullable=False)
    ear = db.Column(db.Float, default=0.32)
    nokEmail = db.Column(db.String(320))
    nokCode = db.Column(db.Integer, default=0)
    nokVerified = db.Column(db.Boolean, default=False)

    def check_password(self, password):
        return self.password == password

    def __repr__(self):
        return '<User %r>' % self.username


# A class to represent the next of kins


db.create_all()


@app.route('/')
def base():
    return "server is up!"

# Function to facilitate logging in for an existing user


@app.route('/processing', methods=["POST"])
def process():
    username = request.json.get("username")
    password = request.json.get("password")
    email = request.json.get("email")
    try:
        new_user = User(
            username=username,
            password=password,
            email=email,
            ear=0.32,
        )
        db.session.add(new_user)
        db.session.commit()

        return "success"

    except:

        return "failure"


# Function to facilitate log in
@app.route('/login', methods=["POST"])
def login():
    username = request.json.get("username")
    password = request.json.get("password")
    existing_user = User.query.filter(
        User.username == username
    ).first()

    if existing_user:
        print(existing_user.username)
        # check if the password is accurate
        if existing_user.password == password:

            return "login"
        else:
            print("incorrect password")
            return "incorrect password"
    return "user not found"


# Function to facilitate getting the ear value for a user
@app.route('/get_value', methods=['GET', 'POST'])
def get_value():
    name = request.json.get('name')

    existing_user = User.query.filter(User.username == name).first()
    result = existing_user.ear
    return str(result)


# Function to send verification email to next of kin
@app.route('/add_nok', methods=['GET', 'POST'])
def add_nok():

    global s
    username = request.json.get('name')
    relationshipEmail = request.json.get('email')
    verificationCode = randint(100000, 999999)

    try:
        nominating_user = User.query.filter(User.username == username).first()
        nominating_user_email = nominating_user.email

        message_template = read_template('verification.txt')
        msg = MIMEMultipart()
        message = message_template.substitute(USEREMAIL=nominating_user_email,
                                              VERIFICATION_CODE=verificationCode)
        msg['From'] = MY_ADDRESS
        msg['To'] = relationshipEmail
        msg['Subject'] = "Next of kin nomination"

        msg.attach(MIMEText(message, 'plain'))
        s.send_message(msg)
        del msg

    except smtplib.SMTPServerDisconnected:
        s = smtp_connect()
        nominating_user = User.query.filter(User.username == username).first()
        nominating_user_email = nominating_user.email

        message_template = read_template('verification.txt')
        msg = MIMEMultipart()
        message = message_template.substitute(USEREMAIL=nominating_user_email,
                                              VERIFICATION_CODE=verificationCode)
        msg['From'] = MY_ADDRESS
        msg['To'] = relationshipEmail
        msg['Subject'] = "Next of kin nomination"

        msg.attach(MIMEText(message, 'plain'))
        s.send_message(msg)

    nominating_user.nokEmail = relationshipEmail
    nominating_user.nokCode = verificationCode
    nominating_user.nokVerified = False
    nominating_user_email = nominating_user.email
    print(nominating_user.nokCode)
    db.session.commit()

    return 'success'

# Function to check whether a nok is verified


@app.route('/check_verification', methods=['GET', 'POST'])
def check_verification():
    relationshipEmail = request.json.get('email')
    username = request.json.get('name')
    existingEntry = User.query.filter(User.username == username).first()
    print(existingEntry)

    if existingEntry.nokVerified:
        return 'true'
    return 'false'


# Function to verify the Next of Kin email address
@app.route('/verify_nok', methods=['GET', 'POST'])
def verify_nok():
    inputtedCode = 0
    try:
        inputtedCode = int(request.json.get('input'))
        print(inputtedCode)
    except ValueError:
        return 'failure'

    username = request.json.get('name')
    print(username)

    existingEntry = User.query.filter(User.username == username).first()
    print(existingEntry)
    print(existingEntry.nokCode)
    print(type(existingEntry.nokCode))
    if int(existingEntry.nokCode) == inputtedCode:

        existingEntry.nokVerified = True
        db.session.commit()
        return 'Success'
    return 'Failure'


# Function to delete a Next of Kin
@app.route('/delete_nok', methods=['GET', 'POST'])
def delete_nok():
    username = request.json.get('name')
    existingEntry = User.query.filter(User.username == username).first()
    existingEntry.nokEmail = None
    existingEntry.nokVerified = False
    existingEntry.nokCode = 0
    db.session.commit()

    return 'deleted'


# Function to simulate to app running and calculating the EAR
@app.route('/video_player/<name>', methods=['POST'])
def player(name):
    global ear_collection
    if name not in ear_collection.keys():
        ear_collection[name] = []
    string = request.json.get('picture')
    img = readb64(string['base64'])
    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    faces = hog_face_detector(gray)
    avg_ear = 0
    if not faces:
        return 'no'

    for face in faces:

        face_landmarks = dlib_facelandmark(gray, face)

        left_eye = []

        right_eye = []

        for point in range(36, 42):
            x = face_landmarks.part(point).x
            y = face_landmarks.part(point).y
            left_eye.append((x, y))

        # maybe to make it faster we can do just one eye? unless the guy wink alot it should be the same
        for point in range(42, 48):
            x = face_landmarks.part(point).x
            y = face_landmarks.part(point).y
            right_eye.append((x, y))

        left_ear = calculate_ear(left_eye)

        right_ear = calculate_ear(right_eye)
        avg_ear = (left_ear + right_ear) / 2
        ear_collection[name].append(avg_ear)

    ear_collection[name] = ear_collection[name][-3:]
    value = mean(ear_collection[name])

    return str(value)


# Function to clear the two lists so that past ear values do not affect current session
@app.route('/clear/<name>', methods=['POST'])
def clear(name):
    global calibration_collection, ear_collection
    print('clearing')
    if name in calibration_collection.keys():
        calibration_collection[name].clear()
    if name in ear_collection.keys():
        ear_collection[name].clear()
    return 'cleared'


# Function to send location information to next of kin
@app.route('/send_location', methods=['GET', 'POST'])
def send_location():
    latititude = float(request.json.get('latitude'))
    longitude = float(request.json.get('longitude'))
    username = request.json.get('username')
    location = str(geocoder.reverse((latititude, longitude)))

    nokEmail = User.query.filter(User.username == username).first().nokEmail
    if not nokEmail:
        return 'done'

    nokVerified = User.query.filter(
        User.username == username).first().nokVerified
    if not nokVerified:
        return 'done'

    global s
    try:

        nominating_user = User.query.filter(User.username == username).first()
        nominating_user_email = nominating_user.email

        message_template = read_template('location.txt')
        msg = MIMEMultipart()
        message = message_template.substitute(EMAIL=nominating_user_email,
                                              LOCATION=location
                                              )
        msg['From'] = MY_ADDRESS
        msg['To'] = nokEmail
        msg['Subject'] = "User location alert!"

        msg.attach(MIMEText(message, 'plain'))
        s.send_message(msg)
        del msg
        print('sent')

    except smtplib.SMTPServerDisconnected:
        s = smtp_connect()
        nominating_user = User.query.filter(User.username == username).first()
        nominating_user_email = nominating_user.email

        message_template = read_template('location.txt')
        msg = MIMEMultipart()
        message = message_template.substitute(EMAIL=nominating_user_email,
                                              LOCATION=location
                                              )
        msg['From'] = MY_ADDRESS
        msg['To'] = nokEmail
        msg['Subject'] = "User location alert!"

        msg.attach(MIMEText(message, 'plain'))
        s.send_message(msg)
        print('sent')

    return 'sent email'


# Function to help the user calibrate ear to their liking
@app.route('/calibration/<name>', methods=['POST'])
def calibration(name):
    if name not in calibration_collection.keys():
        calibration_collection[name] = []
    string = request.json.get('picture')
    is_final = request.json.get('final')
    name = request.json.get('name')
    img = readb64(string['base64'])

    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    faces = hog_face_detector(gray)

    if not faces:
        return 'done'

    for face in faces:
        face_landmarks = dlib_facelandmark(gray, face)
        left_eye = []
        right_eye = []

        for point in range(36, 42):
            x = face_landmarks.part(point).x
            y = face_landmarks.part(point).y

            left_eye.append((x, y))

        for point in range(42, 48):
            x = face_landmarks.part(point).x
            y = face_landmarks.part(point).y

            right_eye.append((x, y))

        left_ear = calculate_ear(left_eye)
        right_ear = calculate_ear(right_eye)

        mean_ear = (left_ear + right_ear) / 2

        calibration_collection[name].append(mean_ear)

    print(name)

    if is_final == 'true':
        print('final one')
        value = mean(calibration_collection[name])
        print(value)

        user = User.query.filter(User.username == name).first()
        user.ear = value

        db.session.commit()

        print('updated!')
        return str(mean(calibration_collection[name]))

    return 'next_loop'


@app.route('/checkEmail', methods=['POST'])
def checkEmail():

    def read_template(filename):
        with open(filename, 'r', encoding='utf-8') as template_file:
            template_file_content = template_file.read()
        return Template(template_file_content)

    email = request.json.get("email")
    print(email)

    existing_user = User.query.filter(
        User.email == email
    ).first()
    global s

    if existing_user:
        try:
            message_template = read_template('message.txt')
            msg = MIMEMultipart()
            message = message_template.substitute(
                USERNAME=existing_user.username, PASSWORD=existing_user.password)
            msg['From'] = MY_ADDRESS
            msg['To'] = email
            msg['Subject'] = "Forgot password!"

            msg.attach(MIMEText(message, 'plain'))

            s.send_message(msg)
            del msg
            return "valid"

        except smtplib.SMTPServerDisconnected:
            s = smtp_connect()
            message_template = read_template('message.txt')
            msg = MIMEMultipart()
            message = message_template.substitute(
                USERNAME=existing_user.username, PASSWORD=existing_user.password)
            msg['From'] = MY_ADDRESS
            msg['To'] = email
            msg['Subject'] = "Forgot password!"

            msg.attach(MIMEText(message, 'plain'))

            s.send_message(msg)
            del msg
            return "valid"

    return "invalid"


@app.route('/getInfoPersonal', methods=["POST"])
def getInfoPersonal():
    userInfo = ['', '']
    username = request.json.get("username")
    existing_user = User.query.filter(
        User.username == username
    ).first()
    # get the nok info as well as the email address
    userInfo[0] = existing_user.email
    userInfo[1] = existing_user.username
    return userInfo[0] + "," + userInfo[1]


@app.route('/getInfoNok', methods=["POST"])
def getInfoNok():
    userInfo = ['', '']
    username = request.json.get("username")
    existing_user = User.query.filter(
        User.username == username
    ).first()
    # get the nok info as well as the email address
    userInfo[0] = existing_user.nokEmail
    print(existing_user.nokCode)
    if not userInfo[0]:
        return 'nothing'
    userInfo[1] = existing_user.nokVerified
    if userInfo[1]:
        return userInfo[0] + "," + "You have already verified the next of kin email"

    return userInfo[0] + "," + "You have not yet verified the next of kin email. Ask them to provide the verification code sent from email address stayawakeorbital@outlook.com"


@app.route('/updateInfoName', methods=["POST"])
def updateInfoName():
    oldName = request.json.get("name")
    newUsername = request.json.get("username")

    existing_user = User.query.filter(
        User.username == oldName
    ).first()
    # get the nok info as well as the email address
    try:

        existing_user.username = newUsername
        db.session.commit()
        return "success"
    except Exception as e:
        print(e)
        return "failure"


@app.route('/updateInfoEmail', methods=["POST"])
def updateInfoEmail():
    oldName = request.json.get("name")

    newEmail = request.json.get("email")

    existing_user = User.query.filter(
        User.username == oldName
    ).first()
    # get the nok info as well as the email address
    try:
        existing_user.email = newEmail

        db.session.commit()
        return "success"
    except:
        return "failure"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
