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
import time

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#set up connection to the databse
DATABASE_URL = os.environ['DATABASE_URL']
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL?sslmode=require')
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
uri = os.getenv("DATABASE_URL")  # or other relevant config var
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
db = SQLAlchemy(app)



#set up the functions used for facial detection
hog_face_detector = dlib.get_frontal_face_detector()

dlib_facelandmark = dlib.shape_predictor(
    'shape_predictor_68_face_landmarks.dat')


ear_collection = []
threshold = 0.32

def readb64(base64_string):
    sbuf = io.BytesIO()
    sbuf.write(base64.b64decode(base64_string))
    pimg = Image.open(sbuf)
    return cv2.cvtColor(np.array(pimg), cv2.COLOR_RGB2BGR)


def calculate_ear(eye):
    a = distance.euclidean(eye[1], eye[5])
    b = distance.euclidean(eye[2], eye[4])
    c = distance.euclidean(eye[0], eye[3])
    ear = (a + b) / (2 * c)
    return ear


def mean(lst):
    if len(lst) == 0:
        return 0
    final = 0
    for i in lst:
        final += i
    return final / len(lst)




#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/facialdetection'

# consumer.py for rabbitmq

# create a user class

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(64), nullable=False)

    def check_password(self, password):
        return self.password == password

    def __repr__(self):
        return '<User %r>' % self.username



@app.route('/')
def base():
    return "server is up!"

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
        )
        db.session.add(new_user)
        db.session.commit()
        print("s")
        return "success"

    except:
        print("f")
        return "failure"

@app.route('/login', methods=["POST"])
def login():
    username = request.json.get("username")
    password = request.json.get("password")
    existing_user = User.query.filter(
                User.username == username
                ).first()
    if existing_user:
        print(existing_user.username)
        #check if the password is accurate
        if existing_user.password == password:

            return "login"
        else:
            print("incorrect password")
            return "incorrect password"
    return "user not found"


@app.route('/get_value', methods=['GET', 'POST'])
def get_value():
    name = request.json.get('name')
    result = db.execute(f"SELECT ear FROM users WHERE username = '{name}'")
    print(result)
    return str(result)


@app.route('/video_player', methods=['POST'])
def player():
    global ear_collection
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
        ear_collection.append(avg_ear)

    ear_collection = ear_collection[-10:]
    value = mean(ear_collection)

    print(avg_ear)
    print(len(ear_collection))
    print(value)

    return str(value)


@app.route('/clear', methods=['POST'])
def clear():
    global calibration_collection, ear_collection
    print('clearing')
    calibration_collection.clear()
    ear_collection.clear()
    return 'cleared'


@app.route('/calibration', methods=['POST'])
def calibration():
    calibration_collection = [];
    string = request.json.get('picture')
    is_final = request.json.get('final')
    name = request.json.get('name')
    img = readb64(string['base64'])

    img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    cv2.imwrite("random.jpg", img)

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

        calibration_collection.append(mean_ear)

    print(name)

    if is_final == 'true':
        print('final one')
        value = mean(calibration_collection)
        print(value)

        db.execute(f"UPDATE users SET ear={value} WHERE username = '{name}'")

        db.commit()

        print('updated!')
        return str(mean(calibration_collection))

    return 'next_loop'


@app.route('/checkEmail', methods=['POST'])
def checkEmail():
    email = request.json.get("email")
    existing_user = User.query.filter(
                User.email == email
                ).first()
    if existing_user:
        #email the username and password!
        existing_user.username
        existing_user.password

        return "valid"

    return "invalid"



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

