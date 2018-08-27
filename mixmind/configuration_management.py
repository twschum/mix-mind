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

from .recipe import DrinkRecipe
from .barstock import Barstock_SQL, Ingredient
from .database import db
from .models import Bar, User
from .util import load_recipe_json
from . import log

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
        # setup default Bar
        default_bar = Bar(name=app.config['MIXMIND_DEFAULT_BAR_NAME'],
                cname=app.config.get('MIXMIND_DEFAULT_BAR_CNAME', app.config['MIXMIND_DEFAULT_BAR_NAME']),
                is_active=True)
        existing_default_bar = Bar.query.filter_by(cname=default_bar.cname).one_or_none()
        if existing_default_bar:
            default_bar = existing_default_bar
        else:
            db.session.add(default_bar)
            db.session.commit()
        # setup ingredient stock, using default if the database is empty
        self.barstock = Barstock_SQL()
        if Ingredient.query.count() == 0:
            barstock_files = get_ingredient_files(app)
            self.barstock.load_from_csv(barstock_files, default_bar.id)
        # initialize recipe library
        recipe_files = get_recipe_files(app)
        self.base_recipes = load_recipe_json(recipe_files)
        self.recipes = [DrinkRecipe(name, recipe).generate_examples(self.barstock, stats=True)
                for name, recipe in self.base_recipes.iteritems()]

    def regenerate_recipes(self):
        self.recipes = [recipe.generate_examples(self.barstock, stats=True) for recipe in  self.recipes]

BarConfig = namedtuple("BarConfig", "id,cname,name,bartender,margin")

def get_bar_config():
    """ For now, only one bar bay me "active" at a time
    """
    if 'current_bar' not in g:
        active_list = Bar.query.filter_by(is_active=True).all()
        if len(active_list) == 0:
            flash("No bars currently active!", 'danger')
            raise RuntimeError("No active bars in the database - must be at least one.")
        elif len(active_list) > 1:
            flash("More than one bar is active, using first one", 'danger')
        bar = active_list[0]
        bartender = User.query.filter_by(id=bar.bartender_on_duty).one_or_none()
        g.current_bar = BarConfig(id=bar.id, cname=bar.cname, name=bar.name, bartender=bartender,
                margin=bar.margin)
    return g.current_bar
