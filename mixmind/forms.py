"""
Definitions of the various forms used
"""
from wtforms import validators, widgets, Form, Field, FormField, FieldList, TextField, TextAreaField, BooleanField, DecimalField, IntegerField, SelectField, SelectMultipleField, FileField, PasswordField, StringField, SubmitField, HiddenField
from flask import g

from .models import User
from .util import VALID_UNITS

# TODO refactor with flask_wtf which presets form csrfs (or roll my own I guess)
# TODO use InputRequired validator

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

class HiddenIntField(IntegerField):
    widget = widgets.HiddenInput()

class EmailField(TextField):
    def process_formdata(self, valuelist):
        if valuelist[0]:
            self.data = valuelist[0].strip()
        else:
            self.data = ""

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
    convert = TextField("Convert", description="Convert recipes to a different primary unit", default=None, validators=[validators.AnyOf(VALID_UNITS), validators.Optional()])
    markup = DecimalField("Margin", description="Drink markup: price = ceil((base_cost+1)*markup)", default=1.1) # TODO config management
    info = BooleanField("Info", description="Show the info line for recipes")
    origin = BooleanField("Origin", description="Check origin and mark drinks as Schubar originals")
    variants = BooleanField("Variants", description="Show variants for drinks")

    # filtering options
    all_ = BooleanField("Allow all ingredients", description="Include all recipes, regardless of if they can be made from the loaded barstock")
    include = CSVField("Include Ingredients", description="Ingredient(s), separated by commas")
    exclude = CSVField("Exclude Ingredients", description="Ingredient(s), separated by commas")
    use_or = BooleanField("Logical OR", description="Use logical OR for included and excluded ingredient lists instead of default AND")
    name = TextField("Name", description="Filter by a cocktail's name")
    tag = TextField("Tag", description="Filter by tag")
    style = SelectField("Style", description="", choices=pairs(['','All Day Cocktail','Before Dinner Cocktail','After Dinner Cocktail','Longdrink', 'Hot Drink', 'Sparkling Cocktail', 'Wine Cocktail']))
    glass = SelectField("Glass", description="", choices=pairs(['','cocktail','martini','collins','rocks','highball','flute','shot','shooter','mug']))
    prep = SelectField("Prep", description="", choices=pairs(['','shake', 'stir', 'build', 'throw']))
    ice = SelectField("Ice", description="", choices=pairs(['','cubed','crushed','neat']))

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
    unit = SelectField("Unit", choices=pairs([VALID_UNITS]), validators=[validators.required()])
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

class UploadBarstockForm(Form):
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)
    upload_csv = FileField("Upload a Barstock CSV", [validators.regexp(ur'^[^/\\]\.csv$')])
    replace_existing = BooleanField("Replace existing stock?", default=False)

class BarstockForm(Form):
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)

    categories = 'Spirit,Liqueur,Vermouth,Bitters,Syrup,Dry,Juice,Mixer,Wine,Ice'.split(',')
    #types = ',Brandy,Dry Gin,Genever,Amber Rum,White Rum,Dark Rum,Rye Whiskey,Vodka,Orange Liqueur,Dry Vermouth,Sweet Vermouth,Aromatic Bitters,Orange Bitters,Fruit Bitters,Bourbon Whiskey,Tennessee Whiskey,Irish Whiskey,Scotch Whisky,Silver Tequila,Gold Tequila,Mezcal,Aquavit,Amaretto,Blackberry Liqueur,Raspberry Liqueur,Campari,Amaro,Cynar,Aprol,Creme de Cacao,Creme de Menthe,Grenadine,Simple Syrup,Rich Simple Syrup,Honey Syrup,Orgeat,Maple Syrup,Sugar'.split(',')
    category = SelectField("Category", validators=[validators.required()], choices=pairs(categories))
    #type_ = SelectField("Type", validators=[validators.required()], choices=pairs(types))
    type_ = TextField("Type", validators=[validators.required()])
    bottle = TextField("Brand", description='Specify the bottle, e.g. "Bulliet Rye", "Beefeater", "Tito\'s", or "Bacardi Carta Blanca"', validators=[validators.required()])
    proof = DecimalField("Proof", description="Proof rating of the ingredient, if any", validators=[validators.required(), validators.NumberRange(min=0, max=200)])
    size_ml = DecimalField("Size (mL)", description="Size of the ingredient in mL", validators=[validators.required(), validators.NumberRange(min=0, max=20000)])
    price = DecimalField("Price ($)", description="Price paid or approximate market value in USD", validators=[validators.required(), validators.NumberRange(min=0, max=2000)])

class OrderForm(Form):
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)
    notes = TextField("Notes")

class OrderFormAnon(OrderForm):
    name = TextField("Your Name", validators=[validators.required()])
    email = EmailField("Confirmation Email", validators=[validators.Email("Invalid email address"), validators.required()])

class LoginForm(Form):
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)
    #name = TextField("Your Name", validators=[validators.required()])
    email = EmailField("Email", validators=[validators.required()])
    password = PasswordField("Password", validators=[validators.required()])

class EditUserForm(Form):
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    nickname = StringField('Nickname')
    venmo_id = StringField('Venmo ID') # TODO integrate venmo logo!
    submit = SubmitField('Save Profile')

class CreateBarForm(Form):
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)
    cname = TextField("Bar Unique Name", description="Unique name for the bar", validators=[validators.required()])
    name = TextField("Bar Display Name", description="Display name for the bar, leave blank to use unique name")
    tagline = TextField("Tagline", description="Tag line or slogan for the bar")
    create_bar = SubmitField("Create Bar", render_kw={"class": "btn btn-success"})

class EditBarForm(Form):
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)
    bar_id = HiddenIntField("bar_id", render_kw={})
    name = TextField("Bar Name", description="Display name for the bar")
    tagline = TextField("Tagline", description="Tag line or slogan for the bar")

    # someday use just "bartenders"
    bartender = SelectField("Assign Bartender On Duty", description="Assign a bartender to receive orders",
            choices=[('', '')]+[(user.email, user.get_name_with_email()) for user in User.query.all()])

    prices = BooleanField("Prices", description="Show prices")
    prep_line = BooleanField("Preparation", description="Show preparation instructions")
    examples = BooleanField("Examples", description="Show specific examples for each recipe")
    convert = TextField("Convert", description="Convert all recipes to one unit", default=None, validators=[validators.AnyOf(VALID_UNITS), validators.Optional()])
    markup = DecimalField("Margin", description="Drink markup: price = ceil((base_cost+1)*markup)")
    info = BooleanField("Info", description="Adds info tidbit to recipes")
    origin = BooleanField("Origin", description="Denote drinks originating at Schubar")
    variants = BooleanField("Variants", description="List variants for drinks")
    summarize = BooleanField("Summarize", description="List ingredient names instead of full recipe")
    edit_bar = SubmitField("Commit Changes", render_kw={"class": "btn btn-success"})
