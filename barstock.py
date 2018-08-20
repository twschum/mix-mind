import string
import itertools
import logging as log

try:
    import pandas as pd
    has_pandas = True
except ImportError:
    has_pandas = False

import util

from database import Base, db_session
from sqlalchemy import Boolean, DateTime, Column, Integer, String, ForeignKey, Enum, Float
from sqlalchemy.exc import SQLAlchemyError
import csv

Categories = 'Spirit Liqueur Vermouth Bitters Syrup Juice Mixer Wine Beer Dry Ice'.split()

db_uri = "mysql+mysqldb://root@/<dbname>?unix_socket=/cloudsql/<projectid>:<instancename>"

class Ingredient(Base):
    __tablename__  = 'ingredient'
    Category   = Column(Enum(*Categories))
    Type       = Column(String(), primary_key=True)
    Bottle     = Column(String(), primary_key=True)
    In_Stock   = Column(Boolean(), default=True)
    Proof      = Column(Float())
    Size_mL    = Column(Float())
    Price_Paid = Column(Float())
    Price_mL   = Column('$/mL', Float())

    def __str__(self):
        return "|".join([self.Category, self.Type, self.Bottle])

    def __getitem__(self, field):
        return getattr(self, field)

    def __setitem__(self, field, value):
        return setattr(self, field, value)

    display_name_mappings = {
        "Category": {'k': "Category", 'v': lambda x: x},
        "Type": {'k': "Type", 'v': lambda x: x},
        "Bottle": {'k': "Bottle", 'v': lambda x: x},
        "In Stock": {'k': "In_Stock", 'v': util.get_bool_from_int},
        "Size (mL)": {'k': "Size_mL", 'v': util.get_float},
        "Price Paid": {'k': "Price_Paid", 'v': util.get_price_float},
    }

def get_barstock_instance(csv_list, include_all=False):
    """ Factory for getting the right, initialized barstock
    """
    if has_pandas:
        return Barstock_DF.load(csv_list, include_all=include_all)
    else:
        return Barstock_SQL.loas(csv_list)

def _calculated_columns(thing):
    """ Given an object with the required fields,
    calculate and add the other fields
    """
    thing['Size (oz)'] = util.convert_units(thing['Size (mL)'], 'mL', 'oz')
    thing['$/mL'] = thing['Price Paid'] / thing['Size (mL)']
    thing['$/cL'] = thing['Price Paid']*10 / thing['Size (mL)']
    thing['$/oz'] = thing['Price Paid'] / thing['Size (oz)']

class Barstock(object):
    pass

class Barstock_SQL(Barstock):
    @classmethod
    def load(cls, barstock_csv, include_all=False):
        """Load the given CSVs"""
        if isinstance(barstock_csv, basestring):
            barstock_csv = [barstock_csv]
        ingredients = []
        for csv_file in barstock_csv:
            with open(csv_file) as fp:
                reader = csv.DictReader(fp)
                for row in reader:
                    if not row.get('Type') and not row.get('Bottle'):
                        continue # ignore rows without the required primary keys
                    clean_row = {Ingredient.display_name_mappings[k]['k'] : Ingredient.display_name_mappings[k]['v'](v)
                            for k,v in row.iteritems()
                            if k in Ingredient.display_name_mappings}
                    #ingredients.append(Ingredient(**clean_row))
                    try:
                        ingredient = Ingredient(**clean_row)
                        row = db_session.query(Ingredient).filter(Ingredient.Bottle == ingredient.Bottle, Ingredient.Type == ingredient.Type).one_or_none()
                        if row: # update
                            for k, v in clean_row.iteritems():
                                row[k] = v
                        else: # insert
                            db_session.add(ingredient)
                        db_session.commit()
                    except SQLAlchemyError as err:
                        log.error("{}: on row: {}".format(err, clean_row))
                        break
        #db_session.bulk_save_objects(ingredients)
        return cls()

class Barstock_DF(Barstock):
    """ Wrap up a csv of bottle info with some helpful methods
    for data access and querying
    """

    def __init__(self, df):
        self.df = df

    def get_all_bottle_combinations(self, specifiers):
        """ For a given list of ingredient specifiers, return a list of lists
        where each list is a specific way to make the drink
        e.g. Martini passes in ['gin', 'vermouth'], gets [['Beefeater', 'Noilly Prat'], ['Knickerbocker', 'Noilly Prat']]
        """
        bottle_lists = [self.slice_on_type(i)['Bottle'].tolist() for i in specifiers]
        opts = itertools.product(*bottle_lists)
        return opts

    def get_bottle_proof(self, ingredient):
        return self.get_bottle_field(ingredient, 'Proof')

    def get_bottle_category(self, ingredient):
        return self.get_bottle_field(ingredient, 'Category')

    def cost_by_bottle_and_volume(self, ingredient, amount, unit='oz'):
        per_unit = self.get_bottle_field(ingredient, '$/{}'.format(unit))
        return per_unit * amount

    def get_bottle_field(self, ingredient, field):
        if field not in self.df.columns:
            raise AttributeError("get-bottle-field '{}' not a valid field in the data".format(field))
        return self.get_ingredient_row(ingredient).at[0, field]

    def get_ingredient_row(self, ingredient):
        if ingredient.bottle is None:
            raise ValueError("ingredient {} has no bottle specified".format(ingredient.__repr__()))
        row = self.slice_on_type(ingredient)
        if len(row) > 1:
            raise ValueError('{} has multiple entries in the input data!'.format(ingredient.__repr__()))
        elif len(row) < 1:
            raise ValueError('{} has no entry in the input data!'.format(ingredient.__repr__()))
        return row

    def slice_on_type(self, specifier):
        type_ = specifier.what.lower()
        if type_ in ['rum', 'whiskey', 'whisky', 'tequila', 'vermouth']:
            type_ = 'whisk' if type_ == 'whisky' else type_
            matching = self.df[self.df['type'].str.contains(type_)]
        elif type_ == 'any spirit':
            matching = self.df[self.df.type.isin(['dry gin', 'rye whiskey', 'bourbon whiskey', 'amber rum', 'dark rum', 'white rum', 'genever', 'brandy', 'aquavit'])]
            #matching = self.df[self.df['Category'] == 'Spirit']
        elif type_ == 'bitters':
            matching = self.df[self.df['Category'] == 'Bitters']
        else:
            matching = self.df[self.df['type'] == type_]
        if specifier.bottle:
            return matching[matching['Bottle'] == specifier.bottle].reset_index(drop=True)
        else:
            return matching

    def sorted_df(self):
        return self.df.sort_values(['Category','Type','Price Paid'])


    def add_row(self, row):
        """ where row is a dict """
        _calculated_columns(row)
        row = {k:[v] for k,v in row.iteritems()}
        row = pd.DataFrame.from_dict(row)
        self.df = pd.concat([self.df, row])

    @classmethod
    def load(cls, barstock_csv, include_all=False):
        if isinstance(barstock_csv, basestring):
            barstock_csv = [barstock_csv]
        # TODO validate columns, merge duplicates
        df = pd.concat([pd.read_csv(filename) for filename in barstock_csv])
        df = df.drop_duplicates(['Type', 'Bottle'])
        df = df.dropna(subset=['Type'])
        # convert money columns to floats
        for col in [col for col in df.columns if '$' in col or 'Price' in col]:
            df[col] = df[col].replace('[\$,]', '', regex=True).astype(float)
        df = df.fillna(0)
        _calculated_columns(df)
        df['type'] = map(string.lower, df['Type'])
        df['Category'] = pd.Categorical(df['Category'], cls.Categories)

        # drop out of stock items
        if not include_all:
            #log debug how many dropped
            df = df[df["In Stock"] > 0]
        return cls(df)

