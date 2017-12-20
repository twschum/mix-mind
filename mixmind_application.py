#!/usr/bin/env python

from flask import Flask, render_template, flash, request, send_file
from wtforms import validators, widgets, Form, Field, FormField, FieldList, TextField, TextAreaField, BooleanField, DecimalField, IntegerField, SelectField

import os

import recipe as drink_recipe
import util
import formatted_menu
from barstock import Barstock

# app config
app = Flask(__name__)
app.config.from_object(__name__)
with open('local_secret') as fp:
    app.config['SECRET_KEY'] = fp.read().strip()


class MixMindServer():
    def __init__(self):
        base_recipes = util.load_recipe_json(['recipes.json'])
        self.barstock = Barstock.load('Barstock - Sheet1.csv', False)
        self.recipes = [drink_recipe.DrinkRecipe(name, recipe).generate_examples(self.barstock) for name, recipe in base_recipes.iteritems()]
mms = MixMindServer()


class CSVField(Field):
    widget = widgets.TextInput()

    def _value(self):
        if self.data:
            return u', '.join(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist[0]:
            self.data = [x.strip().lower() for x in valuelist[0].split(',') if x.strip()]
        else:
            self.data = []


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
    convert = TextField("Convert", description="Convert recipes to a different primary unit", default=None, validators=[validators.AnyOf(util.VALID_UNITS), validators.Optional()])
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
    pdf_filename = TextField("Filename to use", description="Basename of the pdf and tex files generated", default="web_drinks_file")
    ncols = IntegerField("Number of columns", default=2, description="Number of columns to use for the menu")
    liquor_list = BooleanField("Liquor list", description="Show list of the available ingredients")
    liquor_list_own_page = BooleanField("Liquor list (own page)", description="Show list of the available ingredients on a separate page")
    debug = BooleanField("LaTeX debug output", description="Add debugging output to the pdf")
    align = BooleanField("Align items", description="Align drink names across columns")
    title = TextField("Title", description="Title to use")
    tagline = TextField("Tagline", description="Tagline to use below the title")


class IngredientField(Form):
    ingredient = TextField("Ingredient", validators=[validators.required()])
    quantity = DecimalField("Quantity", validators=[validators.required()])
    is_optional = BooleanField("Optional")

class RecipeForm(Form):
    name = TextField("Name", description="The recipe name", validators=[validators.required()])
    info = TextField("Info", description="Additional information about the recipe")
    ingredients = FieldList(FormField(IngredientField), min_entries=1, validators=[validators.required()])
    unit = SelectField("Unit", choices=[util.VALID_UNITS], validators=[validators.required()])
    #glass =
    #unit =
    #prep =
    #ice =
    #garnish =


def bundle_options(tuple_class, args):
    return tuple_class(*(getattr(args, field).data for field in tuple_class._fields))

def recipes_from_options(form, to_html=False):
    display_options = bundle_options(util.DisplayOptions, form)
    filter_options = bundle_options(util.FilterOptions, form)
    recipes, excluded = util.filter_recipes(mms.recipes, filter_options)
    if form.convert.data:
        map(lambda r: r.convert(form.convert.data), recipes)
    if to_html:
        recipes = [formatted_menu.format_recipe_html(recipe, display_options) for recipe in recipes]
    return recipes

@app.route("/", methods=['GET', 'POST'])
def mainpage():
    form = DrinksForm(request.form)
    print form.errors
    recipes = []
    excluded = None

    if request.method == 'POST':
        if form.validate():
            print request
            recipes = recipes_from_options(form, to_html=True)
            flash("Settings applied. Showing {} available recipes".format(len(recipes)))
        else:
            flash("Error in form validation")

    return render_template('application_main.html', form=form, recipes=recipes, excluded=excluded)

@app.route("/download/", methods=['POST'])
def menu_download():
    form = DrinksForm(request.form)
    print form.errors

    if form.validate():
        print request
        recipes = recipes_from_options(form)

        display_options = bundle_options(util.DisplayOptions, form)
        form.pdf_filename.data = formatted_menu.filename_from_options(bundle_options(util.PdfOptions, form), display_options)
        pdf_options = bundle_options(util.PdfOptions, form)
        pdf_file = '{}.pdf'.format(pdf_options.pdf_filename)

        formatted_menu.generate_recipes_pdf(recipes, pdf_options, display_options, mms.barstock.df)
        return send_file(os.path.abspath(pdf_file), 'application/pdf', as_attachment=True, attachment_filename=pdf_file)

    else:
        flash("Error in form validation")
        return render_template('application_main.html', form=form, recipes=[], excluded=None)

@app.route("/recipes/", methods=['GET','POST'])
def recipe_edit():
    form = RecipeForm(request.form)
    print form.errors

    if request.method == 'POST':
        print request

        print form.name

    return render_template('recipes.html', form=form)


@app.route('/drinks.html')
def drinks_page():
    return app.send_static_file('drinks.html')

@app.route('/json/<recipe_name>')
def recipe_json(recipe_name):
    try:
        return str(mms.recipes[recipe_name])
    except KeyError:
        return "{} not found".format(recipe_name)

