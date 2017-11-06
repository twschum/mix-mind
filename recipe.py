"""
DrinkRecipe class encapsulates how a drink recipe is calculated and formulated,
can provide itself as a dict/json, tuple of values, do conversions, etc.
Just generally make it better OOP
"""
import re
from fractions import Fraction
from recordtype import recordtype
import itertools

import util

# water volume added by preperation method for ABV estimate
WATER_BY_PREP = {'shake': 1.65, 'stir': 1.3}

class RecipeError(StandardError):
    pass

class DrinkRecipe(object):
    """ Initialize a drink with a handle to the available stock data and its recipe json
    """
    RecipeExample = recordtype('RecipeExample', [('bottles', []), ('cost', 0), ('abv', 0), ('std_drinks', 0), ('volume', 0)])
    RecipeStats = recordtype('RecipeStats', 'min_cost,max_cost,min_abv,max_abv,min_std_drinks,max_std_drinks,volume', default=RecipeExample)

    @util.default_initializer
    def __init__(self, name, recipe_dict, stock_df=None):
        # from recipe dict pull out other info and set defaults
        self.info      =  recipe_dict.get('info',      '')
        self.iba_info  =  recipe_dict.get('IBA_description', '')
        self.origin    =  recipe_dict.get('origin',    '')
        self.unit      =  recipe_dict.get('unit',      'oz') # cL, mL, tsp, dash, drop, bar spoon
        self.prep      =  recipe_dict.get('prep',      'shake') # build, stir
        self.ice       =  recipe_dict.get('origin',    'cubed') # crushed
        self.glass     =  recipe_dict.get('glass',     'cocktail') # rocks, martini, champagne flute
        self.variants  =  recipe_dict.get('variants',  [])
        self.max_cost     =  0
        self.examples     =  []
        self.ingredients  =  []
        for type_, quantity in recipe_dict.get('ingredients', {}).iteritems():
            self.ingredients.append(QuantizedIngredient(type_, quantity, self.unit))
        for type_, quantity in recipe_dict.get('optional', {}).iteritems():
            self.ingredients.append(OptionalIngredient(type_, quantity, self.unit))
        if recipe_dict.get('misc'):
            self.ingredients.append(Ingredient(recipe_dict.get('misc')))
        if recipe_dict.get('garnish'):
            self.ingredients.append(Garnish(recipe_dict.get('garnish')))

        self.show_examples = False

    def __str__(self):
        """ Drink recipe basic plain text output format
        """
        lines = []
        lines.append(self.name)
        lines.extend([i.str() for i in self.ingredients])
        if self.variants:
            lines.append("\tVariants:")
            lines.extend(['\t'+v for v in self.variants])
        if self.show_examples:
            lines.append("\tExamples:")
            lines.extend(['\t'+v for v in self.examples])
        lines.append('')
        return '\n'.join(lines)

    def __repr__(self):
        return "{}:{},[{}]".format(self.__class__.__name__, self.name, ','.join((i.__repr__() for i in self.ingredients)))

    @property
    def can_make(self):
        return bool(self.examples)

    def convert(self, to_unit, convert_nonstandard=False):
        """ Convert the main unit of this recipe
        """
        if self.unit == to_unit:
            return
        for ingredient in self.ingredients:
            ingredient.recipe_unit = to_unit
            if ingredient.unit in ['ds', 'drop'] and not convert_nonstandard:
                continue
            try:
                ingredient.convert(to_unit)
            except NotImplementedError:
                pass
        self.unit = to_unit

    def generate_examples(self, barstock):
        """ Given a Barstock, calculate examples drinks from the data
        e.g. For every dry gin and vermouth in Barstock, generate every Martini
        that can be made, along with the cost,abv,std_drinks from the ingredients
        """
        ingredients = self._get_quantized_ingredients()
        example_bottles = barstock.get_all_bottle_combinations((i.type_ for i in ingredients))
        for bottles in example_bottles:
            example = self.RecipeExample(); example.bottles = []
            for bottle, ingredient in zip(bottles, ingredients):
                if ingredient.unit == 'literal':
                    continue
                example.cost       += ingredient.get_cost(bottle, barstock)
                example.std_drinks += ingredient.get_std_drinks(bottle, barstock)
                example.volume     += ingredient.get_amount_as(self.unit, rounded=False, single_value=True)
                # remove juice and such from the bottles listed
                if barstock.get_bottle_category(bottle, ingredient.type_) in ['Vermouth', 'Liqueur', 'Bitters', 'Spirit', 'Wine']:
                    example.bottles.append(bottle)
            example.bottles = ', '.join(example.bottles);
            example.volume *= WATER_BY_PREP.get(self.prep, 1.0)
            example.abv = util.calculate_abv(example.std_drinks, example.volume, self.unit)
            self.max_cost = max(self.max_cost, example.cost)
            self.examples.append(example)
        return self # so it can be used when chained

    def calculate_stats(self):
        """ After generating examples, calculate stats for this drink
        """
        if not self.examples:
            return False
        def _find_example(examples, attr, max_=False):
            return sorted(examples, key=lambda e: getattr(e, attr), reverse=max_)[0]
        self.stats = self.RecipeStats()
        self.stats.min_cost = _find_example(self.examples, 'cost')
        self.stats.max_cost = _find_example(self.examples, 'cost', max_=True)
        self.stats.min_abv = _find_example(self.examples, 'abv')
        self.stats.max_abv = _find_example(self.examples, 'abv', max_=True)
        self.stats.min_std_drinks = _find_example(self.examples, 'std_drinks')
        self.stats.max_std_drinks = _find_example(self.examples, 'std_drinks', max_=True)
        self.stats.volume = _find_example(self.examples, 'volume', max_=True).volume
        return True

    def _get_quantized_ingredients(self):
        return [i for i in self.ingredients if isinstance(i, QuantizedIngredient)]

    def primary_spirit(self):
        max_amount = 0
        max_ingredient = None
        for i in self._get_quantized_ingredients(): # TODO enforce ingredient Category tags
            amount = i.get_amount_as(self.unit, rounded=False, single_value=True)
            if amount > max_amount and not i.top_with:
                max_amount = amount
                max_ingredient = i.type_
        return max_ingredient

    def contains_ingredient(self, ingredient):
        for i in self.ingredients:
            if ingredient in i.type_:
                return True
        return False


class Ingredient(object):
    """ An "ingredient" is every item that should be represented in standard text
    """
    def _repr_fmt(self):
        return "<{}[{{}}]>".format(self.__class__.__name__)

    @util.default_initializer
    def __init__(self, description):
        self.unit = None
        self.type_ = description

    def str(self):
        return str(self.description)

    def __repr__(self):
        return self._repr_fmt().format(self.description)

    def convert(self, new_unit):
        pass


class Garnish(Ingredient):
    """ An ingredient line that denotes it's a garnish
    """
    def str(self):
        return "{}, for garnish".format(super(Garnish, self).str())

    def __repr__(self):
        return super(Garnish, self)._repr_fmt().format(self.description)


class QuantizedIngredient(Ingredient):
    """ Has a unit based on the raw quantity, responsible for unit conversions, text output
    """
    @util.default_initializer
    def __init__(self, type_, raw_quantity, recipe_unit):

        self.top_with = False
        # interpret the raw quantity
        if isinstance(raw_quantity, basestring):
            if raw_quantity == 'Top with':
                self.amount = util.convert_units(3.0, 'oz', recipe_unit, rounded=True)
                self.unit = recipe_unit
                self.top_with = True

            elif 'dash' in raw_quantity:
                self.unit = 'ds'
                if raw_quantity == 'dash':
                    self.amount = 1
                elif re.match(r'[0-9]+ dashes', raw_quantity):
                    self.amount = int(raw_quantity.split()[0])
                elif re.match(r'[0-9]+ to [0-9]+ dashes', raw_quantity):
                    self.amount = (int(raw_quantity.split()[0]), int(raw_quantity.split()[2]))
                else:
                    raise RecipeError("Unknown format for dash amount: {} {}".format(raw_quantity, type_))

            elif 'tsp' in raw_quantity:
                try:
                    self.amount = float(raw_quantity.split()[0])
                except ValueError:
                    self.amount = float(Fraction(raw_quantity.split()[0]))
                self.unit = 'tsp'

            elif 'drop' in raw_quantity:
                self.unit = 'drop'
                if raw_quantity == 'drop':
                    self.amount = 1
                elif re.match(r'[0-9]+ drops', raw_quantity):
                    self.amount = int(raw_quantity.split()[0])
                else:
                    raise RecipeError("Unknown format for dash amount: {} {}".format(raw_quantity, type_))

            elif raw_quantity in ['one', 'two', 'three']:
                self.amount = raw_quantity
                self.unit = 'literal'
            else:
                raise RecipeError("Unknown ingredient quantity: {} {}".format(raw_quantity, type_))
        else:
            self.amount = raw_quantity
            self.unit = recipe_unit

    def __repr__(self):
        return super(QuantizedIngredient, self)._repr_fmt().format("{},{},{}".format(self.amount, self.unit, self.type_))

    def convert(self, new_unit):
        if self.unit == 'literal':
            return
        self.amount = self.get_amount_as(new_unit)
        self.unit = new_unit

    def get_amount_as(self, new_unit, rounded=True, single_value=False):
        if self.unit == 'literal':
            return
        if isinstance(self.amount, tuple):
            lower  = util.convert_units(self.amount[0], self.unit, new_unit, rounded=rounded)
            higher = util.convert_units(self.amount[1], self.unit, new_unit, rounded=rounded)
            amount = (lower+higher)/2.0 if single_value else (lower, higher)
        else:
            amount = util.convert_units(self.amount, self.unit, new_unit, rounded=rounded)
        return amount

    def str(self):
        if self.top_with:
            return "Top with {}".format(self.type_)
        if self.unit == 'literal':
            return "{} {}".format(self.amount, self.type_)

        if self.unit == 'ds':
            if isinstance(self.amount, tuple):
                amount = "{:.0f} to {:.0f}".format(self.amount[0], self.amount[1])
                unit = 'dashes'
            elif self.amount == 1:
                amount = 'dash'
                unit = 'of'
            else:
                amount = "{:.0f}".format(self.amount)
                unit = 'dashes'
        elif self.unit == 'drop':
            if isinstance(self.amount, tuple):
                amount = "{:.0f} to {:.0f}".format(self.amount[0], self.amount[1])
                unit = 'drops'
            elif self.amount == 1:
                amount = 'drop'
                unit = 'of'
            else:
                amount = "{:.0f}".format(self.amount)
                unit = 'drops'
        elif self.unit in ['oz', 'tsp']:
            amount = util.to_fraction(self.amount)
            unit = self.unit
        else:
            amount = self.amount
            unit = self.unit

        formats = {
                'mL': u"{:.0f} {} {}",
                'cL': u"{:.1f} {} {}",
                }
        return formats.get(self.unit, u"{} {} {}").format(amount, unit, self.type_)

    def get_cost(self, bottle, barstock):
        if self.unit == 'literal':
            return 0
        amount = self.get_amount_as(self.recipe_unit, rounded=False, single_value=True)
        return barstock.cost_by_bottle_and_volume(bottle, self.type_, amount, self.recipe_unit)

    def get_std_drinks(self, bottle, barstock):
        if self.unit == 'literal':
            return 0
        amount = self.get_amount_as(self.recipe_unit, rounded=False, single_value=True)
        proof = barstock.get_bottle_proof(bottle, self.type_)
        return util.calculate_std_drinks(proof, amount, self.recipe_unit)


class OptionalIngredient(QuantizedIngredient):
    """ A quantized ingredient that just gets an extra output tag
    """
    def str(self):
        return "{}, (optional)".format(super(OptionalIngredient, self).str())

