""" Configuration of app.config dict
"""
import os.path
import logging
log = logging.getLogger()

# flask-sqlalchemy
SQLALCHEMY_TRACK_MODIFICATIONS = False # explicitly remove deprecated feature

# logging
#path = app.config['LOGGING_PATH']
#os.makedirs(path, exist_ok=True)
#info_fh = RotatingFileHandler(os.path.join(path, 'mixmind.log'), maxBytes=10000000, backupCount=3)
#info_fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
#info_fh.setLevel(logging.INFO)
#log = logging.getLogger()

# mix-mind
MIXMIND_DIR = os.path.abspath(os.path.curdir)
MIXMIND_RECIPES_DIR = "recipes/"
MIXMIND_INGREDIENTS_DIR = "ingredients/"

MIXMIND_DEFAULT_RECIPES = ["recipes_schubar.json", "IBA_all.json"]
MIXMIND_DEFAULT_INGREDIENTS = ["12BBplus.csv"]

def get_recipe_files(app):
    return get_checked_files(app, MIXMIND_RECIPES_DIR, MIXMIND_DEFAULT_RECIPES)

def get_ingredient_files(app):
    return get_checked_files(app, MIXMIND_INGREDIENTS_DIR, MIXMIND_DEFAULT_INGREDIENTS)

def get_checked_files(app, partial_path, files):
    abspath = app.config.get('MIXMIND_DIR', MIXMIND_DIR)
    files = [os.path.join(abspath, partial_path, f) for f in files]
    missing = {0}-{0}
    for f in files:
        if not os.path.isfile(f):
            missing.add(f)
            log.warning("{} not found, will be omitted".format(f))
    return list(set(files) - missing)
