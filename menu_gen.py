#!/usr/bin/env python
"""
Turn recipes json into a readable menu
TODO figure out how to handle recipes calling for an ingredient by name instead of type
TODO jsonschema for recipes
"""

import argparse
import json
import cPickle as pickle
import string
import itertools
from collections import OrderedDict, namedtuple
from fractions import Fraction

import pandas as pd
import numpy as np

import recipe as drink_recipe
import util


def get_ingredient_str(name, amount, unit):
    if isinstance(amount, basestring):
        amount_str = amount
        if amount == 'dash':
            unit = 'of'
        else:
            unit = ''
    elif unit == 'oz':
        amount_str = util.to_fraction(amount)
    else:
        amount_str = str(amount)
    if unit:
        unit += ' '
    return "{} {}{}".format(amount_str, unit, name)

def check_stat(field, tracker, example, drink_name):
    if example[field] > tracker[field]:
        tracker.update(example)
        tracker['name'] = drink_name
    return tracker

RecipeContent = namedtuple('RecipeContent', 'name,info,ingredients,variants,origin,examples,prep,ice,glass,max_cost')

def convert_to_menu(recipes, prices=True, all_=True, stats=True):
    """ Convert recipe json into readible format
    """

    menu = []
    menu_tuples = []
    most_expensive = {'cost':0}
    most_booze = {'drinks':0}
    most_abv = {'abv': 0}
    for drink_name, recipe in recipes.iteritems():
        lines = []
        lines.append(drink_name)
        unit = recipe.get('unit', 'oz')
        origin = recipe.get('origin', '')
        prep = recipe.get('prep', 'shake')
        ice = recipe.get('origin', 'cubed')
        glass = recipe.get('glass', 'up')

        info = recipe.get('info')
        if info:
            lines.append('\t"{}"'.format(info))

        ingredients = []
        for ingredient, amount in recipe['ingredients'].iteritems():
            item_str = get_ingredient_str(ingredient, amount, unit)
            lines.append('\t'+item_str)
            ingredients.append(item_str)

        for ingredient, amount in recipe.get('optional', {}).iteritems():
            item_str = "{} (optional)".format(get_ingredient_str(ingredient, amount, unit))
            lines.append('\t'+item_str)
            ingredients.append(item_str)

        misc = recipe.get('misc')
        if misc:
            lines.append("\t{}".format(misc))
            ingredients.append(misc)

        garnish = recipe.get('garnish')
        if garnish:
            garnish = "{}, for garnish".format(garnish)
            lines.append('\t'+garnish)
            ingredients.append(garnish)

        examples = recipe.get('examples', [])
        if examples:
            if prices:
                lines.append("\t    Examples: ".format(examples))
            for e in examples:
                most_expensive = check_stat('cost', most_expensive, e, drink_name)
                most_booze = check_stat('drinks', most_booze, e, drink_name)
                most_abv = check_stat('abv', most_abv, e, drink_name)
                if prices:
                    lines.append("\t    ${cost:.2f} | {abv:.2f}% ABV | {drinks:.2f} | {bottles}".format(**e))

        variants = recipe.get('variants', [])
        if variants:
            lines.append("\t    Variant{}:".format('s' if len(variants) > 1 else ''))
            for v in variants:
                lines.append("\t    {}".format(v))

        if all_ or examples:
            menu.append('\n'.join(lines))
            menu_tuples.append(RecipeContent(drink_name, info, ingredients, variants, origin, examples, prep, ice, glass, recipe.get('max_cost',0)))
        else:
            print "Can't make {}".format(drink_name)

    if stats:
        print "Most Expensive: {name}, ${cost:.2f} | {abv:.2f}% ABV | {drinks:.2f} | {bottles}".format(**most_expensive)
        print "Most Booze: {name}, ${cost:.2f} | {abv:.2f}% ABV | {drinks:.2f} | {bottles}".format(**most_booze)
        print "Highest ABV (estimate): {name}, ${cost:.2f} | {abv:.2f}% ABV | {drinks:.2f} | {bottles}".format(**most_abv)
    return menu, menu_tuples

def expand_recipes(df, recipes):

    for drink_name, recipe in recipes.iteritems():
        unit = recipe.get('unit', 'oz')
        prep = recipe.get('prep', 'shake')

        ingredients_names = []
        ingredients_amounts = []
        for name, amount in recipe['ingredients'].iteritems():
            if isinstance(amount, basestring):
                if amount == 'Top with':
                    amount = 3.0
                elif 'dash' in amount:
                    amount = util.dash_to_volume(amount, unit)
                elif 'tsp' in amount:
                    try:
                        amount = float(amount.split()[0])
                    except ValueError:
                        amount = float(Fraction(amount.split()[0]))
                    amount = util.tsp_to_volume(amount, unit)
                else:
                    continue
            ingredients_names.append(name)
            ingredients_amounts.append(amount)

        # calculate cost for every combination of ingredients for this drink
        examples = []
        for bottles in get_all_bottle_combinations(df, ingredients_names):
            sum_ = 0
            std_drinks = 0
            volume = 0
            display_list = []
            for bottle, type_, amount in zip(bottles, ingredients_names, ingredients_amounts):
                sum_ += cost_by_bottle_and_volume(df, bottle, type_, amount, unit)
                std_drinks += drinks_by_bottle_and_volume(df, bottle, type_, amount, unit)
                volume += amount
                # remove juice and such from the bottles listed
                category = get_bottle_by_type(df, bottle, type_).get_value(0, 'Category')
                if category in ['Vermouth', 'Liqueur', 'Bitters', 'Spirit']:
                    display_list.append(bottle)
            # add ~40% for stirred and ~65% for shaken
            water_added_by_prep = { } # TODO shake, stir, mix? something w/o ice
            volume *= 1.65 if prep == 'shake' else 1.4
            abv = 40.0 * (std_drinks*(1.5 if unit == 'oz' else 45.0) / volume)

            examples.append({'bottles': ', '.join(display_list),
                             'cost': sum_,
                             'abv': abv,
                             'drinks': std_drinks})
        recipes[drink_name]['examples'] = examples
        # calculate the max price
        price = 0
        if examples:
            prices = [e['cost'] for e in examples]
            price = max(prices)
        recipes[drink_name]['max_cost'] = price

    return recipes

class Barstock(object):
    """ Wrap up a csv of bottle info with some helpful methods
    for data access and querying
    """
    def get_all_bottle_combinations(self, types):
        bottle_lists = [slice_on_type(self.df, t)['Bottle'].tolist() for t in types]
        opts = itertools.product(*bottle_lists)
        return opts

    def get_bottle_proof(self, bottle, type_):
        return get_bottle_by_type(self.df, bottle, type_)['Proof'].median()

    def cost_by_bottle_and_volume(self, bottle, type_, amount, unit='oz'):
        per_unit = get_bottle_by_type(self.df, bottle, type_)['$/{}'.format(unit)].median()
        return per_unit * amount

    def get_bottle_by_type(self, bottle, type_):
        by_type = slice_on_type(self.df, type_)
        row = by_type[by_type['Bottle'] == bottle].reset_index(drop=True)
        if len(row) > 1:
            raise ValueError('{} "{}" has multiple entries in the input data!'.format(type_, bottle))
        return row

    def slice_on_type(self, type_):
        if type_ in ['rum', 'whiskey', 'tequila', 'vermouth']:
            return self.df[self.df['type'].str.contains(type_)]
        elif type_ == 'any spirit':
            return self.df[self.df.type.isin(['dry gin', 'rye whiskey', 'amber rum', 'dark rum', 'white rum', 'genever', 'brandy', 'aquavit'])]
            #return self.df[self.df['Category'] == 'Spirit']
        elif type_ == 'bitters':
            return self.df[self.df['Category'] == 'Bitters']
        else:
            return self.df[self.df['type'] == type_]

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

def get_parser():
    p = argparse.ArgumentParser(description="""
Example usage:
    ./program -v -d
""", formatter_class=argparse.RawTextHelpFormatter)
    subparsers = p.add_subparsers(help='commands', dest='command')

    p.add_argument('-v', dest='verbose', action='store_true')
    p.add_argument('-b', dest='barstock', default='Barstock - Sheet1.csv', help="Barstock csv filename")
    p.add_argument('-r', dest='recipes', default='recipes.json', help="Barstock csv filename")
    p.add_argument('-a', dest='all', action='store_true', help="Include all recipes regardless of stock")
    p.add_argument('-p', dest='prices', action='store_true', help="Calculate and display prices for example drinks based on stock")
    p.add_argument('-s', dest='stats', action='store_true', help="Just show some stats")
    txt_parser = subparsers.add_parser('txt', help='Not a pdf')
    txt_parser.add_argument('-w', dest='write', default=None, help="Save text menu out to a file")

    pdf_parser = subparsers.add_parser('pdf', help='Options for generating a pdf via LaTeX integration')
    pdf_parser.add_argument('pdf_filename', default=None, nargs='?', help="Basename of the pdf and tex files")
    pdf_parser.add_argument('-n', dest='ncols', default=2, type=int, help="Number of columns to use for the menu")
    pdf_parser.add_argument('-m', dest='markup', default=1, type=float, help="Drink markup: total = ceil(base_cost*markup)")
    pdf_parser.add_argument('-e', dest='examples', action='store_true', help="Show example recipes")
    pdf_parser.add_argument('-l', dest='liquor_list', action='store_true', help="Show list of the available ingredients")
    pdf_parser.add_argument('-L', dest='liquor_list_own_page', action='store_true', help="Show list of the available ingredients on a separate page")
    pdf_parser.add_argument('-D', dest='debug', action='store_true', help="Add debugging output")
    pdf_parser.add_argument('--align', action='store_true', help="Align drink names across columns")
    pdf_parser.add_argument('--save_cache', help="Pickle the generated menu that can be consumed by the LaTeX menu generator")
    pdf_parser.add_argument('--load_cache', help="Load the generated menu that can be consumed by the LaTeX menu generator")

    test_parser = subparsers.add_parser('test', help='whatever I need it to be')

    return p

def main():

    args = get_parser().parse_args()

    if args.command == 'test':
        with open('recipes.json') as fp:
            base_recipes = json.load(fp, object_pairs_hook=OrderedDict)

        new_recipes = []
        for name, recipe in base_recipes.iteritems():
            try:
                x = drink_recipe.DrinkRecipe(name, recipe)
            except:
                print name, recipe
                raise
            x.convert('oz', convert_nonstandard=False)
            print x
            new_recipes.append(x)

        return

    # TODO Fix the flow here to be less of a roundabout mess

    if args.command == 'pdf' and args.load_cache:
        with open(args.load_cache) as fp:
            menu_tuples = pickle.load(fp)
            print "Loaded recipe cache file {}".format(args.load_cache)
        ingredient_df = pandas.read_pickle(args.load_cache+'.dfpkl')
    else:
        with open(args.recipes) as fp:
            base_recipes = json.load(fp, object_pairs_hook=OrderedDict)
        recipes = [drink.Drink(name, recipe) for name, recipe in base_recipes.iteritems()]

        df = load_cost_df(args.barstock, args.all)
        #all_recipes = expand_recipes(df, base_recipes)
        #menu, menu_tuples = convert_to_menu(all_recipes, args.prices, args.all, args.stats)

    if args.command == 'pdf' and args.save_cache:
        with open(args.save_cache, 'w') as fp:
            pickle.dump(menu_tuples, fp)
            print "Saved recipe cache as {}".format(args.save_cache)
        ingredient_df.to_pickle(args.save_cache+'.dfpkl')

    if args.command == 'pdf' and args.pdf_filename:
        import formatted_menu
        ingredient_df = df if args.liquor_list or args.liquor_list_own_page else pd.DataFrame()
        formatted_menu.generate_recipes_pdf(menu_tuples, args.pdf_filename, args.ncols, args.align,
                args.debug, args.prices, args.markup, args.examples, ingredient_df, args.liquor_list_own_page)
        return

    if args.command == 'txt':
        if args.write:
            with open(args.write, 'w') as fp:
                fp.write('\n\n'.join(menu))
        else:
            print '\n\n'.join(menu)

if __name__ == "__main__":
    main()
