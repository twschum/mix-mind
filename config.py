""" Configuration of app.config dict
"""
import os.path
import logging
log = logging.getLogger()

# flask-sqlalchemy
SQLALCHEMY_TRACK_MODIFICATIONS = False # explicitly remove deprecated feature

# flask-mail (used by flask-security)
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True

# flask-security
SECURITY_CONFIRMABLE   =  True
SECURITY_REGISTERABLE  =  True
SECURITY_RECOVERABLE   =  True
SECURITY_TRACKABLE     =  True
SECURITY_CHANGEABLE    =  True
SECURITY_POST_LOGIN_VIEW = "/user_post_login"
SECURITY_POST_CONFIRM_VIEW = "/user_post_confirm_email"
SECURITY_EMAIL_SUBJECT_REGISTER = "Welcome to Mix-Mind Live"
SECURITY_EMAIL_SUBJECT_PASSWORD_NOTICE = "[Mix-Mind] Your password has been reset"
SECURITY_EMAIL_SUBJECT_PASSWORD_RESET = "[Mix-Mind] Password reset instructions"
SECURITY_EMAIL_SUBJECT_CONFIRM = "[Mix-Mind] Please confirm your email"

# logging
#path = app.config['LOGGING_PATH']
#os.makedirs(path, exist_ok=True)
#info_fh = RotatingFileHandler(os.path.join(path, 'mixmind.log'), maxBytes=10000000, backupCount=3)
#info_fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
#info_fh.setLevel(logging.INFO)
#log = logging.getLogger()

# default recipes and ingredients to load
MIXMIND_DIR = os.path.abspath(os.path.curdir)
MIXMIND_RECIPES_DIR = "recipes/"
MIXMIND_INGREDIENTS_DIR = "ingredients/"

MIXMIND_DEFAULT_RECIPES = ["recipes_schubar.json", "IBA_all.json"]
MIXMIND_DEFAULT_INGREDIENTS = ["12BBplus.csv"]

MIXMIND_DEFAULT_BAR_NAME = "Home Bar"

# time
TIMEZONE = 'US/Eastern'
HUMAN_FORMAT = 'ddd, D MMM YYYY, at LT'
PRECISE_FORMAT = 'YYYY-MM-DD HH:mm:ss'
