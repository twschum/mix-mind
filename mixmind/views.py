"""
Application main for the mixmind app
"""
import os
import random
import datetime
import tempfile
import urllib

from flask import g, render_template, flash, request, send_file, jsonify, redirect, url_for
from flask_security import login_required, roles_required
from flask_security.decorators import _get_unauthorized_view
from flask_login import current_user

from .notifier import send_mail
from .forms import DrinksForm, OrderForm, OrderFormAnon, RecipeForm, RecipeListSelector, BarstockForm, UploadBarstockForm, LoginForm, CreateBarForm, EditBarForm, EditUserForm
from .authorization import user_datastore
from .barstock import Barstock_SQL, Ingredient
from .formatted_menu import filename_from_options, generate_recipes_pdf
from .compose_html import recipe_as_html, users_as_table, orders_as_table, bars_as_table, ingredients_as_table
from .util import filter_recipes, DisplayOptions, FilterOptions, PdfOptions, load_recipe_json, report_stats, find_recipe
from .database import db
from .models import User, Order, Bar
from . import log, app, mms, current_bar

"""
BUGS:
* email sent to customer not bartender
NOTES:
* cards should be same sizes
* template improvements
    - make email template
        - use custom html template params (price fails in email)
        - change email confirmation to result page
        - order submission had wrong name
    - use more bootstrap form goodness
        - need file upload
        - TOGGLES!
* admin pages
    - add/remove ingredients dynamically?
    - add/remove recipes as raw json?
    - menu_generator (what's now "mainpage")
* better commits to db with after_this_request
* menu schemas
    - would be able to include definitive item lists for serving, ice, tag, etc.
* hardening
    - moar logging
    - test error handling
* configuration management
    - support for multiple bars!
    - defaults plus management
    - support for modifying the "bartender on duty" aka Notifier's secret info
    - disable the order button unless we are "open"
* "remember" form open/close position of collapses
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
                            to_html=True, order_link=True, condense_ingredients=current_bar.summarize)

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
        recipe_html = recipe_as_html(recipe, DisplayOptions(
                            prices=current_bar.prices,
                            stats=False,
                            examples=True,
                            all_ingredients=False,
                            markup=current_bar.markup,
                            prep_line=True,
                            origin=current_bar.origin,
                            info=True,
                            variants=True))

    if not recipe.can_make:
        flash('Ingredients to make this are out of stock :(', 'warning')
        return render_template('order.html', form=form, recipe=recipe_html, show_form=False)

    if request.method == 'GET':
        show_form = True
        if current_user.is_authenticated:
            heading = "Order for {}:".format(current_user.get_name(short=True))
        if current_bar.is_closed:
            #flash('The bar is currently closed for orders.', 'warning')
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
                    flash("Unfortunately the bar is closed right now :(", 'warning')
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
                                    variants=True), fancy=False)

                # add to the order database
                order = Order(bar_id=current_bar.id, bartender_id=current_bar.bartender.id,
                        timestamp=datetime.datetime.utcnow(),
                        recipe_name=recipe.name, recipe_html=email_recipe_html)
                if current_user.is_authenticated:
                    order.user_id = current_user.id
                db.session.add(order)
                db.session.commit()

                # TODO add a verifiable token to this
                subject = "[Mix-Mind] {} at {}".format(recipe.name, current_bar.name)
                confirmation_link = "https://{}{}".format(request.host,
                        url_for('confirm_order',
                            email=urllib.quote(user_email),
                            order_id=order.id))

                send_mail(subject, current_bar.bartender.email, "order_submitted",
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
    # TODO this also needs to handle race conditions when switching bars......
    email = urllib.unquote(request.args.get('email'))
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
    user = User.query.filter_by(email=email).one_or_none()
    if user:
        greeting = "{}, you".format(user.get_name(short=True))
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


@app.route('/user', methods=['GET', 'POST'])
@login_required
def user_profile():
    try:
        user_id = int(request.args.get('user_id'))
    except ValueError:
        flash("Invalid user_id parameter", 'danger')
        return render_template('result.html', "User profile unavailable")

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
        return render_template('result.html', "User profile unavailable")

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

    return render_template('user_profile.html', this_user=this_user, edit_user=form)


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
    BAR_BULK_ATTRS = 'name,tagline,prices,prep_line,examples,convert,markup,info,origin,variants,summarize'.split(',')
    new_bar_form = get_form(CreateBarForm)
    edit_bar_form = get_form(EditBarForm)
    if request.method == 'POST':
        if 'create_bar' in request.form:
            if new_bar_form.validate():
                if Bar.query.filter_by(cname=new_bar_form.cname.data).one_or_none():
                    flash("Bar name already in use", 'warning')
                    return redirect(request.url)
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

        elif 'edit_bar' in request.form:
            if edit_bar_form.validate():
                # TODO allow manager to edit this one? use different post url
                bar_id = edit_bar_form.bar_id.data
                bar = Bar.query.filter_by(id=bar_id).one_or_none()
                if bar is None:
                    flash("Invalid bar_id: {}".format(edit_bar_form.bar_id.data), 'danger')
                    return redirect(request.url)

                # add bartender on duty
                user = user_datastore.find_user(email=edit_bar_form.bartender.data)
                if user and user.id != bar.bartender_on_duty:
                    bartender = user_datastore.find_role('bartender')
                    user_datastore.add_role_to_user(user, bartender)
                    bar.bartenders.append(user)
                    bar.bartender_on_duty = user.id
                    # TODO send email to bartender on duty

                for attr in BAR_BULK_ATTRS:
                    setattr(bar, attr, getattr(edit_bar_form, attr).data)
                db.session.commit()
                flash("Successfully updated config for {}".format(bar.cname))

            else:
                flash("Error in form validation", 'warning')

        elif 'activate-bar' in request.form:
            bar_id = request.form.get('bar_id', None, int)
            if bar_id == current_bar.id:
                flash("Bar ID: {} is already active".format(bar_id), 'warning')
                return redirect(request.url)
            if not Bar.query.filter_by(id=bar_id).one_or_none():
                flash("Error: Bar ID: {} is invalid".format(bar_id), 'danger')
                return redirect(request.url)
            # TODO make this shit atomicer
            bars = Bar.query.all()
            for bar in bars:
                bar.is_active = bar.id == bar_id
            db.session.commit()
            mms.regenerate_recipes()
            flash("Bar ID: {} is now active".format(bar_id), 'success')
            return redirect(request.url)

    # for GET requests, fill in the edit bar form
    edit_bar_form.bar_id.render_kw['value'] = current_bar.id
    for attr in BAR_BULK_ATTRS:
        setattr(getattr(edit_bar_form, attr), 'data', getattr(current_bar, attr))

    bars = Bar.query.all()
    users = User.query.all()
    orders = Order.query.all()
    #bar_table = bars_as_table(bars)
    user_table = users_as_table(users)
    order_table = orders_as_table(orders)
    return render_template('dashboard.html', new_bar_form=new_bar_form, edit_bar_form=edit_bar_form,
            users=users, orders=orders,
            bars=bars, user_table=user_table, order_table=order_table)


@app.route("/api/test")
def api_test():
    a = request.args.get('a', 0, type=int)
    b = request.args.get('b', 0, type=int)
    return jsonify(result=a + b)

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
    return render_template('result.html', heading="Still under construction...")
    select_form = get_form(RecipeListSelector)
    print select_form.errors
    add_form = get_form(RecipeForm)
    print add_form.errors

    if request.method == 'POST':
        print request
        if 'recipe-list-select' in request.form:
            recipes = select_form.recipes.data
            mms.regenerate_recipes()
            flash("Now using recipes from {}".format(recipes))

    return render_template('recipes.html', select_form=select_form, add_form=add_form)


@app.route("/admin/ingredients", methods=['GET','POST'])
@login_required
@roles_required('admin')
def ingredient_stock():
    form = get_form(BarstockForm)
    upload_form = get_form(UploadBarstockForm)
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
            Barstock_SQL(current_bar.id).add_row(row)
            mms.regenerate_recipes()

        elif 'remove-ingredient' in request.form:
            pass # TODO this with datatable
            bottle = form.bottle.data
            if bottle in mms.barstock.df.Bottle.values:
                mms.barstock.df = mms.barstock.df[mms.barstock.df.Bottle != bottle]
                mms.regenerate_recipes()
                flash("Removed {}".format(bottle))
            else:
                flash("Error: \"{}\" not found; must match as shown below exactly".format(bottle), 'danger')

        elif 'toggle-in-stock' in request.form:
            uid = urllib.unquote(request.form['uid'])
            ingredient = Ingredient.query_by_uid(uid)
            ingredient.In_Stock = not ingredient.In_Stock
            db.session.commit()

        elif 'upload-csv' in request.form:
            # TODO handle files < 500 kb by keeping in mem
            csv_file = request.files['upload_csv']
            if not csv_file or csv_file.filename == '':
                flash('No selected file', 'danger')
                return redirect(request.url)
            _, tmp_filename = tempfile.mkstemp()
            csv_file.save(tmp_filename)
            Barstock_SQL(current_bar.id).load_from_csv([tmp_filename], current_bar.id)
            os.remove(tmp_filename)
            mms.regenerate_recipes()
            msg = "Ingredients database {} {} for bar {}".format(
                    "replaced by" if upload_form.replace_existing.data else "added to from",
                    csv_file.filename, current_bar.id)
            log.info(msg)
            flash(msg, 'success')

        elif 'reload-recipes' in request.form:
            mms.regenerate_recipes()
            flash("Reloaded the recipe library from current ingredients for {}".format(current_bar.cname))

    ingredients = Ingredient.query.filter_by(bar_id=current_bar.id).order_by(Ingredient.Category, Ingredient.Type).all()
    stock_table = ingredients_as_table(ingredients)
    return render_template('ingredients.html', form=form, upload_form=upload_form, stock_table=stock_table)

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
