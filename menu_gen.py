#!/usr/bin/env python
"""
Turn recipes json into a readable menu
TODO figure out how to handle recipes calling for an ingredient by name instead of type
TODO jsonschema for recipes
"""

import argparse
import json
import cPickle as pickle
from collections import OrderedDict, namedtuple, Counter
import operator

import pandas as pd

import recipe as drink_recipe
from barstock import Barstock
import formatted_menu


def filter_recipes(all_recipes, filter_options):
    reduce_fn = any if filter_options.use_or else all
    recipes = [recipe for recipe in all_recipes if recipe.can_make or filter_options.all]
    if filter_options.include:
        recipes = [recipe for recipe in recipes if
                reduce_fn((recipe.contains_ingredient(ingredient) for ingredient in filter_options.include))]
    if filter_options.exclude:
        recipes = [recipe for recipe in recipes if
                reduce_fn((not recipe.contains_ingredient(ingredient) for ingredient in filter_options.exclude))]
    def get_names(items):
        return set(map(lambda i: i.name, items))
    excluded = ', '.join(sorted(list(get_names(all_recipes) - get_names(recipes))))
    print "    Can't make: {}\n".format(excluded)
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

def load_recipe_json(recipe_files):
    base_recipes = OrderedDict()
    for recipe_json in recipe_files:
        with open(recipe_json) as fp:
            other_recipes = json.load(fp, object_pairs_hook=OrderedDict)
            print "Recipes loaded from {}".format(recipe_json)
            for item in other_recipes.itervalues():
                item.update({'source_file': recipe_json})
            for name in [name for name in other_recipes.keys() if name in base_recipes.keys()]:
                print "Keeping {} from {} over {}".format(name, base_recipes[name]['source_file'], other_recipes[name]['source_file'])
                del other_recipes[name]
            base_recipes.update(other_recipes)
    return base_recipes

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
    p.add_argument('-r', dest='recipes', default='recipes.json', help="Recipes json filename(s). Separate multiple with commas")
    p.add_argument('--save_cache', action='store_true', help="Pickle the generated recipes to cache them for later use (e.g. a quicker build of the pdf)")
    p.add_argument('--load_cache', action='store_true', help="Load the generated recipes from cache for use")

    # display options
    p.add_argument('-p', '--prices', action='store_true', help="Display prices for drinks based on stock")
    p.add_argument('--prep', action='store_true', help="Display a line showing glass, ice, and prep")
    p.add_argument('-s', '--stats', action='store_true', help="Print out a detailed statistics block for the selected recipes")
    p.add_argument('-e', '--examples', action='store_true', help="Show specific examples of a recipe based on the ingredient stock")
    p.add_argument('-c', '--convert', default='oz', choices=['oz','mL','cL'], help="Convert recipes to a different primary unit")
    p.add_argument('-g', '--all-ingredients', action='store_true', help="Show every ingredient instead of just the main liquors with each example")
    p.add_argument('-m', dest='markup', default=1.2, type=float, help="Drink markup: price = ceil((base_cost+1)*markup)")
    p.add_argument('--ignore-info', action='store_true', help="Don't show the info line for recipes")
    p.add_argument('--ignore-origin', action='store_true', help="Don't check origin and mark drinks as Schubar originals")
    p.add_argument('--ignore-variants', action='store_true', help="Don't show variants for drinks")

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
    pdf_parser.add_argument('--title', default=None, help="Title to use")
    pdf_parser.add_argument('--tagline', default=None, help="Tagline to use below the title")

    # Do alternate things
    test_parser = subparsers.add_parser('test', help='whatever I need it to be')

    return p

# make passing a bunch of options around a bit cleaner
DisplayOptions = namedtuple('DisplayOptions', 'prices,stats,examples,all_ingredients,markup,prep,ignore_origin,ignore_info,ignore_variants')
FilterOptions = namedtuple('FilterOptions', 'all,include,exclude,use_or')
PdfOptions = namedtuple('PdfOptions', 'pdf_filename,ncols,liquor_list,liquor_list_own_page,debug,align,title,tagline')
def bundle_options(tuple_class, args):
    return tuple_class(*(getattr(args, field) for field in tuple_class._fields))

def main():
    # TODO refactor the passing of options into the pdf generator
    # TODO category sorting of recipes i.e. After Dinner/Longdrink/Before Dinner ...
    # pass display options to Recipes when generating

    args = get_parser().parse_args()
    display_options = bundle_options(DisplayOptions, args)
    filter_options = bundle_options(FilterOptions, args)

    if args.command == 'test':
        print "This is a test"
        recipes = load_recipe_json(args.recipes.split(','))
        for recipe in (drink_recipe.DrinkRecipe(name, r) for name, r in recipes.iteritems()):
            print recipe.prep_line(caps=False)
        return
        ingredients = Counter()
        for info in recipes.itervalues():
            ingredients.update(info.get('ingredients', {}).iterkeys())
        for i, n in ingredients.most_common():
            print '{:2d} {}'.format(n, unicode(i).encode('ascii', errors='replace'))
        return

    RECIPES_CACHE_FILE = 'cache_recipes.pkl'
    BARSTOCK_CACHE_FILE = 'cache_barstock.pkl'
    if args.load_cache:
        barstock = Barstock(pd.read_pickle(BARSTOCK_CACHE_FILE))
        with open(CACHE_FILE) as fp:
            recipes, filter_options = pickle.load(fp)
            print "Loaded {} recipes from cache file with options:\n{}\n{}".format(len(recipes), filter_options)

    else:
        base_recipes = load_recipe_json(args.recipes.split(','))
        barstock = Barstock.load(args.barstock, args.all)
        recipes = [drink_recipe.DrinkRecipe(name, recipe).generate_examples(barstock)
                for name, recipe in base_recipes.iteritems()]
        if args.convert:
            print "Converting recipes to unit: {}".format(args.convert)
            map(lambda r: r.convert(args.convert), recipes)
        recipes = filter_recipes(recipes, filter_options)

    if args.save_cache:
        barstock.df.to_pickle(BARSTOCK_CACHE_FILE)
        with open(RECIPE_CACHE_FILE, 'w') as fp:
            pickle.dump((recipes, filter_options), fp)
            print "Saved recipes and barstock to cache file".format(len(recipes))

    if args.stats:
        report_stats(recipes)

    if args.command == 'pdf':
        # sort recipes loosely by approximate display length
        #recipes.sort(key=lambda r: len(str(r).split('\n'))/3, reverse=True)
        pdf_options = bundle_options(PdfOptions, args)
        formatted_menu.generate_recipes_pdf(recipes, pdf_options, display_options, barstock.df)
        return

    if args.command == 'txt':
        if args.names:
            print '\n'.join([str(len(str(recipe).split('\n')))+' '+recipe.name for recipe in recipes])
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
