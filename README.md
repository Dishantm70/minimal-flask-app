# Minimal Flask App


A minimal app developed with [Flask](https://flask.palletsprojects.com/en/1.1.x/) framework.

The main purpose is to introduce how to implement the RESTful API with Flask

- SignUp API
- API with Authentication
- DB used is SQLite
- API support for [about-corona-api](https://about-corona.net/documentation)
- Used [Plotly Library](https://plotly.com/python/) to create Bar Chart image from gathered COVID data


## How to deploy

- Make sure you have python (I used Python 3.8.5 for this app)
- Create virtual environment `python3 -m venv venv`
- Activate the venv `source venv/bin/activate`
- Install requirements: `pip3 install -r requirements.txt`
- Go to App's directory & run `python3 app.py`
- And run `python3 worker.py` for worker (who manage asynchronous task like, send mail) which listen to Redis Server

#### Configure Environment Variable for SMTP Mail Server

- Edit `venv/bin/activate` file & add below parameters at the end of the file

```shell script
export EMAIL_USER=<email>
export EMAIL_PASSWORD=<password>
```


## Details about API

#### Create User

```shell script
curl -H "Content-Type: application/json" -X POST -d '{"first_name":"admin", "last_name":"admin", "email":"admin@gmail.com", "password":"admin", "country":"IN"}' -i "http://localhost:2222/api/v1.0/user/add"
```

#### Verify User

```shell script
curl -H "Content-Type: application/json" -X POST -d '{"email":"admin@gmail.com", "password":"admin"}' -i "http://localhost:2222/api/v1.0/user/verify"
```

#### Get User

Get Active User Detail

```shell script
curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/user/get"
```

Get All User Details

```shell script
curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/user/get?user=all"
```

Get Specific User Detail

```shell script
curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/user/get?user=admin@gmail.com"
```

#### Update User

```shell script
curl -H "Content-Type: application/json" -X PUT -u admin@gmail.com:admin -d '{"first_name":"admin", "last_name":"admin", "country":"IN"}' -i "http://localhost:2222/api/v1.0/user/update"
```

#### Update Password

```shell script
curl -H "Content-Type: application/json" -X PUT -u admin@gmail.com:admin -d '{"password":"admin"}' -i "http://localhost:2222/api/v1.0/user/update-password"
```

#### Delete User

```shell script
curl -X DELETE -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/user/delete"
```

#### Get COVID Data
Supported optional parameters are **country** & **date-range**

- If user didn't mention **country** in query-string parameter then it'll take active user's country

- If user didn't mention **start-date** & **end-date** in query-string parameter then it'll take past 15 days as date-range

- If user only mention **start-date** in query-string then system auto consider today's date as **end-date**

- If user only mention **end-date** in query-string then system auto consider **start-date** as end-date

```shell script
curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/covid"

curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/covid?start-date=2020-12-10&end-date=2020-12-20"

curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/covid?country=IN&start-date=2020-12-17"

curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/covid?country=IN&end-date=2020-12-15"

curl -X GET -u admin@gmail.com:admin -i "http://localhost:2222/api/v1.0/covid?country=IN&start-date=2020-12-05&end-date=2020-12-15"
```


## Key Features

- **Exponential Backoff Algorithm with Jitter**
- **Plotly Graph Library:** Create a Group Bar Chart from the gathered COVID data & save it as image
- **Asynchronous Task with the help of Redis Queue (RQ):** Sending image of COVID analysis as attachment in mail
