""" Module handles thread safe configuration management
- uses backing database to get all "global" config required in a request
- makes available to request in the flask.g via a local proxy
- ensures changes to global config don't cause races in the middle of a request
TODO:
    - recipe library still technically needs synchronization
"""
import os.path
from collections import namedtuple

from flask import g, flash
from flask_login import current_user

from .recipe import DrinkRecipe
from .barstock import Barstock_SQL, Ingredient
from .database import db
from .models import Bar, User
from .util import load_recipe_json, to_human_diff, get_ts_formatter
from . import log
# TODO: No handlers could be found for logger "root"
# actual log infos instead of prints

def get_recipe_files(app):
    return get_checked_files(app,
            app.config.get('MIXMIND_RECIPES_DIR'),
            app.config.get('MIXMIND_DEFAULT_RECIPES'))

def get_ingredient_files(app):
    return get_checked_files(app,
            app.config.get('MIXMIND_INGREDIENTS_DIR'),
            app.config.get('MIXMIND_DEFAULT_INGREDIENTS'))

def get_checked_files(app, partial_path, files):
    abspath = app.config.get('MIXMIND_DIR')
    files = [os.path.join(abspath, partial_path, f) for f in files]
    missing = {0}-{0}
    for f in files:
        if not os.path.isfile(f):
            missing.add(f)
            log.warning("{} not found, will be omitted".format(f))
    return list(set(files) - missing)

class MixMindServer():
    """ Contains the global recipe library and handle to the barstock"""
    def __init__(self, app):
        self.time_diff_formatter = to_human_diff
        self.time_human_formatter = get_ts_formatter(app.config.get('HUMAN_FORMAT'), app.config.get('TIMEZONE'))
        self.timestamp_formatter = get_ts_formatter(app.config.get('PRECISE_FORMAT'), app.config.get('TIMEZONE'))
        # setup default Bar
        default_bar = Bar(name=app.config['MIXMIND_DEFAULT_BAR_NAME'],
                cname=app.config.get('MIXMIND_DEFAULT_BAR_CNAME', app.config['MIXMIND_DEFAULT_BAR_NAME']),
                is_public=True, is_default=True)
        existing_default_bar = Bar.query.filter_by(cname=default_bar.cname).one_or_none()
        if existing_default_bar:
            default_bar = existing_default_bar
        else:
            print ("STARTUP: Adding default bar \"{}\"".format(default_bar.cname))
            db.session.add(default_bar)
            db.session.commit()
        # setup ingredient stock, using default if the database is empty
        barstock = Barstock_SQL(default_bar.id)
        if Ingredient.query.filter_by(bar_id=default_bar.id).count() == 0:
            barstock_files = get_ingredient_files(app)
            print ("STARTUP: Loading ingredient stock from files: {}".format(barstock_files))
            barstock.load_from_csv(barstock_files, default_bar.id)
        # initialize recipe library
        recipe_files = get_recipe_files(app)
        print ("STARTUP: Loading recipes from files: {}".format(recipe_files))
        self.base_recipes = load_recipe_json(recipe_files)
        self.processed_recipes = {}
        # TODO Probably don't load all the recipes rn...
        for bar in Bar.query.all():
            print "STARTUP:",
            self.generate_recipes(bar)

    def find_recipe(self, bar_id, name):
        for recipe in self.processed_recipes[bar_id]:
            if recipe.name == name:
                return recipe
        return None

    def generate_recipes(self, bar):
        print ("Generating recipe library for {}".format(bar.cname))
        barstock = Barstock_SQL(bar.id)
        self.processed_recipes[bar.id] = [DrinkRecipe(name, recipe).generate_examples(barstock, stats=True)
                for name, recipe in self.base_recipes.iteritems()]

    def regenerate_recipes(self, bar, ingredient=None, recipe_name=None):
        """Regenerate the examples and statistics data for the recipes at the given bar
        :param string ingredient: only updates recipes with the given ingredient
        :param string reipce_name: only updates the given recipe
        """
        if bar.id not in self.processed_recipes:
            self.generate_recipes(bar)
            return
        if ingredient:
            print ("Updating recipes containing {} for {}".format(ingredient, bar.cname))
            [recipe.generate_examples(Barstock_SQL(bar.id), stats=True) for recipe in self.processed_recipes[bar.id]
                            if recipe.contains_ingredient(ingredient)]
        elif recipe_name:
            recipe = find_recipe(self.processed_recipes[bar.id], recipe_name)
            if recipe is None:
                print ("Error: no recipe found matching name \"{}\"".format(recipe_name))
            print ("Updating recipe {} at {}".format(recipe, bar.cname))
            recipe.generate_examples(Barstock_SQL(bar.id), stats=True)
        else:
            print ("Regenerating recipe library for {}".format(bar.cname))
            [recipe.generate_examples(Barstock_SQL(bar.id), stats=True) for recipe in self.processed_recipes[bar.id]]

BarConfig = namedtuple("BarConfig", "id,cname,name,tagline,owner,bartender,markup,prices,stats,examples,convert,prep_line,origin,info,variants,summarize,is_closed,is_public")

def get_bar_config():
    """ For now, only one bar bay me "active" at a time
    """
    if 'bar_list' not in g:
        # HAX just putting it here for now to get initialized
        g.bar_list = Bar.query.all()
    if 'current_bar' not in g:
        bar = None
        if current_user.is_authenticated and current_user.current_bar_id:
            bar = Bar.query.filter_by(id=current_user.current_bar_id).one_or_none()
        if not bar:
            default_list = Bar.query.filter_by(is_default=True).all()
            if len(default_list) == 0:
                flash("No bars currently set to default!", 'danger')
                raise RuntimeError("No bar set to default in the database - must be at least one.")
            elif len(default_list) > 1:
                flash("More than one bar is set to default, using first one", 'danger')
            bar = default_list[0]
        bartender = User.query.filter_by(id=bar.bartender_on_duty).one_or_none()
        g.current_bar = BarConfig(id=bar.id, cname=bar.cname, name=bar.name,
                tagline=bar.tagline, owner=bar.owner, bartender=bartender, markup=bar.markup,
                prices=bar.prices, stats=bar.stats, examples=bar.examples, convert=bar.convert,
                prep_line=bar.prep_line, origin=bar.origin, info=bar.info, variants=bar.variants,
                summarize=bar.summarize, is_closed=not bartender, is_public=bar.is_public)
    return g.current_bar
