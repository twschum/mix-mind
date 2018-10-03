from os import getenv

env = getenv('FLASK_ENV')
if not env:
    raise RuntimeError("Missing FLASK_ENV for target configuration!")

# make these users admins, triggered when they view their user page
MAKE_ADMIN = ['you@mail.com']

# mail config for flask-security
MAIL_USERNAME = 'my.barman@gmail.com'
MAIL_PASSWORD = "password"
MAIL_DEFAULT_SENDER = MAIL_USERNAME
SECURITY_EMAIL_SENDER = MAIL_USERNAME

# flask general secret configuration
SECRET_KEY = "secret-key"
SECURITY_PASSWORD_SALT = "mmm...salty!"

# format of a link to venmo user profile
VENMO_LINK = "https://venmo.com/code?user_id={}"

# PythonAnywhere environments
PyA_USER = "username"
PyA_PASS = "password"
PyA_HOST = "{}.mysql.pythonanywhere-services.com".format(PyA_USER)
PyA_URI = "mysql+mysqldb://{user}:{passw}@{host}/{user}${dbname}"

# local env using `flask run`
if env == 'development':
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"

# PythonAnywhere environments
elif env == 'development-PyA':
    SQLALCHEMY_DATABASE_URI = PyA_URI.format(user=PyA_USER, passw=PyA_PASS, host=PyA_HOST,
            dbname="test")
elif env == 'production-PyA':
    SQLALCHEMY_DATABASE_URI = PyA_URI.format(user=PyA_USER, passw=PyA_PASS, host=PyA_HOST,
            dbname="production")

else:
    raise RuntimeError('Unknown FLASK_ENV "{}"'.format(env))
