import string
import itertools
import codecs
import logging as log

try:
    import pandas as pd
    has_pandas = True
except ImportError:
    has_pandas = False

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from . import util
from .database import db
from .ingredient import Categories, Ingredient, display_name_mappings

def get_barstock_instance(csv_list, use_sql=False, bar_id=None, include_all=False):
    """ Factory for getting the right, initialized barstock
    """
    if isinstance(csv_list, str):
        csv_list = [csv_list]
    if use_sql or not has_pandas:
        if bar_id is None:
            raise ValueError("Valid bar object required for sql barstock")
        barstock = Barstock_SQL()
        barstock.load_from_csv(csv_list, bar_id)
        return barstock
    elif has_pandas:
        return Barstock_DF.load(csv_list, include_all=include_all)
    else:
        raise NotImplementedError("No pandas and not using sql version of Barstock")

def _calculated_columns(thing):
    """ Given an object with the required fields,
    calculate and add the other fields
    """
    thing['Size (oz)'] = util.convert_units(thing['Size (mL)'], 'mL', 'oz')
    thing['$/mL'] = thing['Price Paid'] / thing['Size (mL)']
    thing['$/cL'] = thing['Price Paid']*10 / thing['Size (mL)']
    thing['$/oz'] = thing['Price Paid'] / thing['Size (oz)']

def _update_computed_fields(row):
    """ Uses clean names
    """
    row.type_ = row.Type.lower()
    try:
        row.Size_oz = util.convert_units(row.Size_mL, 'mL', 'oz')
        row.Cost_per_mL = row.Price_Paid  / row.Size_mL
        row.Cost_per_cL = row.Price_Paid*10  / row.Size_mL
        row.Cost_per_oz = row.Price_Paid  / row.Size_oz
    except ZeroDivisionError:
        log.warning("Ingredient missing size field: {}".format(row))

class DataError(Exception):
    pass

class Barstock(object):
    pass

class Barstock_SQL(Barstock):
    def __init__(self, bar_id):
        self.bar_id = bar_id
    def load_from_csv(self, csv_list, bar_id, replace_existing=True):
        """Load the given CSVs
        if replace_existing is True, will replace the whole db for this bar
        bar_id is the active bar
        """
        if replace_existing:
            rows_deleted = Ingredient.query.filter_by(bar_id=bar_id).delete()
            db.session.commit()
            log.info("Dropped {} rows for {} table".format(rows_deleted, Ingredient.__tablename__))
        for csv_file in csv_list:
            with open(csv_file) as fp:
                # nom the bom
                if fp.read(len(codecs.BOM_UTF8)) != codecs.BOM_UTF8:
                    fp.seek(0)
                reader = util.UnicodeDictReader(fp)
                for row in reader:
                    try:
                        self.add_row(row, bar_id)
                    except DataError as e:
                        log.warning(e)

    def add_row(self, row, bar_id):
        """ where row is a dict of fields from the csv
        returns the Model object for the updated/inserted row"""
        if not row.get('Ingredient', row.get('Type')) or not row.get('Kind', row.get('Bottle')):
            log.debug("Primary key (Ingredient, Kind) missing, skipping ingredient: {}".format(row))
            return
        try:
            clean_row = {display_name_mappings[k]['k'] : display_name_mappings[k]['v'](v)
                    for k,v in row.items()
                    if k in display_name_mappings}
        except UnicodeDecodeError:
            log.warning("UnicodeDecodeError for ingredient: {}".format(row))
            return None
        try:
            ingredient = Ingredient(bar_id=bar_id, **clean_row)
            row = Ingredient.query.filter_by(bar_id=ingredient.bar_id,
                    Kind=ingredient.Kind, Type=ingredient.Type).one_or_none()
            if row: # update
                for k, v in clean_row.items():
                    row[k] = v
                _update_computed_fields(row)
                db.session.commit()
                return row
            else: # insert
                _update_computed_fields(ingredient)
                db.session.add(ingredient)
                db.session.commit()
                return ingredient
        except SQLAlchemyError as err:
            msg = "{}: on row: {}".format(err, clean_row)
            raise DataError(msg)

    def get_all_kind_combinations(self, specifiers):
        """ For a given list of ingredient specifiers, return a list of lists
        where each list is a specific way to make the drink
        e.g. Martini passes in ['gin', 'vermouth'], gets [['Beefeater', 'Noilly Prat'], ['Knickerbocker', 'Noilly Prat']]
        """
        kind_lists = [[b.Kind for b in self.slice_on_type(i)] for i in specifiers]
        opts = itertools.product(*kind_lists)
        return opts

    def get_kind_abv(self, ingredient):
        return self.get_kind_field(ingredient, 'ABV')

    def get_kind_category(self, ingredient):
        return self.get_kind_field(ingredient, 'Category')

    def cost_by_kind_and_volume(self, ingredient, amount, unit='oz'):
        per_unit = self.get_kind_field(ingredient, 'Cost_per_{}'.format(unit))
        return per_unit * amount

    def get_kind_field(self, ingredient, field):
        if field not in list(Ingredient.__table__.columns.keys()):
            raise AttributeError("get-kind-field '{}' not a valid field in the data".format(field))
        return self.get_ingredient_row(ingredient)[field]

    def get_ingredient_row(self, ingredient):
        if ingredient.kind is None:
            raise ValueError("ingredient {} has no kind specified".format(ingredient.__repr__()))
        row = self.slice_on_type(ingredient)
        if len(row) > 1:
            raise ValueError('{} has multiple entries in the input data!'.format(ingredient.__repr__()))
        elif len(row) < 1:
            raise ValueError('{} has no entry in the input data!'.format(ingredient.__repr__()))
        return row[0]

    # TODO sqlqlchemy exception decorator?
    def slice_on_type(self, specifier):
        """ Return query results for rows matching an ingredient specifier
        Handles several special cases
        """
        type_ = specifier.ingredient.lower()
        if type_ in ['rum', 'whiskey', 'whisky', 'tequila', 'vermouth']:
            type_ = 'whisk' if type_ == 'whisky' else type_
            filter_ = Ingredient.type_.like('%{}%'.format(type_))
        elif type_ == 'any spirit':
            spirits = ['dry gin', 'rye whiskey', 'bourbon whiskey', 'amber rum', 'dark rum', 'white rum', 'genever', 'cognac', 'brandy', 'aquavit']
            filter_ = Ingredient.type_.in_(spirits)
        elif type_ == 'bitters':
            filter_ = Ingredient.Category == 'Bitters'
        else:
            filter_ = Ingredient.type_ == type_

        if specifier.kind:
            filter_ = and_(filter_, Ingredient.Kind == specifier.kind)

        filter_ = and_(filter_, Ingredient.bar_id == self.bar_id, Ingredient.In_Stock == True)
        return Ingredient.query.filter(filter_).all()

    def to_csv(self):
        cols = list(Ingredient.__table__.columns.keys())
        result = [','.join(cols)]
        for row in Ingredient.query.all():
            result.append(','.join([str(row[col]) for col in cols]))
        return '\n'.join(result)


class Barstock_DF(Barstock):
    """ Wrap up a csv of kind info with some helpful methods
    for data access and querying
    """

    def __init__(self, df):
        self.df = df

    def get_all_kind_combinations(self, specifiers):
        """ For a given list of ingredient specifiers, return a list of lists
        where each list is a specific way to make the drink
        e.g. Martini passes in ['gin', 'vermouth'], gets [['Beefeater', 'Noilly Prat'], ['Knickerbocker', 'Noilly Prat']]
        """
        kind_lists = [self.slice_on_type(i)['Kind'].tolist() for i in specifiers]
        opts = itertools.product(*kind_lists)
        return opts

    def get_kind_abv(self, ingredient):
        return self.get_kind_field(ingredient, 'ABV')

    def get_kind_category(self, ingredient):
        return self.get_kind_field(ingredient, 'Category')

    def cost_by_kind_and_volume(self, ingredient, amount, unit='oz'):
        per_unit = self.get_kind_field(ingredient, '$/{}'.format(unit))
        return per_unit * amount

    def get_kind_field(self, ingredient, field):
        if field not in self.df.columns:
            raise AttributeError("get-kind-field '{}' not a valid field in the data".format(field))
        return self.get_ingredient_row(ingredient).at[0, field]

    def get_ingredient_row(self, ingredient):
        if ingredient.kind is None:
            raise ValueError("ingredient {} has no kind specified".format(ingredient.__repr__()))
        row = self.slice_on_type(ingredient)
        if len(row) > 1:
            raise ValueError('{} has multiple entries in the input data!'.format(ingredient.__repr__()))
        elif len(row) < 1:
            raise ValueError('{} has no entry in the input data!'.format(ingredient.__repr__()))
        return row

    def slice_on_type(self, specifier):
        type_ = specifier.ingredient.lower()
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
        if specifier.kind:
            return matching[matching['Kind'] == specifier.kind].reset_index(drop=True)
        else:
            return matching

    def sorted_df(self):
        return self.df.sort_values(['Category','Type','Price Paid'])


    def add_row(self, row):
        """ where row is a dict """
        _calculated_columns(row)
        row = {k:[v] for k,v in row.items()}
        row = pd.DataFrame.from_dict(row)
        self.df = pd.concat([self.df, row])

    @classmethod
    def load(cls, barstock_csv, include_all=False):
        if isinstance(barstock_csv, str):
            barstock_csv = [barstock_csv]
        # TODO validate columns, merge duplicates
        df = pd.concat([pd.read_csv(filename) for filename in barstock_csv])
        df = df.drop_duplicates(['Type', 'Kind'])
        df = df.dropna(subset=['Type'])
        # convert money columns to floats
        for col in [col for col in df.columns if '$' in col or 'Price' in col]:
            df[col] = df[col].replace('[\$,]', '', regex=True).astype(float)
        df = df.fillna(0)
        _calculated_columns(df)
        df['type'] = list(map(string.lower, df['Type']))
        df['Category'] = pd.Categorical(df['Category'], Categories)

        # drop out of stock items
        if not include_all:
            #log debug how many dropped
            df = df[df["In Stock"] > 0]
        return cls(df)

