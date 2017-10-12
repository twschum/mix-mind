#!/usr/bin/env python
"""
Turn recipes json into a readable menu
"""

import argparse
import json
import string
import itertools
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
    """ Convert recipe json into readible format
    """

    for drink_name, recipe in recipes.iteritems():
        lines = []
        lines.append(drink_name)
        unit = recipe.get('unit', 'oz')
        prep = recipe.get('prep', '')

        for ingredient, amount in recipe['ingredients'].iteritems():
            lines.append(get_ingredient_amount(ingredient, amount, unit))

        for ingredient, amount in recipe.get('optional', {}).iteritems():
            linestr = "{} (optional)".format(get_ingredient_amount(ingredient, amount, unit))
            lines.append(linestr)

        garnish = recipe.get('garnish')
        if garnish:
            lines.append("\t{}, for garnish".format(garnish))

        examples = recipe.get('examples')
        if examples:
            lines.append("\t    Examples: ".format(examples))
            for e in examples:
                lines.append("\t    ${:.2f} | {}".format(e.values()[0], e.keys()[0]))

        print '\n'.join(lines)

def expand_recipes(df, recipes):

    for drink_name, recipe in recipes.iteritems():

        # ignore non-numeric ingredients
        ingredients_names = [k for k,v in recipe['ingredients'].iteritems() \
                if not isinstance(v, basestring)]
        ingredients_amounts = [v for k,v in recipe['ingredients'].iteritems() \
                if not isinstance(v, basestring)]

        # calculate cost for every combination of ingredients for this drink
        examples = []
        for bottles in get_all_bottle_combinations(df, ingredients_names):
            sum_ = 0
            for bottle, amount in zip(bottles, ingredients_amounts):
                sum_ += cost_by_bottle_and_volume(df, bottle, amount)
            examples.append({','.join(bottles) : sum_})
        recipes[drink_name]['examples'] = examples

    return recipes


def cost_by_bottle_and_volume(df, bottle, amount, unit='oz'):
    # TODO bottle and type comparison
    per_unit = min(df[df['Bottle'] == bottle]['$/{}'.format(unit)])
    return per_unit * amount

def get_all_bottle_combinations(df, types):
    bottle_lists = [slice_on_type(df, t)['Bottle'].tolist() for t in types]
    opts = itertools.product(*bottle_lists)
    return opts

def slice_on_type(df, type_):
    return df[df['type'] == type_]


def calculate_cost(price_df, ingredients, unit):
    pass


def generate_cost_df(barstock_csv):
    df = pd.read_csv(barstock_csv)
    df = df.dropna(subset=['Type'])
    df['type'] = map(string.lower, df['Type'])

    # convert money columns to floats
    for col in [col for col in df.columns if '$' in col]:
        df[col] = df[col].replace('[\$,]', '', regex=True).astype(float)

    return df

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
        base_recipes = json.load(fp, object_pairs_hook=OrderedDict)

    all_recipes = expand_recipes(df, base_recipes)

    convert_to_menu(all_recipes)


if __name__ == "__main__":
    main()
