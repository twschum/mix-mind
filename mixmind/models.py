from sqlalchemy.orm import relationship, backref
from sqlalchemy import Boolean, DateTime, Column, Integer, String, ForeignKey, Enum, Float, Text

from flask_security import UserMixin, RoleMixin

from . import db

class RolesUsers(db.Model):
    id = Column(Integer(), primary_key=True)
    user_id = Column('user_id', Integer(), ForeignKey('user.id'))
    role_id = Column('role_id', Integer(), ForeignKey('role.id'))

class Role(db.Model, RoleMixin):
    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))

class User(db.Model, UserMixin):
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    first_name = Column(String(255))
    last_name = Column(String(255))
    nickname = Column(String(255))
    password = Column(String(255))
    # TODO timezone rip
    last_login_at = Column(DateTime())
    current_login_at = Column(DateTime())
    last_login_ip = Column(String(100))
    current_login_ip = Column(String(100))
    login_count = Column(Integer)
    active = Column(Boolean())
    confirmed_at = Column(DateTime())
    roles = relationship('Role', secondary='roles_users', backref=backref('users', lazy='dynamic'))
    orders = relationship('Order', secondary='orders_users', backref=backref('users', lazy='dynamic'))

    def get_name(self, short=False):
        if self.nickname:
            return self.nickname
        else:
            if short:
                return self.first_name
            return '{} {}'.format(self.first_name, self.last_name)

class OrdersUsers(db.Model):
    id = Column(Integer(), primary_key=True)
    user_id = Column('user_id', Integer(), ForeignKey('user.id'))
    order_id = Column('order_id', Integer(), ForeignKey('order.id'))

class Order(db.Model):
    id = Column(Integer, primary_key=True)
    confirmed = Column(Boolean(), default=False)
    timestamp = Column(DateTime())
    recipe_name = Column(String(100))
    recipe_html = Column(Text())
    # maybe "bar" name
