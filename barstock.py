
import string
import itertools
import pandas as pd

from util import IngredientSpecifier

class Barstock(object):
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
        if type_ in ['rum', 'whiskey', 'tequila', 'vermouth']:
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

    @classmethod
    def load(cls, barstock_csv, include_all=False):
        df = pd.read_csv(barstock_csv)
        df = df.dropna(subset=['Type'])
        df['type'] = map(string.lower, df['Type'])

        # convert money columns to floats
        for col in [col for col in df.columns if '$' in col]:
            df[col] = df[col].replace('[\$,]', '', regex=True).astype(float)

        df['Proof'] = df['Proof'].fillna(0)

        # drop out of stock items
        if not include_all:
            #log debug how many dropped
            df = df[df["In Stock"] != 0]
        return cls(df)

