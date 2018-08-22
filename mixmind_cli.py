#!/usr/bin/env python
"""
Turn recipes json into a readable menu
"""

import argparse
import cPickle as pickle
from collections import Counter, defaultdict
import json
import jsonschema

import pandas as pd

import mixmind.recipe as drink_recipe
from mixmind.barstock import Barstock
import mixmind.formatted_menu as formatted_menu
import mixmind.util as util


def get_parser():
    p = argparse.ArgumentParser(description="""
MixMind Drink Menu Generator by twschum
You'll need:
A json file of recipes conforming to the schema
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
        "misc": "This line shows up below the ingredients",
        "unit": "oz", # or mL, whatever the primary unit is for ingredients
        "prep": "stir", # shake, build, throw
        "ice": "none", # cubed, crushed
        "glass": "martini", # rocks, collins, flute, cocktail
        "garnish": "Lemon twist or olives"
    }}
}}
A csv of ingredients based on the following format:
Category  Type              Bottle           In Stock  Proof  Size (mL)  Price Paid
Spirit    Rye Whiskey       Bulleit Rye      1         90     750        $28.96
Spirit    Dry Gin           New Amsterdam    0         88     1750       $25.49
Liqueur   Orange Liqueur    Triple Sec       1         30     750        $5.99
Vermouth  Dry Vermouth      Noilly Prat Dry  1         32     375        $6.99
Bitters   Aromatic Bitters  Angostura        1         89.4   118        $7.95
Syrup     Simple Syrup      Homemade         1         0      4000       $2.79
Juice     Lemon Juice       Fresh            1         0      45         $0.80
Mixer     Club Soda         Club Soda        0         0      178        $1.00

Example usage:
    {} -b 'Barstock.csv' -r 'my_recipes.json' -p -e -i lime rum -x 'lemon juice'  pdf my_menu -n 2 -l
""".format(__file__), formatter_class=argparse.RawTextHelpFormatter)
    subparsers = p.add_subparsers(help='commands', dest='command')

    # core parameters
    p.add_argument('-v', '--verbose', action='store_true')
    p.add_argument('-b', '--barstock', help="Barstock csv filename")
    p.add_argument('-r', '--recipes', nargs='+', default=['recipes_schubar.json'], help="Recipes json filename(s)")
    p.add_argument('--save_cache', action='store_true', help="Pickle the generated recipes to cache them for later use (e.g. a quicker build of the pdf)")
    p.add_argument('--load_cache', action='store_true', help="Load the generated recipes from cache for use")

    # display options
    p.add_argument('-$', '--prices', action='store_true', help="Display prices for drinks based on stock")
    p.add_argument('-p', '--prep-line', action='store_true', help="Display a line showing glass, ice, and prep")
    p.add_argument('-s', '--stats', action='store_true', help="Print out a detailed statistics block for the selected recipes")
    p.add_argument('-e', '--examples', action='store_true', help="Show specific examples of a recipe based on the ingredient stock")
    p.add_argument('-c', '--convert', default='oz', choices=['oz','mL','cL'], help="Convert recipes to a different primary unit")
    p.add_argument('-g', '--all-ingredients', action='store_true', help="Show every ingredient instead of just the main liquors with each example")
    p.add_argument('-m', '--markup', default=1.2, type=float, help="Drink markup: price = ceil((base_cost+1)*markup)")
    p.add_argument('--info', action='store_true', help="Show the info line for recipes")
    p.add_argument('--origin', action='store_true', help="Check origin and mark drinks as Schubar originals")
    p.add_argument('--variants', action='store_true', help="Show variants for drinks")

    # filtering options
    p.add_argument('-a', dest='all_', action='store_true', help="Include all ingredients from barstock whether or not that are marked in stock")
    p.add_argument('-i', '--include', nargs='+', help="Filter by ingredient(s) that must be contained in the recipe")
    p.add_argument('-x', '--exclude', nargs='+', help="Filter by ingredient(s) that must NOT be contained in the recipe")
    p.add_argument('--or', dest='use_or', action='store_true', help="use logical OR for included and excluded ingredient lists instead of default AND")
    p.add_argument('--name', help="Include drinks matching on name")
    p.add_argument('--tag', help="Include drinks matching a tag")
    p.add_argument('--style', help="Include drinks matching the style such as After Dinner or Longdrink")
    p.add_argument('--list', help="Include drinks matching the specified list")
    p.add_argument('--glass', help="Include drinks matching the glassware")
    p.add_argument('--prep', help="Include drinks matching the prep (shake, stir, build)")
    p.add_argument('--ice', help="Include drinks matching the type of ice (crushed, cubed, neat)")

    # txt output
    txt_parser = subparsers.add_parser('txt', help='Simple plain text output')
    txt_parser.add_argument('--names', action='store_true', help="Show the names of drinks only")
    txt_parser.add_argument('--ingredients', action='store_true', help="Show name and ingredients but not full recipe")
    txt_parser.add_argument('-w', '--write', default=None, help="Save text menu out to a file")

    # pdf (latex) output and options
    pdf_parser = subparsers.add_parser('pdf', help='Options for generating a pdf via LaTeX integration')
    pdf_parser.add_argument('pdf_filename', help="Basename of the pdf and tex files generated")
    pdf_parser.add_argument('-n', '--ncols', default=2, type=int, help="Number of columns to use for the menu")
    pdf_parser.add_argument('-l', '--liquor_list', action='store_true', help="Show list of the available ingredients")
    pdf_parser.add_argument('-L', '--liquor_list_own_page', action='store_true', help="Show list of the available ingredients on a separate page")
    pdf_parser.add_argument('-D', '--debug', action='store_true', help="Add debugging output to the pdf")
    pdf_parser.add_argument('--align', action='store_true', help="Align drink names across columns")
    pdf_parser.add_argument('--title', default=None, help="Title to use")
    pdf_parser.add_argument('--tagline', default=None, help="Tagline to use below the title")

    # Do alternate things
    test_parser = subparsers.add_parser('test', help='whatever I need it to be')

    # Do some validation
    test_parser = subparsers.add_parser('validate', help='Run schema validation against recipe files')

    return p

def bundle_options(tuple_class, args):
    return tuple_class(*(getattr(args, field) for field in tuple_class._fields))

def main():
    args = get_parser().parse_args()
    display_options = bundle_options(util.DisplayOptions, args)
    filter_options = bundle_options(util.FilterOptions, args)
    pd.set_option('display.expand_frame_repr', False)

    if args.command == 'test':
        print "This is a test"
        recipes = util.load_recipe_json(args.recipes)
        # get all the properties
        fields = {}
        for recipe in recipes.itervalues():
            for label, value in recipe.iteritems():
                if label not in ['info', 'variants', 'garnish', 'IBA_description', 'optional', 'ingredients', 'misc']:
                    if not isinstance(value, list):
                        value = [value]
                    try:
                        fields.setdefault(label, Counter()).update(value)
                    except Exception as e:
                        import ipdb; ipdb.set_trace();
                        print e
        for field, values in fields.iteritems():
            print "{}: {}".format(field, values.most_common())
        return

        recipes = [drink_recipe.DrinkRecipe(name, recipe) for name, recipe in recipes.iteritems()]

        # output all the ingredients
        ingredients = Counter()
        for info in recipes.itervalues():
            ingredients.update(info.get('ingredients', {}).iterkeys())
        for i, n in ingredients.most_common():
            print '{:2d} {}'.format(n, unicode(i).encode('ascii', errors='replace'))
        return

    if args.command == 'validate':
        with open('recipe_schema.json') as fp:
            schema = json.load(fp)
        for recipe_file in args.recipes:
            with open(recipe_file) as fp:
                recipes = json.load(fp)
            jsonschema.validate(recipes, schema)
            print "{} passes schema"
        return

    RECIPES_CACHE_FILE = 'cache_recipes.pkl'
    BARSTOCK_CACHE_FILE = 'cache_barstock.pkl'
    if args.load_cache:
        barstock = Barstock(pd.read_pickle(BARSTOCK_CACHE_FILE))
        with open(CACHE_FILE) as fp:
            recipes, filter_options = pickle.load(fp)
            print "Loaded {} recipes from cache file with options:\n{}\n{}".format(len(recipes), filter_options)

    else:
        base_recipes = util.load_recipe_json(args.recipes)
        if args.barstock:
            barstock = Barstock.load(args.barstock, args.all_)
            recipes = [drink_recipe.DrinkRecipe(name, recipe).generate_examples(barstock)
                for name, recipe in base_recipes.iteritems()]
        else:
            recipes = [drink_recipe.DrinkRecipe(name, recipe) for name, recipe in base_recipes.iteritems()]
        if args.convert:
            print "Converting recipes to unit: {}".format(args.convert)
            map(lambda r: r.convert(args.convert), recipes)
        recipes, excluded = util.filter_recipes(recipes, filter_options)

    if args.save_cache:
        barstock.df.to_pickle(BARSTOCK_CACHE_FILE)
        with open(RECIPE_CACHE_FILE, 'w') as fp:
            pickle.dump((recipes, filter_options), fp)
            print "Saved recipes and barstock to cache file".format(len(recipes))

    if args.stats and recipes:
        stats = util.report_stats(recipes)
        for stat in stats:
            print stat

    if args.command == 'pdf':
        #recipes.sort(key=lambda x: x.name)
        if not args.barstock:
            if args.liquor_list or args.liquor_list_own_page or args.examples or args.prices:
                print "Must have a barstock file for these options"
                return
            barstock_df = None
        else:
            barstock_df = barstock.df
        pdf_options = bundle_options(util.PdfOptions, args)
        formatted_menu.generate_recipes_pdf(recipes, pdf_options, display_options, barstock_df)
        return

    if args.command == 'txt':
        groups = defaultdict(list)
        #for recipe in recipes:
            #groups[str(recipe.first_ingredient())].append(recipe)
        #print groups.keys()

        if args.names or args.ingredients:
            if args.ingredients and len(recipes):
                name_w = max((len(recipe.name) for recipe in recipes))
            for recipe in recipes:
                try:
                    if args.ingredients:
                        print "{{:<{}}} - {{}}".format(name_w).format(recipe.name, ', '.join(recipe.get_ingredient_list()))
                    else:
                        print recipe.name
                except UnicodeEncodeError:
                    from pprint import pprint; import ipdb; ipdb.set_trace()
                    print recipe
            #print '\n'.join([str(len(str(recipe).split('\n')))+' '+recipe.name for recipe in recipes])
            print '------------\n{} recipes\n'.format(len(recipes))
            return

        #if args.write:
            #with open(args.write, 'w') as fp:
                #fp.write('\n\n'.join(menu))
        else:
            print '\n'.join([str(recipe) for recipe in recipes])
            print

if __name__ == "__main__":
    main()
