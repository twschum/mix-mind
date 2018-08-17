#!/usr/bin/env python
"""
Application main for the mixmind app
"""
from flask import Flask, render_template, flash, request, send_file, jsonify, redirect
from flask_uploads import UploadSet, DATA, configure_uploads
from werkzeug.utils import secure_filename # ??
import urllib
import flask_login


import os
import random
import logging

import recipe as drink_recipe
import util
import formatted_menu
from barstock import Barstock
from notifier import Notifier
from forms import DrinksForm, OrderForm, RecipeForm, RecipeListSelector, BarstockForm, LoginForm, RegisterUserForm
from models import db, User


"""
NOTES:
* refactor messages to look nicer
* menu schemas
    - would be able to include definitive item lists for serving, ice, tag, etc.
* update bootstrap
* user permissons (non-logged in vs admin)
    - flask-praetorian
    - google app engine
    - backend DB?
    - domain name
        - LetsEncrypt certs
* hardening
    - moar logging
    - test error handling
    - support concurrent users, single admin
* configuration management
    - defaults plus management
    - support for modifying the "bartender on duty" aka Notifier's secret info
    - disable the order button unless we are "open"
"""

# app config TODO move to __init__
app = Flask(__name__)
app.config.from_object(__name__)
with open('local_secret') as fp: # TODO config management
    app.config['SECRET_KEY'] = fp.read().strip()
app.config['UPLOADS_DEFAULT_DEST'] = './stockdb'
datafiles = UploadSet('datafiles', DATA)
configure_uploads(app, (datafiles,))
# general use db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # suppress deprecation warning
db.init_app(app)
# login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = "/login"

log = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    # return None on failure
    log.info("user_loader called")
    return User.query.get(user_id)

@login_manager.request_loader
def load_user_from_request(request):
    # first, try to login using the api_key url arg
    api_key = request.args.get('api_key')
    if api_key:
        user = User.query.filter_by(uuid_=api_key).first()
        if user:
            return user

    # next, try to login using Basic Auth
    api_key = request.headers.get('Authorization')
    if api_key:
        api_key = api_key.replace('Basic ', '', 1)
        try:
            api_key = base64.b64decode(api_key)
        except TypeError:
            pass
        user = User.query.filter_by(uuid_=api_key).first()
        if user:
            return user
    # finally, return None if both methods did not login the user
    return None

@app.route("/login", methods=['GET', 'POST'])
def login():
    """For GET requests, display the login form.
    For POSTS, login the current user by processing the form.
    """
    form = LoginForm(request.form)
    if form.errors:
        log.error(form.errors)
    log.debug(db)

    if request.method == 'POST':
        if form.validate():
            # TODO sanitize
            user_id = form.email.data
            user = User.query.get(user_id)
            if user:
                #if bcrypt.check_password_hash(user.password, form.password.data)
                if user.password == form.password.data:
                    user.authenticated = True
                    db.session.add(user)
                    db.session.commit()
                    flask_login.login_user(user, remember=False)
                    next_ = request.args.get('next', "/")
                    return redirect(next_)
            else:
                flash('Unknown user "{}"'.format(user_id), 'error')
        else:
            flash("Failure in form validation", 'error')
    return render_template("login.html", form=form)

@app.route("/logout", methods=['GET'])
def logout():
    """Logout the current user"""
    user = flask_login.current_user
    user.authenticated = False
    db.session.add(user)
    db.session.commit()
    flask_login.logout_user()
    return render_template("logout.html")


class MixMindServer():
    def __init__(self, recipes=['recipes_schubar.json','IBA_all.json'], barstock_files=['Barstock - Sheet1.csv']):
        self.recipe_files = recipes
        self.barstock_files = barstock_files
        self.base_recipes = util.load_recipe_json(recipes)
        self.barstock = Barstock.load(barstock_files)
        self.recipes = [drink_recipe.DrinkRecipe(name, recipe).generate_examples(self.barstock, stats=True) for name, recipe in self.base_recipes.iteritems()]
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
@flask_login.login_required
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

@app.route("/order/<recipe_name>", methods=['GET', 'POST'])
def order(recipe_name):
    form = OrderForm(request.form)
    recipe_name = urllib.unquote_plus(recipe_name)
    show_form = False

    recipe = util.find_recipe(mms.recipes, recipe_name)
    recipe.convert('oz')
    if not recipe:
        flash('Error: unknown recipe "{}"'.format(recipe_name))
        return render_template('order.html', form=form, recipe=None, show_form=False)
    else:
        recipe_html = formatted_menu.format_recipe_html(recipe,
                util.DisplayOptions(prices=True, stats=False, examples=True, all_ingredients=False,
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

@app.route('/json/<recipe_name>')
def recipe_json(recipe_name):
    recipe_name = urllib.unquote_plus(recipe_name)
    try:
        return jsonify(mms.base_recipes[recipe_name])
    except KeyError:
        return "{} not found".format(recipe_name)

@app.errorhandler(500)
def handle_internal_server_error(e):
    print e
    return render_template('error.html'), 500
