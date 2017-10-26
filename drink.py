"""
Drink class encapsulates how a drink recipe is calculated and formulated,
can provide itself as a dict/json, tuple of values, do conversions, etc.
Just generally make it better OOP
"""

import util

class RecipeError(StandardError):
    pass

class Drink(object):
    """ Initialize a drink with a handle to the available stock data and its recipe json
    """

    @util.default_initializer
    def __init__(self, stock_df, name, recipe_dict):
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
        for type_, quantity in recipe.get('ingredients', {}).iteritems():
            self.ingredients.append(Ingredient(type_, quantity, self.unit))
        for type_, quantity in recipe.get('optional', {}).iteritems():
            self.ingredients.append(OptionalIngredient(type_, quantity, self.unit))
        ingredients.append(Ingredient(recipe.get('misc', '')))
        ingredients.append(Garnish(recipe.get('misc', '')))

        self.show_examples = False

    def __str__(self):
        """ Drink recipe basic output format
        """
        lines = []
        lines.append(self.name)
        lines.extend([i.str() for i in self.ingredients])
        lines.append("Variants")
        lines.extend(self.variants)
        if self.show_examples:
            lines.append("Examples:")
            lines.extend(self.examples)
        lines.append('\n')
        return '\n'.join(lines)


class Ingredient(object):
    """ An "ingredient" is everything that should be represented in standard text, line by line
    """
    @util.default_initializer
    def __init__(self, description):
        pass

    def str(self):
        return str(description)

    def cost(self):
        return 0

    def convert(self, new_unit):
        pass


class Garnish(Ingredient):
    """ An ingredient line that denotes it's a garnish
    """
    def str(self):
        return "{}, for garnish".format(super().str())


class QuantizedIngredient(Ingredient):
    """ Has a unit based on the raw quantity, responsible for unit conversions, text output
    """
    @util.default_initializer
    def __init__(self, type_, raw_quantity, recipe_unit):

        self.top_with = False
        # interpret the raw quantity
        if isinstance(raw_quantity, basestring):
            if raw_quantity == 'Top with':
                self.amount = util.convert_units(3.0, 'oz', 'recipe_unit', rounded=True)
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
                self.amount = tsp_to_volume(self.amount, unit)
            else:
                raise RecipeError("Unknown ingredient quantity: {} {}".format(raw_quantity, type_))
        else:
            self.amount = raw_quantity
            self.unit = recipe_unit

    def convert(self, new_unit):
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
        return "{}, (optional)".format(super().str())

