from sqlalchemy.orm import relationship, backref
from sqlalchemy import Boolean, DateTime, Column, Integer, String, ForeignKey, Enum, Float, Text

import pendulum

from flask_security import UserMixin, RoleMixin

from . import db
from .util import VALID_UNITS

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
    email = Column(String(127), unique=True)
    first_name = Column(String(127))
    last_name = Column(String(127))
    nickname = Column(String(127))
    password = Column(String(127))
    # TODO timezone rip
    last_login_at = Column(DateTime())
    current_login_at = Column(DateTime())
    last_login_ip = Column(String(63))
    current_login_ip = Column(String(63))
    login_count = Column(Integer)
    active = Column(Boolean())
    confirmed_at = Column(DateTime())
    roles = relationship('Role', secondary='roles_users', backref=backref('users', lazy='dynamic')) # many to many
    orders = relationship('Order', back_populates="user", foreign_keys='Order.user_id')# primaryjoin="User.id==Order.user_id") # one to many
    orders_served = relationship('Order', back_populates="bartender", foreign_keys='Order.bartender_id')#primaryjoin="User.id==Order.bartender_id") # one to many (for bartenders)
    works_at = relationship('Bar', secondary='bartenders', backref=backref('bartenders', lazy='dynamic')) # many to many
    venmo_id = Column(String(63)) # venmo id as a string


    def get_name(self, short=False):
        if short:
            if self.nickname:
                return self.nickname
            else:
                return self.first_name
        return '{} {}'.format(self.first_name, self.last_name)

    def get_name_with_email(self):
        return u'{} ({})'.format(self.get_name(short=True), self.email)

    def get_role_names(self):
        return ', '.join([role.name for role in self.roles])

    def get_bar_names(self):
        return ', '.join([bar.cname for bar in self.works_at])

class Order(db.Model):
    id = Column(Integer, primary_key=True)
    bar_id = Column(Integer, ForeignKey('bar.id'))
    user_id = Column(Integer, ForeignKey('user.id'))
    bartender_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates="orders", foreign_keys=[user_id])
    bartender = relationship('User', back_populates="orders_served", foreign_keys=[bartender_id])
    timestamp = Column(DateTime())
    confirmed = Column(DateTime())
    recipe_name = Column(String(127))
    recipe_html = Column(Text())

    def where(self):
        bar = Bar.query.filter_by(id=self.bar_id).one_or_none()
        if bar:
            return bar.name

    def time_to_confirm(self):
        if not self.confirmed:
            return "N/A"
        diff = pendulum.instance(self.confirmed) - pendulum.instance(self.timestamp)
        return "{} minutes, {} seconds".format(diff.minutes, diff.remaining_seconds)


class Bar(db.Model):
    id = Column(Integer(), primary_key=True)
    cname = Column(String(63), unique=True) # unique name for finding the bar
    name = Column(String(63))
    tagline = Column(String(255), default="Tips &mdash; always appreciated, never required")
    is_active = Column(Boolean(), default=False)
    bartender_on_duty = Column(Integer(), ForeignKey('user.id'))
    ingredients = relationship('Ingredient') # one to many
    orders = relationship('Order') # one to many
    # browse display settings
    markup     =  Column(Float(),    default=1.10)
    prices     =  Column(Boolean(),  default=True)
    stats      =  Column(Boolean(),  default=False)
    examples   =  Column(Boolean(),  default=False)
    convert    =  Column(Enum(*(['']+VALID_UNITS)), default='oz')
    prep_line  =  Column(Boolean(),  default=False)
    origin     =  Column(Boolean(),  default=False)
    info       =  Column(Boolean(),  default=True)
    variants   =  Column(Boolean(),  default=False)
    summarize  =  Column(Boolean(),  default=True)

class Bartenders(db.Model):
    id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey('user.id'))
    bar_id = Column(Integer(), ForeignKey('bar.id'))

