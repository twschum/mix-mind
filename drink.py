"""
Drink class encapsulates how a drink recipe is calculated and formulated,
can provide itself as a dict/json, tuple of values, do conversions, etc.
Just generally make it better OOP
"""

import util

class Drink(object):
    """ Initialize a drink with a handle to the available stock data and its recipe json
    """

    @util.default_initializer
    def __init__(self, stock_df, name, recipe_dict):
        pass

