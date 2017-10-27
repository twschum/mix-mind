"""
Recipe class encapsulates how a drink recipe is calculated and formulated,
can provide itself as a dict/json, tuple of values, do conversions, etc.
Just generally make it better OOP
"""
import re
from fractions import Fraction
from collections import namedtuple
import itertools

import util

class RecipeError(StandardError):
    pass

class DrinkRecipe(object):
    """ Initialize a drink with a handle to the available stock data and its recipe json
    """
    RecipeExample = namedtuple('RecipeExample', 'bottles,cost,abv,drinks')


    @util.default_initializer
    def __init__(self, name, recipe_dict, stock_df=None):
        # from recipe dict pull out other info and set defaults
        self.info      =  recipe_dict.get('info',      '')
        self.origin    =  recipe_dict.get('origin',    '')
        self.unit      =  recipe_dict.get('unit',      'oz')
        self.prep      =  recipe_dict.get('prep',      'shake')
        self.ice       =  recipe_dict.get('origin',    'cubed')
        self.glass     =  recipe_dict.get('glass',     'up')
        self.variants  =  recipe_dict.get('variants',  [])
        self.examples  =  []
        self.ingredients = []
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
            lines.append("Variants:")
            lines.extend(['\t'+v for v in self.variants])
        if self.show_examples:
            lines.append("Examples:")
            lines.extend(['\t'+v for v in self.examples])
        lines.append('')
        return '\n'.join(lines)

    def convert(self, to_unit, convert_nonstandard=False):
        if self.unit == to_unit:
            return
        for ingredient in self.ingredients:
            if ingredient.unit in ['ds', 'drop'] and not convert_nonstandard:
                continue
            try:
                ingredient.convert(to_unit)
            except NotImplementedError:
                pass
        self.unit = to_unit


    def generate_examples(self, barstock):
        ingredient_types = [i.type_ for i in self.ingredients if isinstance(i, QuantizedIngredient)]




class Ingredient(object):
    """ An "ingredient" is every item that should be represented in standard text
    """
    @util.default_initializer
    def __init__(self, description):
        self.unit = None

    def str(self):
        return str(self.description)

    def cost(self):
        return 0

    def convert(self, new_unit):
        pass


class Garnish(Ingredient):
    """ An ingredient line that denotes it's a garnish
    """
    def str(self):
        return "{}, for garnish".format(super(Garnish, self).str())


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

    def convert(self, new_unit):
        if self.unit == 'literal':
            return
        if isinstance(self.amount, tuple):
            lower  = util.convert_units(self.amount[0], self.unit, new_unit, rounded=True)
            higher = util.convert_units(self.amount[1], self.unit, new_unit, rounded=True)
            self.amount = (lower, higher)
        else:
            self.amount = util.convert_units(self.amount, self.unit, new_unit, rounded=True)
        self.unit = new_unit

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
                'mL': "{:.0f} {} {}",
                'cL': "{:.1f} {} {}",
                }
        return formats.get(self.unit, "{} {} {}").format(amount, unit, self.type_)


class OptionalIngredient(QuantizedIngredient):
    """ A quantized ingredient that just gets an extra output tag
    """
    def str(self):
        return "{}, (optional)".format(super(OptionalIngredient, self).str())

