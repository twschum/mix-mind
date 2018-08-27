""" Pulls together modules to implement
user roles and authorization
"""
from flask_security import Security, SQLAlchemyUserDatastore
from flask_security.forms import ConfirmRegisterForm
from wtforms import validators, StringField

from . import db, app
from .models import User, Role

class ExtendedConfirmRegisterForm(ConfirmRegisterForm):
    # flask-security user registration
    first_name = StringField('First Name', validators=[validators.required()])
    last_name = StringField('Last Name', validators=[validators.required()])
    nickname = StringField('Nickname')

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore, confirm_register_form=ExtendedConfirmRegisterForm)
