#!/usr/bin/env python

from flask import Flask, render_template, flash, request
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField, BooleanField, DecimalField, widgets

import menu_gen
import recipe as drink_recipe

# app config
app = Flask(__name__)
app.config.from_object(__name__)
with open('local_secret') as fp:
    app.config['SECRET_KEY'] = fp.read().strip()


class MixMindServer():
    def __init__(self):
        base_recipes = menu_gen.load_recipe_json(['recipes.json'])
        self.recipes = {name:drink_recipe.DrinkRecipe(name, recipe) for name, recipe in base_recipes.iteritems()}

mms = MixMindServer()


class ReusableForm(Form):
    name = TextField('Name:', validators=[validators.required()])
    email = TextField('Email:', validators=[validators.required(), validators.Length(min=6, max=35)])
    password = TextField('Passwords:', validators=[validators.required(), validators.Length(min=3, max=35)])

    def reset(self):
        blankData = MultiDict([ ('csrf', self.reset_csrf() ) ])
        self.process(blankData)

class ToggleField(BooleanField):
    def __call__(self, **kwargs):
        return super(ToggleField, self).__call__(
                data_toggle="toggle",
                data_on="{} Enabled".format(self.label.text),
                data_off="{} Disabled".format(self.label.text),
                data_width="300",
                **kwargs)

class ToggleButtonWidget(widgets.Input):
    pass

class DrinksForm(Form):
    # display options
    prices = BooleanField("Prices", description="Display prices for drinks based on stock")
    prep_line = BooleanField("Preparation", description="Display a line showing glass, ice, and prep")
    stats = BooleanField("Stats", description="Print out a detailed statistics block for the selected recipes")
    examples = BooleanField("Examples", description="Show specific examples of a recipe based on the ingredient stock")
    convert = TextField("Convert", description="Convert recipes to a different primary unit", default=None, validators=[validators.AnyOf(['oz','mL','cL']), validators.Optional()])
    all_ingredients = BooleanField("All_ingredients", description="Show every ingredient instead of just the main liquors with each example")
    markup = DecimalField("Markup", description="Drink markup: price = ceil((base_cost+1)*markup)", default=1.2)
    ignore_info = BooleanField("Ignore_info", description="Don't show the info line for recipes", default="false")
    ignore_origin = BooleanField("Ignore_origin", description="Don't check origin and mark drinks as Schubar originals")
    ignore_variants = BooleanField("Ignore_variants", description="Don't show variants for drinks")

    # filtering options
    #p.add_argument('-a', '--all', action='store_true', help="Include all ingredients from barstock whether or not that are marked in stock")
    #p.add_argument('-i', '--include', nargs='+', help="Filter by ingredient(s) that must be contained in the recipe")
    #p.add_argument('-x', '--exclude', nargs='+', help="Filter by ingredient(s) that must NOT be contained in the recipe")
    #p.add_argument('--or', dest='use_or', action='store_true', help="use logical OR for included and excluded ingredient lists instead of default AND")
    #p.add_argument('--style', help="Include drinks matching the style such as After Dinner or Longdrink")
    #p.add_argument('--glass', help="Include drinks matching the style such as After Dinner or Longdrink")
    #p.add_argument('--prep', help="Include drinks matching the style such as After Dinner or Longdrink")
    #p.add_argument('--ice', help="Include drinks matching the style such as After Dinner or Longdrink")

@app.route("/", methods=['GET', 'POST'])
def hello():
    #form = ReusableForm(request.form)
    form = DrinksForm(request.form)
    drink = None


    print form.errors
    if request.method == 'POST':
        name=request.form['name']
        password=request.form['password']
        email=request.form['email']
        print name, " ", email, " ", password

        if form.validate():
            # Save the comment here.
            flash('Thanks for registration ' + name)
            print request
        else:
            flash('Error: All the form fields are required. ')

    return render_template('hello.html', form=form, drink=drink)


@app.route('/json/<recipe_name>')
def recipe_json(recipe_name):
    try:
        return str(mms.recipes[recipe_name])
    except KeyError:
        return "{} not found".format(recipe_name)



