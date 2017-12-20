""" Miscallanious util funcitons for the mix-mind project
"""

from functools import wraps
from fractions import Fraction
from collections import OrderedDict, namedtuple
import json
import inspect

# make passing a bunch of options around a bit cleaner
DisplayOptions = namedtuple('DisplayOptions', 'prices,stats,examples,all_ingredients,markup,prep_line,origin,info,variants')
FilterOptions = namedtuple('FilterOptions', 'all,include,exclude,use_or,style,glass,prep,ice')
PdfOptions = namedtuple('PdfOptions', 'pdf_filename,ncols,liquor_list,liquor_list_own_page,debug,align,title,tagline')

def filter_recipes(all_recipes, filter_options):
    reduce_fn = any if filter_options.use_or else all
    recipes = [recipe for recipe in all_recipes if recipe.can_make or filter_options.all]
    if filter_options.include:
        recipes = [recipe for recipe in recipes if
                reduce_fn((recipe.contains_ingredient(ingredient, include_optional=True)
                for ingredient in filter_options.include))]
    if filter_options.exclude:
        recipes = [recipe for recipe in recipes if
                reduce_fn((not recipe.contains_ingredient(ingredient, include_optional=False)
                for ingredient in filter_options.exclude))]
    for attr in 'style glass prep ice'.split():
        recipes = filter_on_attribute(recipes, filter_options, attr)

    def get_names(items):
        return set(map(lambda i: i.name, items))
    excluded = sorted(list(get_names(all_recipes) - get_names(recipes)))
    print "    Can't make: {}\n".format(', '.join(excluded))
    return recipes, excluded

def filter_on_attribute(recipes, filter_options, attribute):
    if getattr(filter_options, attribute):
        attr_value = getattr(filter_options, attribute).lower()
        recipes = [recipe for recipe in recipes if attr_value in getattr(recipe, attribute).lower()]
    return recipes

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
    return [most_expensive, most_booze, most_abv, least_expensive, least_booze, least_abv]

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


def default_initializer(func):
    names, varargs, keywords, defaults = inspect.getargspec(func)
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        for name, arg in list(zip(names[1:], args)) + list(kwargs.items()):
            setattr(self, name, arg)
        func(self, *args, **kwargs)
    return wrapper

def to_fraction(amount):
    fraction = Fraction.from_float(float(amount)).limit_denominator(99)
    if fraction.denominator == 1:
        return fraction.numerator
    whole = fraction.numerator / fraction.denominator
    numer = fraction.numerator % fraction.denominator
    return "{}{}/{}".format(str(whole)+' ' if whole > 0 else '', numer, fraction.denominator)

def calculate_price(cost, markup, rounded=True):
    price = (cost+1) * markup
    if rounded:
        price = int(price+1)
    return price

def calculate_std_drinks(proof, amount, unit):
    """ Standard drink is 1.5 oz or 45 ml at 80 proof
    """
    adjusted_proof = proof / 80.0
    adjusted_amount = convert_units(amount, unit, 'oz') / 1.5
    return adjusted_proof * adjusted_amount

def calculate_abv(std_drinks, volume, unit):
    if unit == 'oz':
        units_per_std_drink = 1.5
    elif unit == 'mL':
        units_per_std_drink = 45.0
    elif unit == 'cL':
        units_per_std_drink = 4.5
    else:
        raise NotImplementedError("number of standard drinks for unit '{}' is unknown".format(unit))
    abv = 40.0 * (std_drinks*units_per_std_drink / volume)
    return abv


# units, yo
ML_PER_OZ           =  29.5735
ML_PER_OZ_ROUNDED   =  30.0
ML_PER_TSP          =  4.92892
ML_PER_TSP_ROUNDED  =  5.0
ML_PER_DS           =  0.92
ML_PER_CL           =  10.0
ML_PER_DROP         =  0.12
OZ_PER_TSP          =  1.0/8.0
OZ_PER_DS           =  1.0/32.0
OZ_PER_DROP         =  1.0/240.0

def convert_units(amount, from_unit, to_unit, rounded=False):
    if from_unit == 'literal':
        return amount
    amount = float(amount)
    if from_unit == to_unit:
        return amount
    unit_conversions = {
            'ds': dash_to_volume,
            'tsp': tsp_to_volume,
            'mL': mL_to_volume,
            'cL': cL_to_volume,
            'oz': oz_to_volume,
            'drop': drop_to_volume,
            }
    convert = unit_conversions.get(from_unit, lambda x,y,z: no_conversion(from_unit, to_unit))
    return convert(amount, to_unit, rounded)

def no_conversion(from_unit, to_unit):
    raise NotImplementedError("conversion from {} to {}".format(from_unit, to_unit))

def dash_to_volume(amount, unit, rounded=False):
    mL_per_oz = ML_PER_OZ if not rounded else ML_PER_OZ_ROUNDED
    if unit == 'mL':
        return amount * ML_PER_DS
    elif unit == 'cL':
        return amount * ML_PER_DS / ML_PER_CL
    elif unit == 'oz':
        return amount / mL_per_oz
    else:
        no_conversion('dash', unit)

def tsp_to_volume(amount, unit, rounded=False):
    mL_per_tsp = ML_PER_TSP if not rounded else ML_PER_TSP_ROUNDED
    if unit == 'oz':
        return amount * OZ_PER_TSP
    elif unit == 'mL':
        return amount * mL_per_tsp
    elif unit == 'cL':
        return amount * mL_per_tsp / ML_PER_CL
    else:
        no_conversion('tsp', unit)

def oz_to_volume(amount, unit, rounded=False):
    mL_per_oz = ML_PER_OZ if not rounded else ML_PER_OZ_ROUNDED
    if unit == 'mL':
        return amount * mL_per_oz
    elif unit == 'cL':
        return amount * mL_per_oz / ML_PER_CL
    elif unit == 'tsp':
        return amount / OZ_PER_TSP
    elif unit == 'ds':
        return amount / OZ_PER_DS
    elif unit == 'drop':
        return amount / OZ_PER_DROP
    else:
        no_conversion('oz', unit)

def mL_to_volume(amount, unit, rounded=False):
    mL_per_oz = ML_PER_OZ if not rounded else ML_PER_OZ_ROUNDED
    mL_per_tsp = ML_PER_TSP if not rounded else ML_PER_TSP_ROUNDED
    if unit == 'oz':
        return amount / mL_per_oz
    elif unit == 'cL':
        return amount / ML_PER_CL
    elif unit == 'ds':
        return amount / ML_PER_DS
    elif unit == 'tsp':
        return amount / mL_per_tsp
    elif unit == 'drop':
        return amount / ML_PER_DROP
    elif unit == 'mL':
        return amount
    else:
        no_conversion('mL', unit)

def drop_to_volume(amount, unit, rounded=False):
    if unit == 'oz':
        return amount * OZ_PER_DROP
    elif unit == 'mL':
        return amount * ML_PER_DROP
    elif unit == 'cL':
        return amount * ML_PER_DROP / ML_PER_CL
    else:
        no_conversion('drop', unit)

def cL_to_volume(amount, unit, rounded=False):
    try:
        return mL_to_volume(amount, unit, rounded) * ML_PER_CL
    except NotImplementedError:
        no_conversion('cL', unit)

class IngredientSpecifier(object):
    """ Allow type:bottle in recipes,
    e.g. "white rum:Barcadi Catra Blanca" or "aromatic bitters:Angostura"
    """
    @default_initializer
    def __init__(self, what, bottle=None):
        if what is None:
            raise ValueError("IngredientSpecifier what (type) cannot be None")
        if '(' in what and ')' in what:
            self.extra = what.strip()[what.find('('):]
            self.what = what.strip()[:what.find('(')].strip()
        else:
            self.extra = None

    @classmethod
    def from_string(cls, type_str):
        if ':' in type_str:
            t = type_str.split(':')
            if len(t) == 2:
                what = t[0]
                bottle = t[1]
            else:
                raise ValueError("Unknown ingredient specifier: {}".format(type_str))
        else:
            what = type_str
            bottle = None
        return cls(what, bottle)

    def __str__(self):
        return self.bottle if self.bottle else "{}{}".format(self.what, ' '+self.extra if self.extra else '')

    def __repr__(self):
        return "{}:{}".format(self.what, self.bottle if self.bottle else '')

