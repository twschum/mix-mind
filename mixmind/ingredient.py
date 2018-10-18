import urllib
import copy

from sqlalchemy import and_, Boolean, DateTime, Column, Integer, ForeignKey, Enum, Float, Unicode
from sqlalchemy.exc import SQLAlchemyError

import util
from .database import db
from .compose_html import close

Categories = 'Spirit Liqueur Vermouth Bitters Syrup Juice Mixer Wine Beer Dry Ice'.split()

# key is the value that should exist in the CSV file,
# inner key is the name in the Model
display_name_mappings = {
    "Category":    {'k':  "Category",     'v':  util.as_utf8, 'csv': 1},
    "Ingredient":  {'k':  "Type",         'v':  util.as_utf8, 'csv': 2},
    "Kind":        {'k':  "Kind",         'v':  util.as_utf8, 'csv': 3},
    "In Stock":    {'k':  "In_Stock",     'v':  util.from_bool_from_num},
    "ABV":         {'k':  "ABV",          'v':  util.from_float, 'csv': 5},
    "Proof":       {'k':  "ABV",          'v':  lambda x: util.from_float(x) / 2.0},
    "Size (mL)":   {'k':  "Size_mL",      'v':  util.from_float, 'csv': 7},
    "Size (oz)":   {'k':  "Size_oz",      'v':  util.from_float},
    "Price Paid":  {'k':  "Price_Paid",   'v':  util.from_price_float, 'csv': 9},
    "$/mL":        {'k':  "Cost_per_mL",  'v':  util.from_price_float},
    "$/cL":        {'k':  "Cost_per_cL",  'v':  util.from_price_float},
    "$/oz":        {'k':  "Cost_per_oz",  'v':  util.from_price_float},
}

# TODO value constraints (e.g. 100% max abv, no negative price, etc.)
class Ingredient(db.Model):
    bar_id     = Column(Integer(), ForeignKey('bar.id'), primary_key=True)
    Category   = Column(Enum(*Categories))
    Type       = Column(Unicode(length=100), primary_key=True)
    Kind       = Column(Unicode(length=255), primary_key=True)
    In_Stock   = Column(Boolean(), default=True)
    ABV        = Column(Float(), default=0.0)
    Size_mL    = Column(Float(), default=0.0)
    Price_Paid = Column(Float(), default=0.0)
    # computed
    type_        = Column(Unicode(length=100))
    Size_oz      = Column(Float(), default=0.0)
    Cost_per_mL  = Column(Float(), default=0.0)
    Cost_per_cL  = Column(Float(), default=0.0)
    Cost_per_oz  = Column(Float(), default=0.0)

    def as_dict(self):
        data = copy.copy(self.__dict__)
        del data['_sa_instance_state']
        return data

    _csv_labels = sorted([label for label, val in display_name_mappings.iteritems() if val.get('csv')],
            key=lambda x: display_name_mappings[x].get('csv'))

    @classmethod
    def csv_heading(self):
        return u'{}\n'.format(','.join(self._csv_labels))

    def as_csv(self):
        return u'{}\n'.format(u','.join([unicode(self[display_name_mappings[attr]['k']])
                for attr in self._csv_labels]))

    def __str__(self):
        return u"|".join([self.Category, self.Type, self.Kind])

    def __repr__(self):
        return u"|".join([self.Category, self.Type, self.Kind])

    def __getitem__(self, field):
        return getattr(self, field)

    def __setitem__(self, field, value):
        return setattr(self, field, value)

    def _uid(self):
        return u"|".join([str(self.bar_id), self.Type, self.Kind])

    @classmethod
    def query_by_uid(cls, uid):
        bid, t, b = urllib.unquote(uid).split('|')
        return cls.query.filter_by(bar_id=int(bid), Type=t, Kind=b).one_or_none()

    def instock_toggle(self):
        # make a button to change the stock
        attrs = {'type': "submit", 'target': "_blank", 'name': "toggle-in-stock"}
        if self.In_Stock:
            attrs['class'] = "btn btn-small btn-success"
            attrs['value'] = "&check;"
        else:
            attrs['class'] = "btn btn-small btn-danger"
            attrs['value'] = "&times;"
        uid = close('', 'input', type="hidden", name='uid', value=urllib.quote(self._uid()))
        submit = close('', 'input', **attrs)
        return close('{}{}'.format(uid, submit),
                'form', id='stock-{}'.format(self._uid()), action="", method="post", role="form")

