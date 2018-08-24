""" Pulls together modules to implement
user roles and authorization
"""
from flask_security import Security, SQLAlchemyUserDatastore

from . import db, app
from .models import User, Role
from .forms import ExtendedConfirmRegisterForm

user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore, confirm_register_form=ExtendedConfirmRegisterForm)
