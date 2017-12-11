#!/usr/bin/env python

from flask import Flask
app = Flask(__name__)

import menu_gen
import recipe as drink_recipe

class MixMindServer():
    def __init__(self):
        base_recipes = menu_gen.load_recipe_json(['recipes.json'])
        self.recipes = {name:drink_recipe.DrinkRecipe(name, recipe) for name, recipe in base_recipes.iteritems()}

mms = MixMindServer()

@app.route('/')
def hello():
    return "Hello, World!"

@app.route('/Martini')
def martini():
    return str(mms.recipes['Martini'])

@app.route('/json/<recipe_name>')
def recipe_json():
    print recipe_name
    try:
        return str(mms.recipes[recipe_name])
    except KeyError:
        return "{} not found".format(recipe_name)

