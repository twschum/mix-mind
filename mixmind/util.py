""" Miscallanious util funcitons for the mix-mind project
"""
from functools import wraps
from fractions import Fraction
from collections import OrderedDict, namedtuple
import operator
import json
import inspect
import uuid
import pendulum
from . import log

# make passing a bunch of options around a bit cleaner
DisplayOptions = namedtuple('DisplayOptions', 'prices,stats,examples,all_ingredients,markup,prep_line,origin,info,variants')
FilterOptions = namedtuple('FilterOptions', 'search,all_,include,exclude,include_use_or,exclude_use_or,style,glass,prep,ice,name,tag')
PdfOptions = namedtuple('PdfOptions', 'pdf_filename,ncols,liquor_list,liquor_list_own_page,debug,align,title,tagline')

VALID_UNITS = ['oz', 'mL', 'cL']

class ResultRecipes(object):
    def add_items(self, recipes):
        pass
    def get_items(self):
        pass

class UnionResultRecipes(ResultRecipes):
    def __init__(self):
        self.container = OrderedDict()
    def add_items(self, recipes):
        for recipe in recipes:
            self.container[recipe.name] = recipe
    def get_items(self):
        return self.container.values()

class IntersectionResultRecipes(ResultRecipes):
    def __init__(self):
        self.container = None
    def add_items(self, recipes):
        if self.container is None:
            self.container = recipes
        else:
            self.container = [x for x in self.container if x in recipes]
    def get_items(self):
        return self.container

def filter_recipes(all_recipes, filter_options, union_results=False):
    """Filters the recipe list based on a FilterOptions bundle of parameters
    :param list[Recipe] all_recipes: list of recipe object to filter
    :param FilterOptions filter_options: bundle of filtering parameters
        search str: search an arbitrary string against the ingredients and attributes
    :param bool union_results: for each attributes searched against, combine results
        with set intersection by default, or union if True
    """
    result_recipes = UnionResultRecipes() if union_results else IntersectionResultRecipes()
    recipes = [recipe for recipe in all_recipes if filter_options.all_ or recipe.can_make]
    if filter_options.search:
        include_list = [filter_options.search.lower()]
    else:
        include_list = filter_options.include
    if include_list:
        reduce_fn = any if filter_options.include_use_or else all
        result_recipes.add_items([recipe for recipe in recipes if
                reduce_fn((recipe.contains_ingredient(ingredient, include_optional=True)
                for ingredient in include_list))])
    if filter_options.exclude:
        reduce_fn = any if filter_options.exclude_use_or else all
        result_recipes.add_items([recipe for recipe in recipes if
                reduce_fn((not recipe.contains_ingredient(ingredient, include_optional=False)
                for ingredient in filter_options.exclude))])
    for attr in 'style glass prep ice name tag'.split():
        result_recipes.add_items(filter_on_attribute(recipes, filter_options, attr))

    result_recipes = result_recipes.get_items()

    def get_names(items):
        return set(map(lambda i: i.name, items))
    excluded = sorted(list(get_names(all_recipes) - get_names(result_recipes)))
    log.debug("Excluded: {}\n".format(', '.join(excluded)))
    return result_recipes, excluded

def find_recipe(recipes, name):
    for recipe in recipes:
        if recipe.name == name:
            return recipe
    return None

def filter_on_attribute(recipes, filter_options, attribute):
    attr_value = getattr(filter_options, attribute).lower()
    if filter_options.search and not attr_value:
        attr_value = filter_options.search.lower()
    if attr_value:
        recipes = [recipe for recipe in recipes if attr_value in getattr(recipe, attribute).lower()]
    return recipes

def get_uuid():
    return unicode(uuid.uuid4())

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

    def as_html(self):
        return u"<tr><td> {{title:{}}} </td><td> {{drink_name:{}}} </td><td> ${{cost:.2f}} </td><td> {{abv:>5.2f}}% ABV </td><td> {{std_drinks:.2f}} </td><td style:text-align=left> {{bottles}} </td></tr>"\
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

def report_stats(recipes, as_html=False):
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
    if as_html:
        return u"<table class=statsbloc><thead><th></th><th>Drink</th><th style='text-align: right;'>Cost</th><th style='text-align: right;'>Est ABV</th><th style='text-align: right;'>Std Drinks</th><th>Ingredients</th></thead><tbody>{}</tbody></table>".format(u''.join([s.as_html()
            for s in [most_expensive, most_booze, most_abv, least_expensive, least_booze, least_abv]]))
    else:
        return [most_expensive, most_booze, most_abv, least_expensive, least_booze, least_abv]

def load_recipe_json(recipe_files):
    base_recipes = OrderedDict()
    for recipe_json in recipe_files:
        with open(recipe_json) as fp:
            other_recipes = json.load(fp, object_pairs_hook=OrderedDict)
            log.info("Recipes loaded from {}".format(recipe_json))
            for item in other_recipes.itervalues():
                item.update({'source_file': recipe_json})
            for name in [name for name in other_recipes.keys() if name in base_recipes.keys()]:
                log.debug("Keeping {} from {} over {}".format(name, base_recipes[name]['source_file'], other_recipes[name]['source_file']))
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

# utils to convert string values
def from_float(s):
    if not s:
        return 0.0
    return float(s)
def from_price_float(s):
    if isinstance(s, basestring):
        return from_float(s.replace('$', ''))
    return from_float(s)
def from_bool_from_num(s):
    if not s:
        return False
    return bool(float(s))
def as_utf8(s):
    return unicode(s, 'utf-8')

def to_fraction(amount):
    fraction = Fraction.from_float(float(amount)).limit_denominator(99)
    if fraction.denominator == 1:
        return fraction.numerator
    whole = fraction.numerator / fraction.denominator
    numer = fraction.numerator % fraction.denominator
    return "{}{}/{}".format(str(whole)+' ' if whole > 0 else '', numer, fraction.denominator)

def calculate_price(cost, markup):
    return int(((cost + 1) * float(markup)) +1)

def calculate_std_drinks(abv, amount, unit):
    """ Standard drink is 1.5 oz or 45 ml at 40% abv
    """
    adjusted_abv = abv / 40.0
    adjusted_amount = convert_units(amount, unit, 'oz') / 1.5
    return adjusted_abv * adjusted_amount

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
    try:
        amount = float(amount)
    except TypeError: # pd series breaks this
        amount = amount
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
        return self.bottle if self.bottle else u"{}{}".format(self.what, u' '+self.extra if self.extra else u'')

    def __repr__(self):
        return u"{}:{}".format(self.what, self.bottle if self.bottle else '')

def to_human_diff(dt):
    """Return datetime as humanized diff from now"""
    return pendulum.instance(dt).diff_for_humans() if dt else '-'

def get_ts_formatter(fmt, tz):
    """Returns callable that will format a datetime"""
    return lambda dt: pendulum.instance(dt).in_timezone(tz).format(fmt) if dt else '-'

