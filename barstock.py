
import itertools
import pandas as pd

from util import IngredientSpecifier

class Barstock(object):
    """ Wrap up a csv of bottle info with some helpful methods
    for data access and querying
    """
    # TODO move to own file
    def get_all_bottle_combinations(self, types):
        """ For a given list of ingredient types, return a list of lists
        where each list is a specific way to make the drink
        e.g. Martini passes in ['gin', 'vermouth'], gets [['Beefeater', 'Noilly Prat'], ['Knickerbocker', 'Noilly Prat']]
        """
        bottle_lists = [self.slice_on_type(t)['Bottle'].tolist() for t in types]
        opts = itertools.product(*bottle_lists)
        return opts

    def get_bottle_proof(self, bottle, type_):
        return self.get_bottle_field(bottle, type_, 'Proof')

    def get_bottle_category(self, bottle, type_):
        return self.get_bottle_field(bottle, type_, 'Category')

    def cost_by_bottle_and_volume(self, bottle, type_, amount, unit='oz'):
        per_unit = self.get_bottle_field(bottle, type_, '$/{}'.format(unit))
        return per_unit * amount

    def get_bottle_field(self, bottle, type_, field):
        if field not in self.df.columns:
            raise AttributeError("get-bottle-field '{}' not a valid field in the data".format(field))
        return self.get_bottle_by_type(bottle, type_).at[0, field]

    def get_bottle_by_type(self, bottle, type_):
        by_type = self.slice_on_type(type_)
        row = by_type[by_type['Bottle'] == bottle].reset_index(drop=True)
        if len(row) > 1:
            raise ValueError('{} "{}" has multiple entries in the input data!'.format(type_, bottle))
        return row

    def slice_on_type(self, type_):
        type_ = type_.lower()
        if type_ in ['rum', 'whiskey', 'tequila', 'vermouth']:
            return self.df[self.df['type'].str.contains(type_)]
        elif type_ == 'any spirit':
            return self.df[self.df.type.isin(['dry gin', 'rye whiskey', 'amber rum', 'dark rum', 'white rum', 'genever', 'brandy', 'aquavit'])]
            #return self.df[self.df['Category'] == 'Spirit']
        elif type_ == 'bitters':
            return self.df[self.df['Category'] == 'Bitters']
        else:
            return self.df[self.df['type'] == type_]

    @classmethod
    def load(cls, barstock_csv, include_all=False):
        obj = cls()
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
        obj.df = df
        return obj

