import json
import os
import pandas as pd
import plotly.graph_objects as go
import requests
import time

from datetime import datetime, timedelta
from flask import abort, Flask, g, jsonify, make_response, request
from flask_httpauth import HTTPBasicAuth
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from passlib.hash import sha256_crypt
from random import random, randint
from rq import Queue
from rq.job import Job
from worker import conn

app = Flask(__name__)
auth = HTTPBasicAuth()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

mail_settings = {
    "MAIL_SERVER": 'smtp.gmail.com',
    "MAIL_PORT": 465,
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": os.environ['EMAIL_USER'],
    "MAIL_PASSWORD": os.environ['EMAIL_PASSWORD']
}
app.config.update(mail_settings)

db = SQLAlchemy(app)
mail = Mail(app)

q = Queue(connection=conn)

COVID_API_BASE_URL = "https://corona-api.com/"


# User DB to maintain the signup details
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(), nullable=False)
    last_name = db.Column(db.String(), nullable=False)
    email = db.Column(db.String(), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(), nullable=False)
    country = db.Column(db.String(), nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "country": self.country,
        }

    def hash_password(self, password):
        self.password_hash = sha256_crypt.encrypt(password)


db.create_all()


@auth.verify_password
def verify_password(email, password):
    app.logger.info(f"Email: {email}")
    app.logger.info(f"Password: {password}")
    user = User.query.filter(User.email == email).first()
    app.logger.info("Checking given credentials...")
    if not user or not sha256_crypt.verify(password, user.password_hash):
        return False
    g.active_user = user
    return True


@app.route('/')
def intro():
    # @todo: Need to remove as this is just for dev purpose
    # User.__table__.drop(db.engine)

    response = make_response(
        jsonify({
            "FLASK": "Minimal app with demonstration of RESTful API",
        }),
        200
    )
    response.headers["Content-Type"] = "application/json"
    return response


# Create New User:
# ----------------
# curl -H "Content-Type: application/json" -X POST -d '{"first_name":"admin", "last_name":"admin",
# "email":"admin@gmail.com", "password":"admin", "country":"IN"}' -i "http://localhost:2222/api/v1.0/user/add"

@app.route('/api/v1.0/user/add', methods=['POST'])
def create_user():
    first_name = request.json.get('first_name')
    last_name = request.json.get('last_name')
    email = request.json.get('email')
    password = request.json.get('password')
    country = request.json.get('country')
    if not first_name or not last_name or not email or not password or not country:
        abort(400)  # Bad Request: Missing Parameters
    if User.query.filter(User.email == email).first():
        response = make_response(
            jsonify({
                "email": email,
                "message": "E-mail already exists!"
            }),
            200
        )
        response.headers["Content-Type"] = "application/json"
        return response
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        country=country
    )
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()
    response = make_response(
        jsonify({
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "country": country,
            "message": "User successfully created."
        }),
        201
    )
    response.headers["Content-Type"] = "application/json"
    return response


# Verify User:
# ------------
# curl -H "Content-Type: application/json" -X POST -d '{"email":"admin@gmail.com",
# "password":"admin"}' -i "http://localhost:2222/api/v1.0/user/verify"

@app.route('/api/v1.0/user/verify', methods=['POST'])
def verify_user():
    email = request.json.get('email')
    password = request.json.get('password')
    if not email or not password:
        abort(400)  # Bad Request: Missing Parameters
    user = User.query.filter(User.email == email).first()
    if not user:
        abort(404)  # Not Found: User not found
    elif not sha256_crypt.verify(password, user.password_hash):
        response = make_response(
            jsonify({
                "message": "Password is incorrect."
            }),
            200
        )
        response.headers["Content-Type"] = "application/json"
        return response
    else:
        response = make_response(
            jsonify({
                "user": user.serialize(),
                "message": "Successfully logged-in."
            }),
            200
        )
        response.headers["Content-Type"] = "application/json"
        return response


# Get Active User:
# ----------------
# curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/user/get"

# Get List of Users:
# ------------------
# curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/user/get?user=all"

# Get Specific User:
# ------------------
# curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/user/get?user=admin@gmail.com"

@app.route('/api/v1.0/user/get', methods=['GET'])
@auth.login_required
def get_user():
    user = request.args.get('user')
    if not user:
        response = make_response(
            jsonify({
                "user": g.active_user.serialize(),
            }),
            200
        )
        response.headers["Content-Type"] = "application/json"
        return response
    elif user == 'all':
        all_user = User.query.all()
        response = make_response(
            jsonify({
                "users": [user.serialize() for user in all_user],
            }),
            200
        )
        response.headers["Content-Type"] = "application/json"
        return response
    else:
        user = User.query.filter(User.email == user).first()
        if not user:
            abort(404)  # Not Found: User not found
        response = make_response(
            jsonify({
                "user": user.serialize(),
            }),
            200
        )
        response.headers["Content-Type"] = "application/json"
        return response


# Update User Info:
# -----------------
# curl -H "Content-Type: application/json" -X PUT -u admin@gmail.com:admin -d '{"first_name":"admin",
# "last_name":"admin", "country":"IN"}' -i "http://localhost:2222/api/v1.0/user/update"

@app.route('/api/v1.0/user/update', methods=['PUT'])
@auth.login_required
def update_user():
    # valid_keys = ['first_name', 'last_name', 'country']
    if request.json.get('email'):
        response = make_response(
            jsonify({
                "message": "E-mail can not be updated!"
            }),
            200
        )
        response.headers["Content-Type"] = "application/json"
        return response
    first_name = request.json.get('first_name')
    last_name = request.json.get('last_name')
    country = request.json.get('country')
    if first_name or last_name or country:
        if first_name:
            g.active_user.first_name = first_name
        if last_name:
            g.active_user.last_name = last_name
        if country:
            g.active_user.country = country
        db.session.commit()
        response = make_response(
            jsonify({
                "user": g.active_user.serialize(),
                "message": "User details successfully updated."
            }),
            200
        )
        response.headers["Content-Type"] = "application/json"
        return response
    else:
        abort(400)  # Bad Request: Unknown Parameters


# Update User Password:
# ---------------------
# curl -H "Content-Type: application/json" -X PUT -u admin@gmail.com:admin -d '{"password":"admin"}'
# -i "http://localhost:2222/api/v1.0/user/update-password"

@app.route('/api/v1.0/user/update-password', methods=['PUT'])
@auth.login_required
def update_user_password():
    password = request.json.get('password')
    if not password:
        abort(400)  # Bad Request: Missing Parameters
    g.active_user.hash_password(password)
    db.session.commit()
    response = make_response(
        jsonify({
            "message": "Password successfully updated."
        }),
        200
    )
    response.headers["Content-Type"] = "application/json"
    return response


# Delete User:
# ------------
# curl -X DELETE -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/user/delete"

@app.route('/api/v1.0/user/delete', methods=['DELETE'])
@auth.login_required
def delete_user():
    db.session.delete(g.active_user)
    db.session.commit()
    response = make_response(
        jsonify({
            "message": "User successfully deleted."
        }),
        200
    )
    response.headers["Content-Type"] = "application/json"
    return response


def _send_mail(sender, recipient, start_date, end_date, country, image_file_name):
    with app.app_context():
        recipients = [recipient]
        message = f"Hi,\n\n" \
                  f"Here is the image of the COVID Analysis between time-range {start_date} to {end_date}\n\n" \
                  f"Regards,\n" \
                  f"Anonymous"
        subject = f"{country} - COVID Analysis"
        msg = Message(recipients=recipients,
                      sender=sender,
                      body=message,
                      subject=subject)
        with app.open_resource(f"images/{image_file_name}") as fp:
            msg.attach(image_file_name, "image/png", fp.read())
        mail.send(msg)
        return "Mail was sent successfully."


def _get_covid_data(api_url, country, start_date, end_date):
    request_url = requests.get(api_url)

    # Just for testing purpose of `Exponential Backoff Algorithm with Jitter`
    # request_url.status_code = 502

    request_url.raise_for_status()

    content = request_url.content
    dict_content = content.decode("UTF-8")
    response = json.loads(dict_content)
    data_frame = pd.DataFrame(response['data']['timeline'])
    data_frame['date'] = pd.to_datetime(data_frame['date'], format='%Y-%m-%d')
    date_mask = (data_frame['date'] >= start_date) & (data_frame['date'] <= end_date)
    data_frame = data_frame.loc[date_mask]

    x_axis = data_frame['date'].dt.strftime('%Y-%m-%d').tolist()
    y_deaths = data_frame['deaths'].tolist()
    y_confirmed = data_frame['confirmed'].tolist()
    y_recovered = data_frame['recovered'].tolist()

    fig = go.Figure(data=[
        go.Bar(name='Confirmed', x=x_axis, y=y_confirmed),
        go.Bar(name='Recovered', x=x_axis, y=y_recovered),
        go.Bar(name='Deaths', x=x_axis, y=y_deaths)
    ])
    fig.update_layout(barmode='group')
    # Will open Graph in Browser
    # fig.show()

    if not os.path.exists("images"):
        os.mkdir("images")
    image_file_name = f"{country}-{start_date}-{end_date}.png"
    fig.write_image(f"images/{image_file_name}")

    app.logger.info(f"\n\nCOVID - Data Frame \n"
                    f"Country Code: {country} \n"
                    f"Date Range: {start_date} - {end_date} \n\n"
                    f"{data_frame} \n\n")

    # Replace original timeline with manipulate timeline
    response['data']['timeline'] = data_frame.to_dict('records')

    # Send mail to user
    sender = app.config.get("MAIL_USERNAME")
    recipient = g.active_user.email
    from app import _send_mail
    job = q.enqueue_call(func=_send_mail, args=(sender, recipient, start_date, end_date,
                                                country, image_file_name,))
    app.logger.info(f"Job Id: {job.get_id()}")
    return response


# Get COVID data for Active User's Country:
# -----------------------------------------
# curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/covid"
# curl -X GET -u admin@gmail.com:admin -i
# "http://localhost:2222/api/v1.0/covid?start-date=2020-12-10&end-date=2020-12-20"

# Get COVID data for Specific Country:
# ------------------------------------
# curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/covid?country=IN&start-date=2020-12-17"
# curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/covid?country=IN&end-date=2020-12-15"
# curl -X GET -u admin@gmail.com:admin -i
# "http://localhost:2222/api/v1.0/covid?country=IN&start-date=2020-12-05&end-date=2020-12-15"

RETRY_CODES = [429, 502, 503, 504]
# 429 - Too Many Requests
# 502 - Bad Gateway
# 503 - Service Unavailable
# 504 - Gateway Timeout
# Need to retry again if we got any of the above HTTP Status Code


@app.route('/api/v1.0/covid', methods=['GET'])
@auth.login_required
def get_covid_data():
    country = request.args.get('country')
    if not country:
        country = g.active_user.country

    start_date = request.args.get('start-date')
    end_date = request.args.get('end-date')
    api_url = COVID_API_BASE_URL + 'countries/' + country

    if not end_date and not start_date:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=15)
    else:
        if start_date and not end_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.now()
        else:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            start_date = end_date

    try:
        return _get_covid_data(api_url, country, start_date, end_date)
    except requests.HTTPError as err:
        if err.response.status_code not in RETRY_CODES:
            app.logger.error("Raising error...")
            abort(err.response.status_code)

        app.logger.info("Please wait... Retrying again with Exponential Backoff...")
        # Max Retry 3 times, after that show original error
        for retry in range(1, 4):
            base_sleep_time = 1
            sleep_time_with_jitter = retry * ((base_sleep_time + randint(1, 5)) * random())
            time.sleep(sleep_time_with_jitter)
            try:
                app.logger.info(f"Trying again({retry}) ... (after waiting {sleep_time_with_jitter} seconds)")
                return _get_covid_data(api_url, country, start_date, end_date)
            except requests.HTTPError as err1:
                if err1.response.status_code not in RETRY_CODES:
                    abort(err1.response.status_code)
        app.logger.error("Raising error...")
        abort(err.response.status_code)


# Old JobId will stay only for 500 seconds
@app.route("/api/v1.0/job/<job_key>", methods=['GET'])
@auth.login_required
def get_job_results(job_key):
    job = Job.fetch(job_key, connection=conn)

    if job.is_finished:
        response = make_response(
            jsonify({
                "result": str(job.result)
            }),
            200
        )
        response.headers["Content-Type"] = "application/json"
        return response
    else:
        response = make_response(
            jsonify({
                "result": "Nay!"
            }),
            202
        )
        response.headers["Content-Type"] = "application/json"
        return response


if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=2222)
