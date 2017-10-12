#!/usr/bin/env python
"""
Turn recipes json into a readable menu
"""

import argparse
import json
from collections import OrderedDict

import pandas as pd
import numpy as np

def get_fraction(amount):
    numer, denom = float(amount).as_integer_ratio()
    if denom == 1:
        return numer
    whole = numer / denom
    numer = numer % denom
    return "{}{}/{}".format(str(whole)+' ' if whole > 0 else '', numer, denom)

def get_ingredient_amount(name, amount, unit):
    if isinstance(amount, basestring):
        amount_str = amount
    elif unit == 'oz':
        amount_str = get_fraction(amount)
    else:
        amount_str = str(amount)
    return "\t{} {} {}".format(amount_str, unit, name)

def convert_to_menu(recipes):
    """
    """

    drinks_text = []
    for drink_name, recipe in recipes.iteritems():
        lines = []
        lines.append(drink_name)
        unit = recipe.get('unit', 'oz')
        prep = recipe.get('prep', '')

        for ingredient, amount in recipe['ingredients'].iteritems():
            if ingredient == "optional":
                continue
            lines.append(get_ingredient_amount(ingredient, amount, unit))

        for ingredient, amount in recipe['ingredients'].get('optional', {}).iteritems():
            linestr = "{} (optional)".format(get_ingredient_amount(ingredient, amount, unit))
            lines.append(linestr)

        garnish = ingredients.get('garnish')
        if garnish:
            lines.append("\t{}, for garnish".format(garnish))

        print '\n'.join(lines)

def calculate_cost(price_df, ingredients, unit):
    pass

def generate_cost_df(barstock_csv):
    import ipdb; ipdb.set_trace()
    df = barstock.from_csv(barstock_csv)


def get_parser():
    p = argparse.ArgumentParser(description="""
Example usage:
    ./program -v -d
""", formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('-v', dest='verbose', action='store_true')

    return p

def main():

    args = get_parser().parse_args()

    df = generate_cost_df('Barstock - Sheet1.csv')

    with open('recipes.json') as fp:
        convert_to_menu(json.load(fp, object_pairs_hook=OrderedDict))


if __name__ == "__main__":
    main()
