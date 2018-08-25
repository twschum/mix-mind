"""
Application main for the mixmind app
"""
import os
import random
import datetime

from flask import render_template, flash, request, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import urllib
from flask_security import login_required, roles_required
from flask_security.decorators import _get_unauthorized_view
from flask_login import current_user

from .notifier import send_mail
from .forms import DrinksForm, OrderForm, OrderFormAnon, RecipeForm, RecipeListSelector, BarstockForm, LoginForm
from .authorization import user_datastore
from .recipe import DrinkRecipe
from .barstock import get_barstock_instance
from .formatted_menu import filename_from_options, generate_recipes_pdf
from .compose_html import recipe_as_html, users_as_table, orders_as_table
from .util import filter_recipes, DisplayOptions, FilterOptions, PdfOptions, load_recipe_json, report_stats, find_recipe
from .database import db, init_db
from .models import User, Order, Bar
from . import log, app, datafiles
import config

"""
BUGS:
* markup seems to have changed?
* email sent to customer not bartender
NOTES:
* cards should be same sizes
* template improvements
    - header
        - move greeting over to right with log in/out
    - make email template
        - use custom html template params (price fails in email)
        - change email confirmation to result page
        - order submission had wrong name
    - use more bootstrap form goodness
* admin pages
    - add/remove ingredients dynamically?
    - add/remove recipes as raw json?
    - menu_generator (what's now "mainpage")
    - user stats dashboard
* better commits to db with after_this_request
* user improvements
    - order history
* menu schemas
    - would be able to include definitive item lists for serving, ice, tag, etc.
* update bootstrap
* hardening
    - moar logging
    - test error handling
* configuration management
    - support for multiple bars!
    - defaults plus management
    - support for modifying the "bartender on duty" aka Notifier's secret info
    - disable the order button unless we are "open"
* "remember" form open/close position
"""
# views-wide domain-specific state
mms = None
@app.before_first_request
def initialize_shared_data():
    global mms
    mms = MixMindServer()
    # invalidate users
    #for user in User.query.all():
        #user.confirmed_at = None
    #db.session.commit()

class MixMindServer():
    # TODO synchronization
    def __init__(self, recipe_files=None, ingredient_files=None):
        # setup current "bar"
        default_bar = Bar(cname=app.config['BAR_CNAME'], name=app.config.get('BAR_NAME', app.config['BAR_CNAME']))
        exists = Bar.query.filter_by(cname=default_bar.cname).one_or_none()
        if exists:
            self.current_bar = exists.id
        else:
            db.session.add(default_bar)
            db.session.commit()
            self.current_bar = default_bar.id
        self.recipe_files = config.get_recipe_files(app) if not recipe_files else recipe_files
        self.barstock_files = config.get_ingredient_files(app) if not ingredient_files else ingredient_files
        self.base_recipes = load_recipe_json(self.recipe_files)
        self.barstock = get_barstock_instance(self.barstock_files, use_sql=True, bar=self.current_bar)
        self.recipes = [DrinkRecipe(name, recipe).generate_examples(self.barstock, stats=True) for name, recipe in self.base_recipes.iteritems()]
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

def get_form(form_class):
    """WTForms update 2.2 breaks when an empty request.form
    is given to it """
    if not request.form:
        return form_class()
    return form_class(request.form)

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
            recipes = [recipe_as_html(recipe, display_options,
                order_link="/order/{}".format(urllib.quote_plus(recipe.name)),
                **kwargs_for_html) for recipe in recipes]
        else:
            recipes = [recipe_as_html(recipe, display_options, **kwargs_for_html) for recipe in recipes]
    return recipes, excluded, stats


################################################################################
# Customer routes
################################################################################


@app.route("/", methods=['GET', 'POST'])
def browse():
    form = get_form(DrinksForm)
    filter_options = None

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
                flash("Bartender's choice! Just try again if you want something else!")
            else:
                n_results = len(recipes)
                if n_results > 0:
                    flash("Filters applied. Showing {} available recipes".format(n_results), 'success')
                else:
                    flash("No results after filtering, try being less specific", 'warning')
        else:
            flash("Error in form validation", 'danger')

    return render_template('browse.html', form=form, recipes=recipes)

@app.route("/order/<recipe_name>", methods=['GET', 'POST'])
def order(recipe_name):
    global mms
    if current_user.is_authenticated:
        form = get_form(OrderForm)
    else:
        form = get_form(OrderFormAnon)

    recipe_name = urllib.unquote_plus(recipe_name)
    show_form = False
    heading = "Order:"

    recipe = find_recipe(mms.recipes, recipe_name)
    recipe.convert('oz')
    if not recipe:
        flash('Error: unknown recipe "{}"'.format(recipe_name), 'danger')
        return render_template('result.html', heading=heading)
    else:
        recipe_html = recipe_as_html(recipe,
                DisplayOptions(prices=True, stats=False, examples=True, all_ingredients=False,
                    markup=mms.default_margin, prep_line=True, origin=True, info=True, variants=True))

    if not recipe.can_make:
        flash('Ingredients to make this are out of stock :(', 'warning')
        return render_template('order.html', form=form, recipe=recipe_html, show_form=False)

    if request.method == 'GET':
        show_form = True
        if current_user.is_authenticated:
            heading = "Order for {}:".format(current_user.get_name())

    if request.method == 'POST':
        if 'submit-order' in request.form:
            if form.validate():
                if current_user.is_authenticated:
                    user_name = current_user.get_name()
                    user_email = current_user.email
                else:
                    user_name = form.name.data
                    user_email = form.email.data

                # TODO use simpler html for recording an order
                # add to the order database
                order = Order(bar_id=mms.current_bar, timestamp=datetime.datetime.utcnow(), recipe_name=recipe.name, recipe_html=recipe_html)
                if current_user.is_authenticated:
                    order.user_id = current_user.id
                db.session.add(order)
                db.session.commit()

                # TODO add a verifiable token to this
                subject = "[Mix-Mind] New {} Order - {}".format(app.config.get('BAR_NAME'), recipe.name)
                confirmation_link = "https://{}{}".format(request.host,
                        url_for('confirm_order',
                            email=urllib.quote(user_email),
                            order_id=order.id))

                # TODO use bar config for bartender on duty
                send_mail(subject, app.config['BARTENDER_EMAIL'], "order_submitted",
                        confirmation_link=confirmation_link,
                        name=user_name,
                        notes=form.notes.data,
                        recipe_html=recipe_html)

                flash("Successfully placed order!", 'success')
                if not current_user.is_authenticated:
                    if User.query.filter_by(email=user_email).one_or_none():
                        flash("Hey, if you log in you won't have to keep typing your email address for orders ;)", 'secondary')
                        return redirect(url_for('security.login'))
                    else:
                        flash("Hey, if you register I'll remember your name and email in future orders!", 'secondary')
                        return redirect(url_for('security.register'))
                return render_template('result.html', heading="Order Placed")
            else:
                flash("Error in form validation", 'danger')

    # either provide the recipe and the form,
    # or after the post show the result
    return render_template('order.html', form=form, recipe=recipe_html, heading=heading, show_form=show_form)

@app.route('/confirm_order')
def confirm_order():
    # TODO this needs a security token
    email = urllib.unquote(request.args.get('email'))
    order_id = request.args.get('order_id')
    venmo_link = app.config.get('VENMO_LINK')
    order = Order.query.filter_by(id=order_id).one_or_none()
    if not order:
        flash("Error: Invalid order_id", 'danger')
        return render_template("result.html", heading="Invalid confirmation link")
    if order.confirmed:
        flash("Error: Order has already been confirmed", 'danger')
        return render_template("result.html", heading="Invalid confirmation link")

    order.confirmed = True

    # update users db
    user = User.query.filter_by(email=email).one_or_none()
    if user:
        greeting = "{}, you".format(user.name(short=True))
        if order.user_id and order.user_id != user.id:
            raise ValueError("Order was created with different id than confirming user!")
        user.orders.append(order)
        user_datastore.put(user)
        user_datastore.commit()
    else:
        greeting = "You"

    try:
        subject = "[Mix-Mind] Your {} Confirmation".format(app.config.get('BAR_NAME'))
        send_mail(subject, email, "order_confirmation",
                greeting=greeting,
                recipe_name=order.recipe_name,
                recipe_html=order.recipe_html,
                venmo_link=venmo_link)
    except Exception:
        log.error("Error sending confirmation email for {} to {}".format(recipe, email))

    flash('Confirmation sent')
    return render_template('result.html', heading="Order Confirmation")


@app.route('/user')
@login_required
def user_profile():
    try:
        user_id = int(request.args.get('user_id'))
    except ValueError:
        flash("Invalid user_id parameter", 'danger')
        return render_template('result.html', "User profile unavailable")

    if current_user.id != user_id and not current_user.has_role('admin'):
        return _get_unauthorized_view()

    if current_user.email in app.config.get('MAKE_ADMIN', []):
        if not current_user.has_role('admin'):
            admin = user_datastore.find_role('admin')
            user_datastore.add_role_to_user(current_user, admin)
            user_datastore.commit()
            flash("You have been upgraded to admin", 'success')

    return render_template('user_profile.html')


@app.route("/user_post_login", methods=['GET'])
def post_login_redirect():
    # show main if admin user
    # maybe use post-register for assigning a role
    if 'admin' in current_user.roles:
        return redirect(url_for('browse'))
    else:
        return redirect(url_for('browse'))


@app.route('/user_post_confirm_email')
@login_required
def user_confirmation_hook():
    if not current_user.has_role('customer'):
        customer = user_datastore.find_role('customer')
        user_datastore.add_role_to_user(current_user, customer)
        user_datastore.commit()
    return render_template('result.html', heading="Email confirmed")


################################################################################
# Admin routes
################################################################################

@app.route("/admin/dashboard", methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def admin_dashboard():
    global mms
    bar = Bar.query.filter_by(id=mms.current_bar).one()
    users = User.query.all()
    orders = Order.query.all()
    user_table = users_as_table(users)
    order_table = orders_as_table(orders)
    return render_template('dashboard.html', users=users, orders=orders, bar=bar,
            user_table=user_table, order_table=order_table)


@app.route("/admin/menu_generator", methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def menu_generator():
    form = get_form(DrinksForm)
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
            flash("Error in form validation", 'danger')

    return render_template('menu_generator.html', form=form, recipes=recipes, excluded=excluded, stats=stats)


@app.route("/admin/menu_generator/download/", methods=['POST'])
@login_required
@roles_required('admin')
def menu_download():
    form = get_form(DrinksForm)

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
        flash("Error in form validation", 'danger')
        return render_template('application_main.html', form=form, recipes=[], excluded=None)


@app.route("/admin/recipes", methods=['GET','POST'])
@login_required
@roles_required('admin')
def recipe_library():
    global mms
    select_form = get_form(RecipeListSelector)
    print select_form.errors
    add_form = get_form(RecipeForm)
    print add_form.errors

    if request.method == 'POST':
        print request
        if 'recipe-list-select' in request.form:
            recipes = select_form.recipes.data
            mms = MixMindServer(recipes=recipes, barstock_files=mms.barstock_files)
            flash("Now using recipes from {}".format(recipes))

    return render_template('recipes.html', select_form=select_form, add_form=add_form)


@app.route("/admin/ingredients", methods=['GET','POST'])
@login_required
@roles_required('admin')
def ingredient_stock():
    global mms
    form = get_form(BarstockForm)
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
                flash("Error: \"{}\" not found; must match as shown below exactly".format(bottle), 'danger')

        elif 'upload-csv' in request.form:
            filename = datafiles.save(secure_filename(request.files['upload_csv']))
            print "CSV uploaded to {}".format(filename)
            mms = MixMindServer(recipes=mms.recipe_files, barstock_files=[filename])
            flash("Ingredients database reloaded from {}".format(filename))

    table = mms.get_ingredients_table()
    return render_template('ingredients.html', form=form, table=table)

@app.route("/admin/debug", methods=['GET'])
@login_required
@roles_required('admin')
def admin_database_debug():
    if app.config.get('DEBUG', False):
        import ipdb; ipdb.set_trace();
        return render_template('result.html', heading="Finished debug session...")
    else:
        return render_template('result.html', heading="Debug unavailable")



################################################################################
# Helper routes
################################################################################

@app.route('/json/<recipe_name>')
def recipe_json(recipe_name):
    recipe_name = urllib.unquote_plus(recipe_name)
    try:
        return jsonify(mms.base_recipes[recipe_name])
    except KeyError:
        return "{} not found".format(recipe_name)


@app.errorhandler(500)
def handle_internal_server_error(e):
    flash(e, 'danger')
    return render_template('result.html', heading="OOPS - Something went wrong..."), 500
