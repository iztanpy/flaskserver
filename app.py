from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, render_template, make_response, redirect, url_for, session
from flask_cors import CORS, cross_origin
from os import environ

app = Flask(__name__)
# CORS(app)
# SQLALCHEMY_TRACK_MODIFICATIONS = False
#
#
# # connect database to flask app
#
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/facialdetection'
# db = SQLAlchemy(app)
#
#
# # create a user class
#
# class User(db.Model):
#     __tablename__ = "users"
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(64), unique=True, nullable=False)
#     password = db.Column(db.String(64), nullable=False)
#
#     def check_password(self, password):
#         return self.password == password
#
#     def __repr__(self):
#         return '<User %r>' % self.username
#
#
# db.create_all()

@app.route('/')
def base():
    return "server is up!"

@app.route('/processing', methods=["POST"])
def process():
    username = request.json.get("username")
    password = request.json.get("password")
    try:
        new_user = User(
            username=username,
            password=password
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




    # existing_user = User.query.filter(
    #      User.username == username
    # ).first()
    # # if username is taken
    # if existing_user:
    #     return 'username already taken!'
    #     # else create a new user
    # new_user = User(
    #     username=username,
    #     password=password
    # )
    # # add to the database
    # db.session.add(new_user)
    # db.session.commit()
    # redirect user to the home page, and see that their record has been added?

#
# @app.route('/calibrate eye size', methods=methods = ["POST", "GET"])
#
# def calibration():





if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

#
# # 2. add records
# usr1 = User()
# usr1.id = 1
# usr1.username = "wang"
# usr1.password = "wangwang"
#
# usr2 = User(id=2, username="yang", password="yang")
# db.session.add(usr1)
# print("Add usr1")
# db.session.add(usr2)
# print("Add usr2")
# db.session.commit()
#
# # 3. query the record, note that the query returns the object ， if the query does not return none
# users1 = User.query.all()  #  query all
# print(users1)
# print("User Count：", len(users1))
#
#
# user = User.query.get(1)
# db.session.delete(user)
# print("Delete usr1")
# db.session.commit()
#
# users2 = User.query.all()  #  query all
# print(users2)
# print("User Count：", len(users2))
