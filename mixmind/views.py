"""
Application main for the mixmind app
"""
import os
import random
import datetime
import tempfile
import urllib.request, urllib.parse, urllib.error
import codecs

import pendulum
from functools import wraps

from flask import g, render_template, flash, request, send_file, jsonify, redirect, url_for, after_this_request
from flask_security import login_required, roles_required, roles_accepted
from flask_security.decorators import _get_unauthorized_view
from flask_login import current_user

from .notifier import send_mail
from .forms import DrinksForm, OrderForm, OrderFormAnon, RecipeForm, RecipeListSelector, BarstockForm, UploadBarstockForm, LoginForm, CreateBarForm, EditBarForm, EditUserForm, SetBarOwnerForm
from .authorization import user_datastore
from .barstock import Barstock_SQL, Ingredient, _update_computed_fields
from .formatted_menu import filename_from_options, generate_recipes_pdf
from .compose_html import recipe_as_html, users_as_table, orders_as_table, bars_as_table
from .util import filter_recipes, DisplayOptions, FilterOptions, PdfOptions, load_recipe_json, report_stats, convert_units
from .database import db
from .models import User, Order, Bar
from . import log, app, mms, current_bar

"""
BUGS:
NOTES:
* admin pages
    - raise 404 on not authorized
    - add/remove recipes as raw json
        - ace embeddable text editor
    - menu_generator
* better commits to db with after_this_request
* menu schemas
    - would be able to include definitive item lists for serving, ice, tag, etc.
* hardening
    - get logging working for reals
    - test error handling
"""
@app.before_request
def initialize_shared_data():
    g.bar_id = current_bar.id

def get_form(form_class):
    """WTForms update 2.2 breaks when an empty request.form
    is given to it """
    if not request.form:
        return form_class()
    return form_class(request.form)

def bundle_options(tuple_class, args):
    return tuple_class(*(getattr(args, field).data for field in tuple_class._fields))

def recipes_from_options(form, display_opts=None, filter_opts=None, to_html=False, order_link=False, convert_to=None, **kwargs_for_html):
    """ Apply display formmatting, filtering, sorting to
    the currently loaded recipes.
    Also can generate stats
    May convert to html, including extra options for that
    Apply sorting
    """
    display_options = bundle_options(DisplayOptions, form) if not display_opts else display_opts
    filter_options = bundle_options(FilterOptions, form) if not filter_opts else filter_opts
    recipes, excluded = filter_recipes(mms.processed_recipes(current_bar), filter_options, union_results=bool(filter_options.search))
    if form.sorting.data and form.sorting.data != 'None': # TODO this is weird
        reverse = 'X' in form.sorting.data
        attr = 'avg_{}'.format(form.sorting.data.rstrip('X'))
        recipes = sorted(recipes, key=lambda r: getattr(r.stats, attr), reverse=reverse)
    if convert_to:
        [r.convert(convert_to) for r in recipes]
    if display_options.stats and recipes:
        stats = report_stats(recipes, as_html=True)
    else:
        stats = None
    # TODO this can certainly be cached
    if to_html:
        if order_link:
            recipes = [recipe_as_html(recipe, display_options,
                order_link="/order/{}".format(urllib.parse.quote_plus(recipe.name)),
                **kwargs_for_html) for recipe in recipes]
        else:
            recipes = [recipe_as_html(recipe, display_options, **kwargs_for_html) for recipe in recipes]
    return recipes, excluded, stats

def get_tmp_file():
    """ Get a temporary file that will be removed by a callback after
    the current request
    :returns: file name as a string
    """
    _, tmp_filename = tempfile.mkstemp()

    @after_this_request
    def rm_tempfile(response):
        try:
            os.remove(tmp_filename)
        except OSError as e:
            log.warning("OSError: Failed to rm tmp file {}: {}".format(tmp_filename, e))
        return response
    return tmp_filename

################################################################################
# Customer routes
################################################################################


@app.route("/", methods=['GET', 'POST'])
def browse():
    form = get_form(DrinksForm)
    filter_options = None

    if request.method == 'GET':
        # filter for current recipes that can be made on the core list
        filter_options = FilterOptions(search="",all_=False,include="",exclude="",include_use_or=False,exclude_use_or=False,style="",glass="",prep="",ice="",name="",tag="core")

    display_opts = DisplayOptions(
                        prices=current_bar.prices,
                        stats=False,
                        examples=current_bar.examples,
                        all_ingredients=False,
                        markup=current_bar.markup,
                        prep_line=current_bar.prep_line,
                        origin=current_bar.origin,
                        info=current_bar.info,
                        variants=current_bar.variants)
    recipes, _, _ = recipes_from_options(form, display_opts=display_opts, filter_opts=filter_options,
                            to_html=True, order_link=True, convert_to=current_bar.convert, condense_ingredients=current_bar.summarize)

    if request.method == 'POST':
        if form.validate():
            n_results = len(recipes)
            if n_results > 0:
                if 'surprise-menu' in request.form:
                    recipes = [random.choice(recipes)]
                    flash("Bartender's choice! Just try again if you want something else!")
                else:
                    flash("Filters applied. Showing {} available recipes".format(n_results), 'success')
            else:
                flash("No results after filtering, try being less specific", 'warning')
        else:
            flash("Error in form validation", 'danger')

    return render_template('browse.html', form=form, recipes=recipes)

@app.route("/order/<recipe_name>", methods=['GET', 'POST'])
def order(recipe_name):
    if current_user.is_authenticated:
        form = get_form(OrderForm)
    else:
        form = get_form(OrderFormAnon)

    recipe_name = urllib.parse.unquote_plus(recipe_name)
    show_form = False
    heading = "Order:"

    recipe = mms.find_recipe(current_bar, recipe_name)
    recipe.convert('oz')
    if not recipe:
        flash('Error: unknown recipe "{}"'.format(recipe_name), 'danger')
        return render_template('result.html', heading=heading)
    else:
        recipe_html = recipe_as_html(recipe, DisplayOptions(
                            prices=current_bar.prices,
                            stats=False,
                            examples=True,
                            all_ingredients=False,
                            markup=current_bar.markup,
                            prep_line=True,
                            origin=current_bar.origin,
                            info=True,
                            variants=True), convert_to=current_bar.convert)

    if not recipe.can_make:
        flash('Ingredients to make this are out of stock :(', 'warning')
        return render_template('order.html', form=form, recipe=recipe_html, show_form=False)

    if request.method == 'GET':
        show_form = True
        if current_user.is_authenticated:
            heading = "Order for {}:".format(current_user.get_name(short=True))
        if current_bar.is_closed:
            flash("It's closed. So sad.", 'warning')

    if request.method == 'POST':
        if 'submit-order' in request.form:
            if form.validate():
                if current_user.is_authenticated:
                    user_name = current_user.get_name()
                    user_email = current_user.email
                else:
                    user_name = form.name.data
                    user_email = form.email.data

                if current_bar.is_closed:
                    flash('The bar has been closed for orders.', 'warning')
                    return redirect(request.url)

                # use simpler html for recording an order
                email_recipe_html = recipe_as_html(recipe, DisplayOptions(
                                    prices=current_bar.prices,
                                    stats=False,
                                    examples=True,
                                    all_ingredients=False,
                                    markup=current_bar.markup,
                                    prep_line=True,
                                    origin=current_bar.origin,
                                    info=True,
                                    variants=True), fancy=False, convert_to=current_bar.convert)

                # add to the order database
                order = Order(bar_id=current_bar.id, bartender_id=current_bar.bartender.id,
                        timestamp=datetime.datetime.utcnow(), user_email=user_email,
                        recipe_name=recipe.name, recipe_html=email_recipe_html)
                if current_user.is_authenticated:
                    order.user_id = current_user.id
                db.session.add(order)
                db.session.commit()

                subject = "{} for {} at {}".format(recipe.name, user_name, current_bar.name)
                confirmation_link = "https://{}{}".format(request.host,
                        url_for('confirm_order',
                            order_id=order.id))
                send_mail(subject, current_bar.bartender.email, "order_submitted",
                        confirmation_link=confirmation_link,
                        name=user_name,
                        notes=form.notes.data,
                        recipe_html=email_recipe_html)

                flash("Your order has been submitted, and you'll receive a confirmation email once the bartender acknowledges it", 'success')
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
    order_id = request.args.get('order_id')
    order = Order.query.filter_by(id=order_id).one_or_none()
    if not order:
        flash("Error: Invalid order_id", 'danger')
        return render_template("result.html", heading="Invalid confirmation link")
    if order.confirmed:
        flash("Error: Order has already been confirmed", 'danger')
        return render_template("result.html", heading="Invalid confirmation link")

    bartender = user_datastore.find_user(id=order.bartender_id)
    if bartender and bartender.venmo_id:
        venmo_link = app.config.get('VENMO_LINK','').format(bartender.venmo_id)
    else:
        venmo_link = None

    order.confirmed = datetime.datetime.utcnow()

    # update users db
    user = User.query.filter_by(email=order.user_email).one_or_none()
    if user:
        greeting = "{}, you".format(user.get_name(short=True))
        if order.user_id and order.user_id != user.id:
            flash("Order was created with different id than confirming user!", 'danger')
            return render_template('result.html', heading="Invalid request")
        user.orders.append(order)
        user_datastore.put(user)
        user_datastore.commit()
    else:
        greeting = "You"

    bar = Bar.query.filter_by(id=order.bar_id).one_or_none()
    if bar is None:
        flash("Invalid bar id with order", 'danger')
        return render_template('result.html', heading="Invalid request")
    subject = "[Mix-Mind] Your {} Confirmation".format(current_bar.name)
    sent = send_mail(subject, order.user_email, "order_confirmation",
            greeting=greeting,
            recipe_name=order.recipe_name,
            recipe_html=order.recipe_html,
            venmo_link=venmo_link)
    if sent:
        flash('Confirmation sent')
    else:
        flash('Confimration email failed', 'danger')
    return render_template('result.html', heading="{} for {}".format(order.recipe_name, user.get_name(short=True) if user else order.user_email),
            body=order.recipe_html)


@app.route('/user', methods=['GET', 'POST'])
@login_required
def user_profile():
    try:
        user_id = int(request.args.get('user_id'))
    except ValueError:
        flash("Invalid user_id parameter", 'danger')
        return render_template('result.html', heading="User profile unavailable")

    if current_user.id != user_id and not current_user.has_role('admin'):
        return _get_unauthorized_view()

    # leaving this trigger here because it's convenient
    if current_user.email in app.config.get('MAKE_ADMIN', []):
        if not current_user.has_role('admin'):
            admin = user_datastore.find_role('admin')
            user_datastore.add_role_to_user(current_user, admin)
            user_datastore.commit()
            flash("You have been upgraded to admin", 'success')

    this_user = user_datastore.find_user(id=user_id)
    if not this_user:
        flash("Unknown user_id", 'danger')
        return render_template('result.html', heading="User profile unavailable")

    form = get_form(EditUserForm)
    if request.method == 'POST':
        if form.validate():
            this_user.first_name = form.first_name.data
            this_user.last_name = form.last_name.data
            this_user.nickname = form.nickname.data
            this_user.venmo_id = form.venmo_id.data
            user_datastore.commit()
            flash("Profile updated", 'success')
            return redirect(request.url)
        else:
            flash("Error in form validation", 'danger')
            return render_template('user_profile.html', this_user=this_user, edit_user=form,
                    human_timestamp=mms.time_human_formatter, human_timediff=mms.time_diff_formatter,
                    timestamp=mms.timestamp_formatter)



    # TODO make admins able to edit user page
    # pre-populate the form with the current values
    for attr in 'first_name,last_name,nickname,venmo_id'.split(','):
        setattr(getattr(form, attr), 'data', getattr(this_user, attr))

    return render_template('user_profile.html', this_user=this_user, edit_user=form,
                human_timestamp=mms.time_human_formatter, human_timediff=mms.time_diff_formatter,
                timestamp=mms.timestamp_formatter)


@app.route("/user_post_login", methods=['GET'])
@login_required
def post_login_redirect():
    # assign any orders with this user's email to the actual user ID
    # these could be from before they registered or ordered while logged out
    orders = Order.query.filter_by(user_email=current_user.email).all()
    for order in orders:
        if not order.user_id:
            order.user_id = current_user.id
            print("Attributing order {} to user {}".format(order.id, current_user.id))
    db.session.commit()
    return redirect(url_for('browse'))


@app.route('/user_post_confirm_email')
@login_required
def user_confirmation_hook():
    if not current_user.has_role('customer'):
        customer = user_datastore.find_role('customer')
        user_datastore.add_role_to_user(current_user, customer)
        user_datastore.commit()
    return redirect(url_for('post_login_redirect'))

################################################################################
# Owner routes
################################################################################
def check_ownership(f):
    """ Ensure current_user owns this bar, or is admin
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.has_role('admin') and current_user != current_bar.owner:
            flash("You do not have permission to view this resource. This could have been an attempt to switch to a different bar when editing a bar of which you had control.", 'danger')
            return render_template('result.html', heading="Not Authorized")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/manage/bar", methods=['GET', 'POST'])
@login_required
@roles_accepted('admin', 'owner')
@check_ownership
def bar_settings():
    BAR_BULK_ATTRS = 'name,tagline,is_public,prices,prep_line,examples,convert,markup,info,origin,variants,summarize'.split(',')
    edit_bar_form = get_form(EditBarForm)
    if request.method == 'POST':
        # TODO invalid to have open without a bartender (js?)
        if edit_bar_form.validate():
            bar_id = current_bar.id
            bar = Bar.query.filter_by(id=bar_id).one_or_none()
            if bar is None:
                flash("Invalid bar_id: {}".format(bar_id), 'danger')
                return redirect(request.url)

            # unassign previous bartender
            if bar.bartender_on_duty:
                old_bartender = user_datastore.find_user(id=bar.bartender_on_duty)
                send_mail("[Mix-Mind] Bartender Duty Unassigned", old_bartender.email, 'simple',
                        heading="No longer bartending at {}".format(bar.name),
                        message="You have been unassigned as the bartender-on-duty at {}.".format(bar.name))
            # add bartender on duty
            user = user_datastore.find_user(email=edit_bar_form.bartender.data)
            if user and user.id != bar.bartender_on_duty:
                bartender = user_datastore.find_role('bartender')
                user_datastore.add_role_to_user(user, bartender)
                bar.bartenders.append(user)
                bar.bartender_on_duty = user.id
                send_mail("[Mix-Mind] Bartender Duty Assigned", user.email, 'simple',
                        heading="Bartending at {}".format(bar.name),
                        message="You have been assigned as the bartender-on-duty at {}.".format(bar.name))
            else:
                # closed/no bartender is same result
                if not user or edit_bar_form.status.data == False:
                    bar.bartender_on_duty = None

            for attr in BAR_BULK_ATTRS:
                setattr(bar, attr, getattr(edit_bar_form, attr).data)
            db.session.commit()
            flash("Successfully updated config for {}".format(bar.cname))
            return redirect(request.url)
        else:
            flash("Error in form validation", 'warning')

    # for GET requests, fill in the edit bar form
    edit_bar_form.status.data = not current_bar.is_closed
    edit_bar_form.bartender.data = '' if current_bar.is_closed else current_bar.bartender.email
    for attr in BAR_BULK_ATTRS:
        setattr(getattr(edit_bar_form, attr), 'data', getattr(current_bar, attr))
    if edit_bar_form is None:
        return redirect(request.url)
    orders = Order.query.filter_by(bar_id=current_bar.id)
    order_table = orders_as_table(orders)
    return render_template('bar_settings.html', edit_bar_form=edit_bar_form, order_table=order_table)

@app.route("/manage/ingredients", methods=['GET','POST'])
@login_required
@roles_accepted('admin', 'owner')
@check_ownership
def ingredient_stock():
    form = get_form(BarstockForm)
    upload_form = get_form(UploadBarstockForm)
    form_open = False
    print(form.errors)

    if request.method == 'POST':
        print(request)
        if 'add-ingredient' in request.form:
            if form.validate():
                row = {}
                row['Category'] = form.category.data
                row['Type'] = form.type_.data
                row['Kind'] = form.kind.data
                row['ABV'] = float(form.abv.data)
                row['Size (mL)'] = convert_units(float(form.size.data), form.unit.data, 'mL')
                row['Price Paid'] = float(form.price.data)
                try:
                    ingredient = Barstock_SQL(current_bar.id).add_row(row, current_bar.id)
                except DataError as e:
                    flash('Error: {}'.format(e), 'danger')
                else:
                    mms.regenerate_recipes(current_bar, ingredient=ingredient.type_)
                return redirect(request.url)
            else:
                form_open = True
                flash("Error in form validation", 'danger')

        elif 'upload-csv' in request.form:
            # TODO handle files < 500 kb by keeping in mem
            csv_file = request.files['upload_csv']
            if not csv_file or csv_file.filename == '':
                flash('No selected file', 'danger')
                return redirect(request.url)

            tmp_filename = get_tmp_file()
            csv_file.save(tmp_filename)
            Barstock_SQL(current_bar.id).load_from_csv([tmp_filename], current_bar.id,
                    replace_existing=upload_form.replace_existing.data)
            mms.generate_recipes(current_bar)
            msg = "Ingredients database {} {} for {}".format(
                    "replaced by" if upload_form.replace_existing.data else "added to from",
                    csv_file.filename, current_bar.cname)
            log.info(msg)
            flash(msg, 'success')

    return render_template('ingredients.html', form=form, upload_form=upload_form, form_open=form_open)


################################################################################
# Admin routes
################################################################################

@app.route("/admin/set_bar_owner", methods=['POST'])
@login_required
@roles_required('admin')
def set_bar_owner():
    set_owner_form = get_form(SetBarOwnerForm)

    if set_owner_form.validate():
        bar_id = current_bar.id
        bar = Bar.query.filter_by(id=bar_id).one_or_none()
        if bar is None:
            flash("Invalid bar_id: {}".format(bar_id), 'danger')
            return None

        # assign owner
        user = user_datastore.find_user(email=set_owner_form.owner.data)
        owner = user_datastore.find_role('owner')
        old_owner = bar.owner
        if user and user != bar.owner:
            user_datastore.add_role_to_user(user, owner)
            bar.owner = user
            send_mail("[Mix-Mind] Bar Ownership Granted", user.email, 'simple',
                    heading="{}, you now own {}".format(user.get_name(), bar.name),
                    message="You have been assigned as the owner of {}</p><p>The bar can now be managed from the site. Switch to your bar, and then navigate to the management settings.".format(bar.name))
            flash("{} is now the proud owner of {}".format(user.get_name(), bar.cname))
        elif set_owner_form.owner.data == '' and bar.owner:
            # remove the owner from this bar
            flash("{} is no longer the owner of {}".format(bar.owner.get_name(), bar.cname))
            bar.owner = None
            # remove "owner" role if user does not own any more bars
            if not old_owner.owns:
                user_datastore.remove_role_from_user(old_owner, owner)
        if old_owner:
            send_mail("[Mix-Mind] Bar Ownership Revoked", old_owner.email, 'simple',
                    heading="{}, you no longer own {}".format(old_owner.get_name(), bar.name),
                    message="You have been unassigned as the owner of {}.".format(bar.name))
        user_datastore.commit()
    else:
        flash("Error in form validation", 'warning')

    return redirect(url_for('admin_dashboard'))

@app.route("/admin/dashboard", methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def admin_dashboard():
    new_bar_form = get_form(CreateBarForm)
    set_owner_form = get_form(SetBarOwnerForm)
    if request.method == 'POST':
        if 'create_bar' in request.form:
            if new_bar_form.validate():
                if Bar.query.filter_by(cname=new_bar_form.cname.data).one_or_none():
                    flash("Bar name already in use", 'warning')
                    return None
                bar_args = {'cname': new_bar_form.cname.data}
                if new_bar_form.name.data == "":
                    bar_args['name'] = bar_args['cname']
                else:
                    bar_args['name'] = new_bar_form.name.data
                if new_bar_form.tagline.data:
                    bar_args['tagline'] = new_bar_form.tagline.data
                new_bar = Bar(**bar_args)
                db.session.add(new_bar)
                db.session.commit()
                flash("Created a new bar", 'success')
            else:
                flash("Error in form validation", 'warning')

        if 'set-default-bar' in request.form:
            bar_id = request.form.get('bar_id', None, int)
            to_activate_bar = Bar.query.filter_by(id=bar_id).one_or_none()
            if to_activate_bar.is_default:
                flash("Bar ID: {} is already the default".format(bar_id), 'warning')
                return redirect(request.url)
            if not to_activate_bar:
                flash("Error: Bar ID: {} is invalid".format(bar_id), 'danger')
                return redirect(request.url)
            bars = Bar.query.all()
            for bar in bars:
                bar.is_default = (bar.id == bar_id)
            db.session.commit()
            flash("Bar ID: {} is now the default".format(bar_id), 'success')
            return redirect(request.url)

    set_owner_form.owner.data = '' if not current_bar.owner else current_bar.owner.email
    bars = Bar.query.all()
    users = User.query.all()
    orders = Order.query.all()
    #bar_table = bars_as_table(bars)
    user_table = users_as_table(users)
    order_table = orders_as_table(orders)
    return render_template('dashboard.html', new_bar_form=new_bar_form,
            set_owner_form=set_owner_form, users=users, orders=orders,
            bars=bars, user_table=user_table, order_table=order_table)

@app.route("/admin/menu_generator", methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def menu_generator():
    return render_template('result.html', heading="Still under construction...")
    form = get_form(DrinksForm)
    print(form.errors)
    recipes = []
    excluded = None
    stats = None

    if request.method == 'POST':
        if form.validate():
            print(request)
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
    raise NotImplementedError

    if form.validate():
        print(request)
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
    return render_template('result.html', heading="Still under construction...")
    select_form = get_form(RecipeListSelector)
    print(select_form.errors)
    add_form = get_form(RecipeForm)
    print(add_form.errors)

    if request.method == 'POST':
        print(request)
        if 'recipe-list-select' in request.form:
            recipes = select_form.recipes.data
            mms.regenerate_recipes(current_bar)
            flash("Now using recipes from {}".format(recipes))

    return render_template('recipes.html', select_form=select_form, add_form=add_form)



################################################################################
# API routes
################################################################################
# All of these routes are designed to be used against ajax calls
# Each route will return a json object with the following parameters:
#  status:  "success" - successful go ahead and use the data
#           "error"   - something went wrong
#  message: "..."     - error message
#  data:    {...}     - the expected data returned to caller
def api_error(message, **kwargs):
    return jsonify(status="error", message=message, **kwargs)
def api_success(data, message="", **kwargs):
    return jsonify(status="success", message=message, data=data, **kwargs)

@app.route("/api/ingredients", methods=['GET'])
@login_required
@roles_accepted('admin', 'owner')
@check_ownership
def api_ingredients():
    ingredients = Ingredient.query.filter_by(bar_id=current_bar.id).order_by(Ingredient.Category, Ingredient.Type).all()
    ingredients = [i.as_dict() for i in ingredients]
    return api_success(ingredients)

@app.route("/api/ingredient", methods=['POST', 'GET', 'PUT', 'DELETE'])
@login_required
@roles_accepted('admin', 'owner')
@check_ownership
def api_ingredient():
    """CRUD endpoint for individual ingredients

    Indentifying parameters:
    :param string iid: iid of the changed row's ingredient

    Create params:
    :param string Category: Category idenfitier
    :param string Kind: kind for ingredient
    :param string Type: type for ingredient
    :param float ABV: ABV value
    :param float Size: Size
    :param string Unit: one of util.VALID_UNITS
    :param float Price: price of the ingredint

    Read:

    Update:
    :param string field: the value being modified
    :param string value: the new value (type coerced from field)

    Delete:

    """
    # check parameters
    iid = request.form.get('iid')
    if iid is None and request.method in ['PUT', 'DELETE']:
        return api_error("iid is a required parameter for {}".fromat(request.method))
    ingredient = Ingredient.query_by_iid(iid)
    if not ingredient and not request.method == 'POST':
        return api_error("Ingredient not found")
    if ingredient.bar_id != current_bar.id:
        return api_error("Request iid {} includes wrong bar_id".format(iid))

    # create
    if request.method == 'POST':
        if ingredient:
            return api_error("Ingredient '{}' already exists, try editing it instead".format(ingredient))
        return api_error("Not implemented")
    # read
    elif request.method == 'GET':
        return api_success(ingredient.as_dict(), messaage="Ingredient: {}".format(ingredient))
    # update
    elif request.method == 'PUT':
        field = request.form.get('field')
        if not field:
            return api_error("'field' is a required parameter")
        elif field not in "Category,Type,Kind,In_Stock,ABV,Size_mL,Size_oz,Price_Paid".split(','):
            return api_error("'{}' is not allowed to be edited via the API".format(field))
        value = request.form.get('value')
        if not value:
            return api_error("'value' is a required parameter")

        # TODO value constraints
        try:
            # the toggle switches return 'on'/'off'
            # but that is their current state, so toggle value here
            if field == 'In_Stock':
                value = {'on': False, 'off': True}[value]
            else:
                value = type(ingredient[field])(value)
        except AttributeError:
            return api_error("Invalid field '{}' for an Ingredient".format(field))
        except ValueError as e:
            return api_error(str(e))

        # special handling
        if field == 'Size_oz':
            # convert to mL because that's how everything works
            ingredient['Size_mL'] = convert_units(value, 'oz', 'mL')
        else:
            ingredient[field] = value
        if field in ['Size_mL', 'Size_oz', 'Price_Paid', 'Type']:
            _update_computed_fields(ingredient)
        try:
            db.session.commit()
        except Exception as e:
            return api_error("{}: {}".format(e.__class__.__name__, e))

        data = ingredient.as_dict()
        mms.regenerate_recipes(current_bar, ingredient=ingredient.type_)
        return api_success(data, message='Successfully updated "{}" for "{}"'.format(field, ingredient.iid()))

    # delete
    elif request.method == 'DELETE':
        db.session.delete(ingredient)
        db.session.commit()
        mms.regenerate_recipes(current_bar, ingredient=ingredient.type_)
        return api_success({'iid': ingredient.iid()}, message='Successfully deleted "{}"'.format(ingredient.iid()))

    return api_error("Unknwon method")

@app.route("/api/ingredients/download", methods=['GET'])
@login_required
@roles_accepted('admin', 'owner')
@check_ownership
def api_ingredients_download():
    ingredients = Ingredient.query.filter_by(bar_id=current_bar.id).order_by(Ingredient.Category, Ingredient.Type).all()
    ingredients = [Ingredient.csv_heading()] + [i.as_csv() for i in ingredients]
    filename = "{}_ingredients_{}.csv".format(current_bar.cname.replace(' ','_'), pendulum.now().int_timestamp)
    tmp_filename = get_tmp_file()
    with open(tmp_filename, 'w') as fp:
        fp.write(codecs.BOM_UTF8)
        fp.writelines((i.encode('utf-8') for i in ingredients))
    return send_file(tmp_filename, 'text/csv', as_attachment=True, attachment_filename=filename)

@app.route("/api/user_current_bar", methods=['POST', 'GET', 'PUT', 'DELETE'])
@login_required
def api_user_current_bar():
    """Request endpoint to change a user's current bar
    :param int user_id: ID of the user to modity
    :param int bar_id: ID of the bar to set as user's current view default
        If 0, will use the configured default bar
    :param string next: Should be the URL of the current page so the user
        can be redirected to that page
    """
    try:
        user_id = int(request.args.get('user_id'))
    except ValueError:
        flash("Invalid user_id parameter", 'danger')
        return render_template('result.html', heading="User profile unavailable")
    try:
        bar_id = int(request.args.get('bar_id'))
    except ValueError:
        flash("Invalid bar_id parameter", 'danger')
        return render_template('result.html', heading="Bar unavailable")
    next_url = request.args.get('next', url_for('browse'))

    user = user_datastore.find_user(id=user_id)
    if user:
        if user != current_user and not current_user.has_role('admin'):
            flash("Cannot change default bar for another user {}".format(user_id), 'danger')
            return render_template('result.html', heading="Invalid default bar request")
        bar = Bar.query.filter_by(id=bar_id).one_or_none()
        if not bar:
            flash("Invalid bar id: {}".format(bar_id))
            return render_template('result.html', heading="Invalid bar")
        if not bar.is_public and (user.id != bar.owner_id) and not user.has_role('admin'):
            flash("Bar {} is not publicly available, you need to be the owner or admin".format(bar_id), 'danger')
            return render_template('result.html', heading="Invalid bar")
        user.current_bar_id = bar.id
        user_datastore.commit()
    else:
        flash("Invalid user {}".format(user_id), 'danger')
        return render_template('result.html', heading="Invalid user")

    return redirect(next_url)


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

@app.route('/api/json/<recipe_name>')
def recipe_json(recipe_name):
    recipe_name = urllib.parse.unquote_plus(recipe_name)
    try:
        return jsonify(mms.base_recipes[recipe_name])
    except KeyError:
        return "{} not found".format(recipe_name)


@app.errorhandler(500)
def handle_internal_server_error(e):
    flash(e, 'danger')
    return render_template('error.html')#, 500


@app.route("/api/test")
def api_test():
    a = request.args.get('a', 0, type=int)
    b = request.args.get('b', 0, type=int)
    return jsonify(result=a + b)

