from flask_sqlalchemy import SQLAlchemy

import util

db = SQLAlchemy()

class User(db.Model):
    """ User where email address is account key
    """
    email = db.Column(db.String(120), primary_key=True, unique=True, nullable=False)
    password = db.Column(db.String)
    uuid_ = db.Column(db.String(36), unique=True)
    username = db.Column(db.String(80), nullable=True)
    authenticated = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(), default="")

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        self.uuid_ = util.get_uuid()
        if not self.role:
            self.role = "customer"

    def __repr__(self):
        return '<User {}>'.format(self.username)

    # Implement flask-login required functions
    @property
    def is_authenticated(self):
        """This property should return True if the user is authenticated,
        i.e. they have provided valid credentials.
        (Only authenticated users will fulfill the criteria of login_required.)
        """
        return self.authenticated

    @property
    def is_active(self):
        """This property should return True if this is an active user -
        in addition to being authenticated, they also have activated their account,
        not been suspended, or any condition your application has for rejecting an account.
        Inactive accounts may not log in (without being forced of course).
        """
        return True

    @property
    def is_anonymous(self):
        """This property should return True if this is an anonymous user.
        (Actual users should return False instead.)
        """
        return False

    def get_id(self):
        """This method must return a unicode that uniquely identifies this user,
        and can be used to load the user from the user_loader callback.
        Note that this must be a unicode - if the ID is natively an int
        or some other type, you will need to convert it to unicode.
        """
        return self.email
