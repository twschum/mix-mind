"""
Application main for the mixmind app
"""
import os
import random

from flask import render_template, flash, request, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import urllib
from flask_security import login_required, roles_required
from flask_login import current_user

from .notifier import Notifier
from .forms import DrinksForm, OrderForm, RecipeForm, RecipeListSelector, BarstockForm, LoginForm, RegisterUserForm
from .authorization import user_datastore
from .recipe import DrinkRecipe
from .barstock import get_barstock_instance
from .formatted_menu import format_recipe_html, filename_from_options, generate_recipes_pdf
from .util import filter_recipes, DisplayOptions, FilterOptions, PdfOptions, load_recipe_json, report_stats, find_recipe
from .database import db, init_db
from . import log, app, datafiles
import config

"""
BUGS:
* abv shows as 0.0% for everything on recipe examples
NOTES:
* template standardization
    - actually use jinja inheritance for pages
    - header (and maybe footer?)
        - provide user login and register links?
    - refactor messages to look nicer
        - include a standard place and look for all messages (top of page?)
    - make security forms look nicer
    - make email template
* admin pages
    - add/remove ingredients dynamically?
    - add/remove recipes as raw json?
    - menu_generator (what's now "mainpage")
    - user stats dashboard
* user improvements
    - order history
    - venmo links lol
* menu schemas
    - would be able to include definitive item lists for serving, ice, tag, etc.
* update bootstrap
* hardening
    - moar logging
    - test error handling
* configuration management
    - defaults plus management
    - support for modifying the "bartender on duty" aka Notifier's secret info
    - disable the order button unless we are "open"
* order workflow
    - if not logged in, take them to a login/registration form,
    prepopulated with name and address
    - track unconfirmed orders
"""
# views-wide domain-specific state
mms = None
@app.before_first_request
def initialize_shared_data():
    global mms
    mms = MixMindServer()

class MixMindServer():
    # TODO synchronization
    def __init__(self, recipe_files=None, ingredient_files=None):
        self.recipe_files = config.get_recipe_files(app) if not recipe_files else recipe_files
        self.barstock_files = config.get_ingredient_files(app) if not ingredient_files else ingredient_files
        self.base_recipes = load_recipe_json(self.recipe_files)
        self.barstock = get_barstock_instance(self.barstock_files, use_sql=True)
        self.recipes = [DrinkRecipe(name, recipe).generate_examples(self.barstock, stats=True) for name, recipe in self.base_recipes.iteritems()]
        self.notifier = Notifier('secrets.json', 'simpler_email_template.html')
        self.default_margin = 1.10

    def get_ingredients_table(self):
        raise NotImplementedError("unavailable for now")
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


def bundle_options(tuple_class, args):
    return tuple_class(*(getattr(args, field).data for field in tuple_class._fields))

def recipes_from_options(form, display_opts=None, filter_opts=None, to_html=False, order_link=False, **kwargs_for_html):
    """ Apply display formmatting, filtering, sorting to
    the currently loaded recipes.
    Also can generate stats
    May convert to html, including extra options for that
    Apply sorting
    """
    display_options = bundle_options(DisplayOptions, form) if not display_opts else display_opts
    filter_options = bundle_options(FilterOptions, form) if not filter_opts else filter_opts
    recipes, excluded = filter_recipes(mms.recipes, filter_options)
    if form.sorting.data and form.sorting.data != 'None': # TODO this is weird
        reverse = 'X' in form.sorting.data
        attr = 'avg_{}'.format(form.sorting.data.rstrip('X'))
        recipes = sorted(recipes, key=lambda r: getattr(r.stats, attr), reverse=reverse)
    if form.convert.data:
        map(lambda r: r.convert(form.convert.data), recipes)
    if display_options.stats and recipes:
        stats = report_stats(recipes, as_html=True)
    else:
        stats = None
    if to_html:
        if order_link:
            recipes = [format_recipe_html(recipe, display_options,
                order_link="/order/{}".format(urllib.quote_plus(recipe.name)),
                **kwargs_for_html) for recipe in recipes]
        else:
            recipes = [format_recipe_html(recipe, display_options, **kwargs_for_html) for recipe in recipes]
    return recipes, excluded, stats

@app.route("/main/", methods=['GET', 'POST'])
@login_required
@roles_required('admin')
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
@login_required
@roles_required('admin')
def menu_download():
    form = DrinksForm(request.form)
    print form.errors

    if form.validate():
        print request
        recipes, _, _ = recipes_from_options(form)

        display_options = bundle_options(DisplayOptions, form)
        form.pdf_filename.data = 'menus/{}'.format(filename_from_options(bundle_options(PdfOptions, form), display_options))
        pdf_options = bundle_options(PdfOptions, form)
        pdf_file = '{}.pdf'.format(pdf_options.pdf_filename)

        generate_recipes_pdf(recipes, pdf_options, display_options, mms.barstock.df)
        return send_file(os.path.abspath(pdf_file), 'application/pdf', as_attachment=True, attachment_filename=pdf_file.lstrip('menus/'))

    else:
        flash("Error in form validation")
        return render_template('application_main.html', form=form, recipes=[], excluded=None)

@app.route("/post_login/", methods=['GET'])
def post_login_redirect():
    # show main if admin user
    # maybe use post-register for assigning a role
    if 'admin' in current_user.roles:
        return redirect(url_for('mainpage'))
    else:
        return redirect(url_for('browse'))

@app.route("/", methods=['GET', 'POST'])
def browse():
    form = DrinksForm(request.form)
    filter_options = None
    log.error(form.errors)

    if request.method == 'GET':
        # filter for current recipes that can be made on the core list
        filter_options = FilterOptions(all_=False,include="",exclude="",use_or=False,style="",glass="",prep="",ice="",name="",tag="core")

    recipes, _, _ = recipes_from_options(form, display_opts=DisplayOptions(True,False,False,False,mms.default_margin,False,False,True,False),
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

@app.route("/order/<recipe_name>", methods=['GET', 'POST'])
def order(recipe_name):
    form = OrderForm(request.form)
    recipe_name = urllib.unquote_plus(recipe_name)
    show_form = False

    recipe = find_recipe(mms.recipes, recipe_name)
    recipe.convert('oz')
    if not recipe:
        flash('Error: unknown recipe "{}"'.format(recipe_name))
        return render_template('order.html', form=form, recipe=None, show_form=False)
    else:
        recipe_html = format_recipe_html(recipe,
                DisplayOptions(prices=True, stats=False, examples=True, all_ingredients=False,
                    markup=mms.default_margin, prep_line=True, origin=True, info=True, variants=True))

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
@login_required
@roles_required('admin')
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
@login_required
@roles_required('admin')
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
            # TODO remove all this replace with new system that's like ordering
            bottle = form.bottle.data
            if bottle in mms.barstock.df.Bottle.values:
                mms.barstock.df = mms.barstock.df[mms.barstock.df.Bottle != bottle]
                mms.regenerate_recipes()
                flash("Removed {}".format(bottle))
            else:
                flash("Error: \"{}\" not found; must match as shown below exactly".format(bottle))

        elif 'upload-csv' in request.form:
            filename = datafiles.save(secure_filename(request.files['upload_csv']))
            print "CSV uploaded to {}".format(filename)
            mms = MixMindServer(recipes=mms.recipe_files, barstock_files=[filename])
            flash("Ingredients database reloaded from {}".format(filename))

    table = mms.get_ingredients_table()
    return render_template('ingredients.html', form=form, table=table)

@app.route('/json/<recipe_name>')
def recipe_json(recipe_name):
    recipe_name = urllib.unquote_plus(recipe_name)
    try:
        return jsonify(mms.base_recipes[recipe_name])
    except KeyError:
        return "{} not found".format(recipe_name)

@app.errorhandler(500)
def handle_internal_server_error(e):
    flash(e, 'error')
    return render_template('error.html'), 500
