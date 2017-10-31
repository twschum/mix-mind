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
import operator

import pandas as pd

import recipe as drink_recipe
import util

def filter_recipes(recipes, filter_options):
    reduce_fn = any if filter_options.use_or else all
    recipes = [recipe for recipe in recipes if recipe.can_make or filter_options.all]
    if filter_options.include:
        recipes = [recipe for recipe in recipes if
                reduce_fn((recipe.contains_ingredient(ingredient) for ingredient in filter_options.include))]
    if filter_options.exclude:
        recipes = [recipe for recipe in recipes if
                reduce_fn((not recipe.contains_ingredient(ingredient) for ingredient in filter_options.exclude))]
    return recipes


class StatTracker(dict):
    # mutable class variables
    _title_width = 0
    _name_width = 0

    def __init__(self, attr, magnitude, str_title):
        if magnitude not in ('max', 'min'):
            raise ValueError('StatTracker magnitude must be "max" or "min"')
        self.op = operator.lt if magnitude == 'min' else operator.gt
        self.stat = '{}_{}'.format(magnitude, attr)
        self.val_attr = attr
        self.val = float('inf') if magnitude == 'min' else 0.0
        self['title'] = str_title
        if len(str_title) > StatTracker._title_width:
            StatTracker._title_width = len(str_title)

    def __str__(self):
        return "{{title:{}}} | {{drink_name:{}}} | ${{cost:.2f}} | {{abv:>5.2f}}% ABV | {{std_drinks:.2f}} | {{bottles}}"\
            .format(self._title_width+1, self._name_width+1).format(**self)

    def update_stat(self, recipe):
        example = getattr(recipe.stats, self.stat)
        ex_val = getattr(example, self.val_attr)
        if self.op(ex_val, self.val):
            self.val = ex_val
            self.update(example._asdict())
            self['drink_name'] = recipe.name
            if len(recipe.name) > StatTracker._name_width:
                StatTracker._name_width = len(recipe.name)

def report_stats(recipes):
    most_expensive = StatTracker('cost', 'max', 'Most Expensive')
    most_booze = StatTracker('std_drinks', 'max', 'Most Std Drinks')
    most_abv = StatTracker('abv', 'max', 'Highest Estimated ABV')
    least_expensive = StatTracker('cost', 'min', 'Least Expensive')
    least_booze = StatTracker('std_drinks', 'min', 'Fewest Std Drinks')
    least_abv = StatTracker('abv', 'min', 'Lowest Estimated ABV')
    for recipe in recipes:
        if recipe.calculate_stats():
            most_expensive.update_stat(recipe)
            most_booze.update_stat(recipe)
            most_abv.update_stat(recipe)
            least_expensive.update_stat(recipe)
            least_booze.update_stat(recipe)
            least_abv.update_stat(recipe)
    print
    print most_expensive
    print most_booze
    print most_abv
    print least_expensive
    print least_booze
    print least_abv
    print

def convert_to_menu(recipes, prices=True, all_=True, stats=True):
    """ Convert recipe json into readable format
    """

    menu = []
    menu_tuples = []
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

    return menu, menu_tuples

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

def get_parser():
    p = argparse.ArgumentParser(description="""
MixMind Drink Menu Generator by twschum
You'll need:
 - A json file of recipes  TODO add a jsonschema
{{
    "Martini": {{
        "info": "The King of Cocktails",
        "ingredients": {{
            "dry gin": 2.5,
            "dry vermouth": 0.5
        }},
        "optional": {{
            "orange bitters": "dash"
        }},
        "variants": ["Reverse Martini: 5 parts vermouth to 1 part gin",
                     "Perfect Martini: equal parts dry and sweet vermouth"],
        "unit": "oz",
        "prep": "stir",
        "ice": "none",
        "glass": "martini",
        "garnish": "Lemon twist or olives"
    }}
}}
 - A csv of liquer bottles based on the following format:
Category  Type              Bottle           In Stock  Proof  Size (mL)  Price Paid  Size (oz)  $/mL    $/oz
Spirit    Rye Whiskey       Bulleit Rye      1         90     750        $28.96      25.4       $0.039  $1.14
Spirit    Dry Gin           New Amsterdam    0         88     1750       $25.49      59.2       $0.015  $0.43
Liqueur   Orange Liqueur    Triple Sec       1         30     750        $5.99       25.4       $0.008  $0.24
Vermouth  Dry Vermouth      Noilly Prat Dry  1         32     375        $6.99       12.7       $0.019  $0.55
Bitters   Aromatic Bitters  Angostura        1         89.4   118        $7.95       4.0        $0.067  $1.99
Syrup     Simple Syrup      Homemade         1         0      4000       $2.79       135.3      $0.001  $0.02
Juice     Lemon Juice       Fresh            1         0      45         $0.80       1.5        $0.018  $0.53
Mixer     Club Soda         Club Soda        0         0      178        $1.00       6.0        $0.006  $0.17

Example usage:
    {} -b 'Barstock.csv' -r 'my_recipes.json' -p -e -i lime rum -x 'lemon juice'  pdf my_menu -n 2 -l
""".format(__file__), formatter_class=argparse.RawTextHelpFormatter)
    subparsers = p.add_subparsers(help='commands', dest='command')

    # core parameters
    p.add_argument('-v', dest='verbose', action='store_true')
    p.add_argument('-b', dest='barstock', default='Barstock - Sheet1.csv', help="Barstock csv filename")
    p.add_argument('-r', dest='recipes', default='recipes.json', help="Recipes json filename")
    p.add_argument('--save_cache', action='store_true', help="Pickle the generated recipes to cache them for later use (e.g. a quicker build of the pdf)")
    p.add_argument('--load_cache', action='store_true', help="Load the generated recipes from cache for use")

    # display options
    p.add_argument('-p', '--prices', action='store_true', help="Display prices for drinks based on stock")
    p.add_argument('-s', '--stats', action='store_true', help="Print out a detailed statistics block for the selected recipes")
    p.add_argument('-e', '--examples', action='store_true', help="Show specific examples of a recipe based on the ingredient stock")
    p.add_argument('-g', '--all-ingredients', action='store_true', help="Show every ingredient instead of just the main liquors with each example")
    p.add_argument('-m', dest='markup', default=1.2, type=float, help="Drink markup: price = ceil((base_cost+1)*markup)")

    # filtering options
    p.add_argument('-a', '--all', action='store_true', help="Include all ingredients from barstock whether or not that are marked in stock")
    p.add_argument('-i', dest='include', nargs='+', help="Filter by ingredient(s) that must be contained in the recipe")
    p.add_argument('-x', dest='exclude', nargs='+', help="Filter by ingredient(s) that must NOT be contained in the recipe")
    p.add_argument('-or', dest='use_or', action='store_true', help="use logical OR for included and excluded ingredient lists instead of default AND")

    # txt output
    txt_parser = subparsers.add_parser('txt', help='Simple plain text output')
    txt_parser.add_argument('--names', action='store_true', help="Show the names of drinks only")
    txt_parser.add_argument('-w', dest='write', default=None, help="Save text menu out to a file")

    # pdf (latex) output and options
    pdf_parser = subparsers.add_parser('pdf', help='Options for generating a pdf via LaTeX integration')
    pdf_parser.add_argument('pdf_filename', help="Basename of the pdf and tex files generated")
    pdf_parser.add_argument('-n', dest='ncols', default=2, type=int, help="Number of columns to use for the menu")
    pdf_parser.add_argument('-l', dest='liquor_list', action='store_true', help="Show list of the available ingredients")
    pdf_parser.add_argument('-L', dest='liquor_list_own_page', action='store_true', help="Show list of the available ingredients on a separate page")
    pdf_parser.add_argument('-D', dest='debug', action='store_true', help="Add debugging output to the pdf")
    pdf_parser.add_argument('--align', action='store_true', help="Align drink names across columns")

    # Do alternate things
    test_parser = subparsers.add_parser('test', help='whatever I need it to be')

    return p

# make passing a bunch of options around a bit cleaner
DisplayOptions = namedtuple('DisplayOptions', 'prices,stats,examples,all_ingredients,markup')
FilterOptions = namedtuple('FilterOptions', 'all,include,exclude,use_or')
PdfOptions = namedtuple('PdfOptions', 'pdf_filename,ncols,liquor_list,liquor_list_own_page,debug,align')
def bundle_options(tuple_class, args):
    return tuple_class(*(getattr(args, field) for field in tuple_class._fields))

def main():

    args = get_parser().parse_args()
    display_options = bundle_options(DisplayOptions, args)

    CACHE_FILE = 'cache.pkl'
    if args.load_cache:
        with open(CACHE_FILE) as fp:
            barstock, recipes = pickle.load(fp)
            print "Loaded {} recipes from cache file".format(len(recipes))

    else:
        with open(args.recipes) as fp:
            base_recipes = json.load(fp, object_pairs_hook=OrderedDict)
        barstock = Barstock.load(args.barstock, args.all)
        recipes = [drink_recipe.DrinkRecipe(name, recipe).generate_examples(barstock)
                for name, recipe in base_recipes.iteritems()]
        recipes = filter_recipes(recipes, bundle_options(FilterOptions, args))

    if args.save_cache:
        with open(CACHE_FILE, 'w') as fp:
            pickle.dump((barstock, recipes), fp)
            print "Saved {} recipes to cache file".format(len(recipes))

    if args.stats:
        report_stats(recipes)

    if args.command == 'test':
        print "This is a test"

    if args.command == 'pdf':
        pdf_options = bundle_options(PdfOptions, args)
        import formatted_menu
        ingredient_df = barstock.df if args.liquor_list or args.liquor_list_own_page else pd.DataFrame()
        formatted_menu.generate_recipes_pdf(recipes, args.pdf_filename, args.ncols, args.align,
                args.debug, args.prices, args.markup, args.examples, ingredient_df, args.liquor_list_own_page)
        return

    if args.command == 'txt':
        if args.names:
            print '\n'.join([recipe.name for recipe in recipes])
            print
            return
        #if args.write:
            #with open(args.write, 'w') as fp:
                #fp.write('\n\n'.join(menu))
        else:
            print '\n'.join([str(recipe) for recipe in recipes])
            print

if __name__ == "__main__":
    main()
