#!/usr/bin/env python

from flask import Flask, render_template, flash, request
from wtforms import validators, widgets, Form, Field, TextField, TextAreaField, StringField, SubmitField, BooleanField, DecimalField, IntegerField

import recipe as drink_recipe
import util
from formatted_menu import format_recipe_html
from barstock import Barstock

# app config
app = Flask(__name__)
app.config.from_object(__name__)
with open('local_secret') as fp:
    app.config['SECRET_KEY'] = fp.read().strip()


class MixMindServer():
    def __init__(self):
        base_recipes = util.load_recipe_json(['recipes.json'])
        barstock = Barstock.load('Barstock - Sheet1.csv', False)
        self.recipes = [drink_recipe.DrinkRecipe(name, recipe).generate_examples(barstock) for name, recipe in base_recipes.iteritems()]
        #self.recipes = {name:drink_recipe.DrinkRecipe(name, recipe) for name, recipe in base_recipes.iteritems()}

mms = MixMindServer()


class ReusableForm(Form):
    name = TextField('Name:', validators=[validators.required()])
    email = TextField('Email:', validators=[validators.required(), validators.Length(min=6, max=35)])
    password = TextField('Passwords:', validators=[validators.required(), validators.Length(min=3, max=35)])


class ToggleField(BooleanField):
    def __call__(self, **kwargs):
        return super(ToggleField, self).__call__(
                data_toggle="toggle",
                data_on="{} Enabled".format(self.label.text),
                data_off="{} Disabled".format(self.label.text),
                data_width="300",
                **kwargs)

class CSVField(Field):
    widget = widgets.TextInput()

    def _value(self):
        if self.data:
            return u', '.join(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [x.strip() for x in valuelist[0].split(',')]
        else:
            self.data = []

class ToggleButtonWidget(widgets.Input):
    pass

class DrinksForm(Form):
    def reset(self):
        blankData = MultiDict([ ('csrf', self.reset_csrf() ) ])
        self.process(blankData)

    # display options
    prices = BooleanField("Prices", description="Display prices for drinks based on stock")
    prep_line = BooleanField("Preparation", description="Display a line showing glass, ice, and prep")
    stats = BooleanField("Stats", description="Print out a detailed statistics block for the selected recipes")
    examples = BooleanField("Examples", description="Show specific examples of a recipe based on the ingredient stock")
    all_ingredients = BooleanField("All Ingredients", description="Show every ingredient instead of just the main liquors with each example")
    convert = TextField("Convert", description="Convert recipes to a different primary unit", default=None, validators=[validators.AnyOf(['oz','mL','cL']), validators.Optional()])
    markup = DecimalField("Markup", description="Drink markup: price = ceil((base_cost+1)*markup)", default=1.2)
    info = BooleanField("Info", description="Show the info line for recipes")
    origin = BooleanField("Origin", description="Check origin and mark drinks as Schubar originals")
    variants = BooleanField("Variants", description="Show variants for drinks")

    # filtering options
    all = BooleanField("Allow all ingredients", description="Include all ingredients from barstock whether or not that are marked in stock")
    include = CSVField("Include", description="Filter by ingredient(s) that must be contained in the recipe")
    exclude = CSVField("Exclude", description="Filter by ingredient(s) that must NOT be contained in the recipe")
    use_or = BooleanField("Logical OR", description="Use logical OR for included and excluded ingredient lists instead of default AND")
    # TODO make these selection fields
    style = TextField("Style", description="Include drinks matching the style such as After Dinner or Longdrink")
    glass = TextField("Glass", description="Include drinks matching the glass type such as cocktail or rocks")
    prep = TextField("Prep", description="Include drinks matching the prep method such as shake or build")
    ice = TextField("Ice", description="Include drinks matching the ice used such as crushed")

    # pdf options
    download_pdf = BooleanField("Download the Menu", description="Basename of the pdf and tex files generated")
    ncols = IntegerField("Number of columns", default=2, description="Number of columns to use for the menu")
    liquor_list = BooleanField("Liquor list", description="Show list of the available ingredients")
    liquor_list_own_page = BooleanField("Liquor list (own page)", description="Show list of the available ingredients on a separate page")
    debug = BooleanField("LaTeX debug output", description="Add debugging output to the pdf")
    align = BooleanField("Align items", description="Align drink names across columns")
    title = TextField("Title", description="Title to use")
    tagline = TextField("Tagline", description="Tagline to use below the title")


def bundle_options(tuple_class, args):
    return tuple_class(*(getattr(args, field).data for field in tuple_class._fields))

@app.route("/", methods=['GET', 'POST'])
def hello():
    #form = ReusableForm(request.form)
    form = DrinksForm(request.form)
    recipes = []
    display_options = None

    print form.errors
    if request.method == 'POST':
        if form.validate():
            # Save the comment here.
            flash("Settings applied")
            print request

            display_options = bundle_options(util.DisplayOptions, form)
            filter_options = bundle_options(util.FilterOptions, form)
            #recipes = util.filter_recipes(mms.recipes, filter_options)
            recipes = [format_recipe_html(recipe, display_options) for recipe in mms.recipes]

        else:
            flash("Error in form validation")

    return render_template('hello.html', form=form, recipes=recipes, nrecipes=len(recipes))


@app.route('/drinks.html')
def drinks_page():
    return app.send_static_file('drinks.html')

@app.route('/json/<recipe_name>')
def recipe_json(recipe_name):
    try:
        return str(mms.recipes[recipe_name])
    except KeyError:
        return "{} not found".format(recipe_name)



