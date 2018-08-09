#!/usr/bin/env python

from flask import Flask, render_template, flash, request, send_file
from flask_uploads import UploadSet, DATA, configure_uploads
from wtforms import validators, widgets, Form, Field, FormField, FieldList, TextField, TextAreaField, BooleanField, DecimalField, IntegerField, SelectField, SelectMultipleField, FileField
from werkzeug.utils import secure_filename
import urllib

import os
import random

import recipe as drink_recipe
import util
import formatted_menu
from barstock import Barstock
from notifier import Notifier

# TODO refactor messages to look nicer
# TODO menu schemas
#   would be able to include definitive item lists for serving, ice, tag, etc.

"""
NOTES:
"""

# app config
app = Flask(__name__)
app.config.from_object(__name__)
with open('local_secret') as fp:
    app.config['SECRET_KEY'] = fp.read().strip()
app.config['UPLOADS_DEFAULT_DEST'] = './stockdb'
datafiles = UploadSet('datafiles', DATA)
configure_uploads(app, (datafiles,))


class MixMindServer():
    def __init__(self, recipes=['recipes_schubar.json','IBA_all.json'], barstock_files=['Barstock - Sheet1.csv']):
        self.recipe_files = recipes
        self.barstock_files = barstock_files
        base_recipes = util.load_recipe_json(recipes)
        self.barstock = Barstock.load(barstock_files)
        self.recipes = [drink_recipe.DrinkRecipe(name, recipe).generate_examples(self.barstock, stats=True) for name, recipe in base_recipes.iteritems()]
        self.notifier = Notifier('secrets.json', 'simpler_email_template.html')
        self.default_margin = 1.10

        url = "https://ipv4.icanhazip.com/"
        try:
            self.ip = urllib.urlopen(url).read().rstrip('\n')
            print "Server running on: {}".format(self.ip)
        except Exception as err:
            print err

    def get_ingredients_table(self):
        df = self.barstock.sorted_df()
        df.Proof = df.Proof.astype('int')
        df['Size (mL)'] = df['Size (mL)'].astype('int')
        df = df[df.Category != 'Ice']
        df = df[df['In Stock'] > 0]
        table = df.to_html(index=False,
                columns='Category,Type,Bottle,Proof,Size (mL),Price Paid'.split(','))
        return table

    def regenerate_recipes(self):
        self.recipes = [recipe.generate_examples(self.barstock, stats=True) for recipe in  self.recipes]

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

def pairs(l):
    return [(x,x) for x in l]

class DrinksForm(Form):
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)

    # display options
    prices = BooleanField("Prices", description="Display prices for drinks based on stock")
    prep_line = BooleanField("Preparation", description="Display a line showing glass, ice, and prep")
    stats = BooleanField("Stats", description="Print out a detailed statistics block for the selected recipes")
    examples = BooleanField("Examples", description="Show specific examples of a recipe based on the ingredient stock")
    all_ingredients = BooleanField("All Ingredients", description="Show every ingredient instead of just the main liquors with each example")
    convert = TextField("Convert", description="Convert recipes to a different primary unit", default=None, validators=[validators.AnyOf(util.VALID_UNITS), validators.Optional()])
    markup = DecimalField("Margin", description="Drink markup: price = ceil((base_cost+1)*markup)", default=mms.default_margin)
    info = BooleanField("Info", description="Show the info line for recipes")
    origin = BooleanField("Origin", description="Check origin and mark drinks as Schubar originals")
    variants = BooleanField("Variants", description="Show variants for drinks")

    # filtering options
    all_ = BooleanField("Allow all ingredients", description="Include all recipes, regardless of if they can be made from the loaded barstock")
    include = CSVField("Include Ingredients", description="Filter by ingredient(s) that must be contained in the recipe")
    exclude = CSVField("Exclude Ingredients", description="Filter by ingredient(s) that must NOT be contained in the recipe")
    use_or = BooleanField("Logical OR", description="Use logical OR for included and excluded ingredient lists instead of default AND")
    name = TextField("Name", description="Filter by a cocktail's name")
    tag = TextField("Tag", description="Filter by tag")
    style = SelectField("Style", description="Include drinks matching the style such as After Dinner or Longdrink", choices=pairs(['','All Day Cocktail','Before Dinner Cocktail','After Dinner Cocktail','Longdrink', 'Hot Drink', 'Sparkling Cocktail', 'Wine Cocktail']))
    glass = SelectField("Glass", description="Include drinks matching the glass type such as cocktail or rocks", choices=pairs(['','cocktail','rocks','highball','flute','shot']))
    prep = SelectField("Prep", description="Include drinks matching the prep method such as shake or build", choices=pairs(['','shake', 'stir', 'build']))
    ice = SelectField("Ice", description="Include drinks matching the ice used such as crushed", choices=pairs(['','cubed','chushed','neat']))

    # sorting options
    # abv, cost, alcohol content
    sorting = SelectField("Sort Results", choices=[
        ("", ""),
        ('abv', "ABV (Low to High)"),
        ('abvX', "ABV (High to Low)"),
        ('cost', "Cost ($ to $$$)"),
        ('costX', "Cost ($$$ to $)"),
        ('std_drinks', "Total Alcohol (Low to High)"),
        ('std_drinksX', "Total Alcohol (High to Low)"),
    ])

    # pdf options
    pdf_filename = TextField("Filename to use", description="Basename of the pdf and tex files generated", default="web_drinks_file")
    ncols = IntegerField("Number of columns", default=2, description="Number of columns to use for the menu")
    liquor_list = BooleanField("Liquor list", description="Show list of the available ingredients")
    liquor_list_own_page = BooleanField("Liquor list (own page)", description="Show list of the available ingredients on a separate page")
    debug = BooleanField("LaTeX debug output", description="Add debugging output to the pdf")
    align = BooleanField("Align items", description="Align drink names across columns")
    title = TextField("Title", description="Title to use")
    tagline = TextField("Tagline", description="Tagline to use below the title")


class RecipeIngredientForm(Form):
    ingredient = TextField("Ingredient", validators=[validators.required()])
    quantity = DecimalField("Quantity", validators=[validators.required()])
    is_optional = BooleanField("Optional")
class RecipeForm(Form):
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)
    name = TextField("Name", description="The recipe name", validators=[validators.required()])
    info = TextField("Info", description="Additional information about the recipe")
    ingredients = FieldList(FormField(RecipeIngredientForm), min_entries=1, validators=[validators.required()])
    unit = SelectField("Unit", choices=pairs([util.VALID_UNITS]), validators=[validators.required()])
    #glass =
    #unit =
    #prep =
    #ice =
    #garnish =

class RecipeListSelector(Form):
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)
    recipes = SelectMultipleField("Available Recipe Lists", description="Select recipe lists to be used for generating a menu",
            choices=[("recipes_schubar.json", "Core Recipes (from @Schubar)"),
                ("IBA_unforgettables.json", "IBA Unforgettables"),
                ("IBA_contemporary_classics.json", "IBA Contemporary Classics"),
                ("IBA_new_era_drinks.json", "IBA New Era Drinks")])

class BarstockForm(Form):
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)
    upload_csv = FileField("Upload a Barstock CSV", [validators.regexp(ur'^[^/\\]\.csv$')])

    categories = 'Spirit,Liqueur,Vermouth,Bitters,Syrup,Dry,Juice,Mixer,Wine,Ice'.split(',')
    types = ',Brandy,Dry Gin,Genever,Amber Rum,White Rum,Dark Rum,Rye Whiskey,Vodka,Orange Liqueur,Dry Vermouth,Sweet Vermouth,Aromatic Bitters,Orange Bitters,Fruit Bitters,Bourbon Whiskey,Tennessee Whiskey,Irish Whiskey,Scotch Whisky,Silver Tequila,Gold Tequila,Mezcal,Aquavit,Amaretto,Blackberry Liqueur,Raspberry Liqueur,Campari,Amaro,Cynar,Aprol,Creme de Cacao,Creme de Menthe,Grenadine,Simple Syrup,Rich Simple Syrup,Honey Syrup,Orgeat,Maple Syrup,Sugar'.split(',')
    category = SelectField("Category", validators=[validators.required()], choices=pairs(categories))
    type_ = SelectField("Type", validators=[validators.required()], choices=pairs(types))
    bottle = TextField("Bottle", description='Specify the bottle, e.g. "Bulliet Rye", "Beefeater", "Tito\'s", or "Bacardi Carta Blanca"', validators=[validators.required()])
    proof = DecimalField("Proof", description="Proof rating of the ingredient, if any", validators=[validators.required(), validators.NumberRange(min=0, max=200)])
    size_ml = DecimalField("Size (mL)", description="Size of the ingredient in mL", validators=[validators.required(), validators.NumberRange(min=0, max=20000)])
    price = DecimalField("Price ($)", description="Price paid or approximate market value in USD", validators=[validators.required(), validators.NumberRange(min=0, max=2000)])

def bundle_options(tuple_class, args):
    return tuple_class(*(getattr(args, field).data for field in tuple_class._fields))

def recipes_from_options(form, display_opts=None, filter_opts=None, to_html=False, order_link=False, **kwargs_for_html):
    """ Apply display formmatting, filtering, sorting to
    the currently loaded recipes.
    Also can generate stats
    May convert to html, including extra options for that
    Apply sorting
    """
    display_options = bundle_options(util.DisplayOptions, form) if not display_opts else display_opts
    filter_options = bundle_options(util.FilterOptions, form) if not filter_opts else filter_opts
    recipes, excluded = util.filter_recipes(mms.recipes, filter_options)
    if form.sorting.data and form.sorting.data != 'None': # TODO this is weird
        reverse = 'X' in form.sorting.data
        attr = 'avg_{}'.format(form.sorting.data.rstrip('X'))
        recipes = sorted(recipes, key=lambda r: getattr(r.stats, attr), reverse=reverse)
    if form.convert.data:
        map(lambda r: r.convert(form.convert.data), recipes)
    if display_options.stats and recipes:
        stats = util.report_stats(recipes, as_html=True)
    else:
        stats = None
    if to_html:
        if order_link:
            recipes = [formatted_menu.format_recipe_html(recipe, display_options,
                order_link="/order/{}".format(urllib.quote_plus(recipe.name)),
                **kwargs_for_html) for recipe in recipes]
        else:
            recipes = [formatted_menu.format_recipe_html(recipe, display_options, **kwargs_for_html) for recipe in recipes]
    return recipes, excluded, stats

@app.route("/main/", methods=['GET', 'POST'])
def mainpage():
    form = DrinksForm(request.form)
    print form.errors
    recipes = []
    excluded = None
    stats = None

    if request.method == 'POST':
        if form.validate():
            print request
            recipes, excluded, stats = recipes_from_options(form, to_html=True)
            flash("Settings applied. Showing {} available recipes".format(len(recipes)))
        else:
            flash("Error in form validation")

    return render_template('application_main.html', form=form, recipes=recipes, excluded=excluded, stats=stats)

@app.route("/download/", methods=['POST'])
def menu_download():
    form = DrinksForm(request.form)
    print form.errors

    if form.validate():
        print request
        recipes, _, _ = recipes_from_options(form)

        display_options = bundle_options(util.DisplayOptions, form)
        form.pdf_filename.data = 'menus/{}'.format(formatted_menu.filename_from_options(bundle_options(util.PdfOptions, form), display_options))
        pdf_options = bundle_options(util.PdfOptions, form)
        pdf_file = '{}.pdf'.format(pdf_options.pdf_filename)

        formatted_menu.generate_recipes_pdf(recipes, pdf_options, display_options, mms.barstock.df)
        return send_file(os.path.abspath(pdf_file), 'application/pdf', as_attachment=True, attachment_filename=pdf_file.lstrip('menus/'))

    else:
        flash("Error in form validation")
        return render_template('application_main.html', form=form, recipes=[], excluded=None)

@app.route("/", methods=['GET', 'POST'])
def browse():
    form = DrinksForm(request.form)
    filter_options = None
    print form.errors

    # TODO main browse with no filters shows core recipes,
    # but when filtering pull in the extended lists as well

    if request.method == 'GET':
        # filter for current recipes that can be made on the core list
        filter_options = util.FilterOptions(all_=False,include="",exclude="",use_or=False,style="",glass="",prep="",ice="",name="",tag="core")

    recipes, _, _ = recipes_from_options(form, display_opts=util.DisplayOptions(True,False,False,False,mms.default_margin,False,False,True,False),
            filter_opts=filter_options, to_html=True, order_link=True, condense_ingredients=True)

    if request.method == 'POST':
        if form.validate():
            print request
            if 'suprise-menu' in request.form:
                recipes = [random.choice(recipes)]
                flash("Bartender's choice applied. Just try again if you want something else!")
            else:
                flash("Settings applied. Showing {} available recipes".format(len(recipes)))
        else:
            flash("Error in form validation")

    return render_template('browse.html', form=form, recipes=recipes)

class OrderForm(Form):
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)
    name = TextField("Your Name", validators=[validators.required()])
    email = TextField("Confirmation Email", validators=[validators.Email("Invalid email address"), validators.required()])
    notes = TextField("Notes")

@app.route("/order/<recipe_name>", methods=['GET', 'POST'])
def order(recipe_name):
    form = OrderForm(request.form)
    recipe_name = urllib.unquote_plus(recipe_name)
    show_form = False

    # TODO failure mode because of missing ingredients

    recipe = util.find_recipe(mms.recipes, recipe_name)
    recipe.convert('oz')
    if not recipe:
        flash('Error: unknown recipe "{}"'.format(recipe_name))
        return render_template('order.html', form=form, recipe=None, show_form=False)
    else:
        recipe_html = formatted_menu.format_recipe_html(recipe, util.DisplayOptions(True,False,False,False,mms.default_margin,True,False,True,True))

    if request.method == 'GET':
        show_form = True
        if not recipe.can_make:
            flash('Ingredients to make this are out of stock!', 'error')


    if request.method == 'POST':
        if 'submit-order' in request.form:
            if not recipe.can_make:
                flash('Ingredients to make this are out of stock!', 'error')
                return render_template('order.html', form=form, recipe=recipe_html, show_form=True)

            if form.validate():
                # get request arg
                subject = "New @Schubar Order - {}".format(recipe.name)
                mms.notifier.send(subject, {
                    '_GREETING_': "{} has ordered a {}".format(form.name.data, recipe.name),
                    '_SUMMARY_': "<a href=http://{}/confirm?email={}&recipe={}>Send Confirmation</a>".format(mms.ip,
                        urllib.quote(form.email.data), urllib.quote(recipe.name) ),
                    '_RECIPE_': "{}".format(recipe_html),
                    '_EXTRA_': "{}".format(form.notes.data)
                    })
                flash("Successfully placed order!")
            else:
                show_form=True
                flash("Error in form validation", 'error')

    # either provide the recipe and the form,
    # or after the post show the result
    return render_template('order.html', form=form, recipe=recipe_html, show_form=show_form)

@app.route('/confirm')
def confirmation():
    email = urllib.unquote(request.args.get('email'))
    recipe = urllib.unquote(request.args.get('recipe'))
    mms.notifier.send("Your @Schubar Confirmation",
            { '_GREETING_': "You ordered {}".format(recipe),
              '_SUMMARY_': 'Your drink order as been acknowledged by the Bartender and should be ready shortly.',
              '_RECIPE_': 'Thanks for using Mix-Mind @Schubar!',
              '_EXTRA_': ''}, alt_target=email)
    flash('Confirmation sent')
    return render_template('order.html', form=None, recipe=None, show_form=False)

@app.route("/recipes/", methods=['GET','POST'])
def recipes():
    global mms
    select_form = RecipeListSelector(request.form)
    print select_form.errors
    add_form = RecipeForm(request.form)
    print add_form.errors

    if request.method == 'POST':
        print request
        if 'recipe-list-select' in request.form:
            recipes = select_form.recipes.data
            mms = MixMindServer(recipes=recipes, barstock_files=mms.barstock_files)
            flash("Now using recipes from {}".format(recipes))

    return render_template('recipes.html', select_form=select_form, add_form=add_form)

@app.route("/ingredients/", methods=['GET','POST'])
def ingredients():
    global mms
    form = BarstockForm(request.form)
    print form.errors

    if request.method == 'POST':
        print request
        if 'add-ingredient' in request.form:
            row = {}
            row['Category'] = form.category.data
            row['Type'] = form.type_.data
            row['Bottle'] = form.bottle.data
            row['Proof'] = float(form.proof.data)
            row['Size (mL)'] = float(form.size_ml.data)
            row['Price Paid'] = float(form.price.data)
            mms.barstock.add_row(row)
            mms.regenerate_recipes()

        elif 'remove-ingredient' in request.form:
            bottle = form.bottle.data
            if bottle in mms.barstock.df.Bottle.values:
                mms.barstock.df = mms.barstock.df[mms.barstock.df.Bottle != bottle]
                mms.regenerate_recipes()
                flash("Removed {}".format(bottle))
            else:
                flash("Error: \"{}\" not found; must match as shown below exactly".format(bottle))

        elif 'upload-csv' in request.form:
            filename = datafiles.save(request.files['upload_csv'])
            print "CSV uploaded to {}".format(filename)
            mms = MixMindServer(recipes=mms.recipe_files, barstock_files=[filename])
            flash("Ingredients database reloaded from {}".format(filename))

    table = mms.get_ingredients_table()
    return render_template('ingredients.html', form=form, table=table)

@app.route('/drinks.html')
def drinks_page():
    return app.send_static_file('drinks.html')

@app.route('/json/<recipe_name>')
def recipe_json(recipe_name):
    try:
        return str(mms.recipes[recipe_name])
    except KeyError:
        return "{} not found".format(recipe_name)

