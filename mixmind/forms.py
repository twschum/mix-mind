"""
Definitions of the various forms used
"""
from wtforms import validators, widgets, Form, Field, FormField, FieldList, TextField, TextAreaField, BooleanField, DecimalField, IntegerField, SelectField, SelectMultipleField, FileField, PasswordField, StringField, SubmitField, HiddenField, compat
from flask import g

from .models import User
from .util import VALID_UNITS

# TODO refactor with flask_wtf which presets form csrfs (or roll my own I guess)

class BaseForm(Form):
    """Custom Form class that implements csrf by default
    render with {{ form.csrf }} in templates
    """
    def reset(self):
        blankData = MultiDict([('csrf', self.reset_csrf())])
        self.process(blankData)

class CSVField(Field):
    """Text field that parses data as comma separated values
    """
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

class SelectExtended(widgets.Select):
    """
    Renders a select field, with disabled options

    If `multiple` is True, then the `size` property should be specified on
    rendering to make the field useful.

    The field must provide an `iter_choices()` method which the widget will
    call on rendering; this method must yield tuples of
    `(value, label, selected, disabled)`.
    """
    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        if self.multiple:
            kwargs['multiple'] = True
        html = ['<select %s>' % widgets.html_params(name=field.name, **kwargs)]
        for val, label, selected, disabled in field.iter_choices():
            html.append(self.render_option(val, label, selected, disabled))
        html.append('</select>')
        return widgets.HTMLString(''.join(html))

    @classmethod
    def render_option(cls, value, label, selected, disabled, **kwargs):
        if value is True:
            # Handle the special case of a 'True' value.
            value = compat.text_type(value)
        options = dict(kwargs, value=value)
        if selected:
            options['selected'] = True
        if disabled:
            options['disabled'] = True
        return widgets.HTMLString('<option %s>%s</option>' % (widgets.html_params(**options), compat.text_type(label)))


class SelectWithPlaceholderField(SelectField):
    """Make the first option disabled selected, thus like a placeholder
    <option value="" disabled selected>Select your option</option>
    """
    widget = SelectExtended()
    def iter_choices(self):
        first = True
        for value, label in self.choices:
            yield (value, label, self.coerce(value) == self.data, first)
            first = False


class ToggleField(BooleanField):
    """Subclass check field to take advantge of the
    bootstrap toggle plugin
    """
    def __init__(self, label='', validators=None, **kwargs):
        """on and off are the text for on/off states
        onstyle/offstyle are the button style, see bs buttons
        """
        render_kw = kwargs.pop('render_kw', {})
        render_kw['data-toggle'] = 'toggle'
        for field in 'on,onstyle,off,offstyle,size'.split(','):
            arg = kwargs.pop(field, None)
            if arg:
                render_kw['data-{}'.format(field)] = arg
        super(ToggleField, self).__init__(label, validators, render_kw=render_kw, **kwargs)

class HiddenIntField(IntegerField):
    """Hidden field and have it coerced into an integer on validate
    """
    widget = widgets.HiddenInput()

class EmailField(TextField):
    """Todo
    """
    def process_formdata(self, valuelist):
        if valuelist[0]:
            self.data = valuelist[0].strip()
        else:
            self.data = ""

def pairs(l):
    return [(x,x) for x in l]

class DrinksForm(BaseForm):
    # display options
    prices = BooleanField("Prices", description="Display prices for drinks based on stock")
    prep_line = BooleanField("Preparation", description="Display a line showing glass, ice, and prep")
    stats = BooleanField("Stats", description="Print out a detailed statistics block for the selected recipes")
    examples = BooleanField("Examples", description="Show specific examples of a recipe based on the ingredient stock")
    all_ingredients = BooleanField("All Ingredients", description="Show every ingredient instead of just the main liquors with each example")
    convert = TextField("Convert", description="Convert recipes to a different primary unit", default=None, validators=[validators.AnyOf(VALID_UNITS), validators.Optional()])
    markup = DecimalField("Margin", description="Drink markup: price = ceil((base_cost+1)*markup)", default=1.1) # TODO config management (current_bar)
    info = BooleanField("Info", description="Show the info line for recipes")
    origin = BooleanField("Origin", description="Check origin and mark drinks as Schubar originals")
    variants = BooleanField("Variants", description="Show variants for drinks")

    # filtering options
    search = TextField("", description="")
    all_ = BooleanField("Allow all ingredients", description="Include all recipes, regardless of if they can be made from the loaded barstock")
    include = CSVField("Include Ingredients", description="Recipes that contain any/all of these comma separated ingredient(s)")
    exclude = CSVField("Exclude Ingredients", description="Recipes that don't contain any/all of these comma separated ingredient(s)")
    include_use_or = ToggleField("<br>", on="any", off="all", onstyle="secondary", offstyle="secondary")
    exclude_use_or = ToggleField("<br>", on="any", off="all", onstyle="secondary", offstyle="secondary")
    name = TextField("Name", description="Filter by a cocktail's name")
    tag = TextField("Tag", description="Filter by tag")
    style = SelectField("Style", description="", choices=pairs(['','All Day Cocktail','Before Dinner Cocktail','After Dinner Cocktail','Longdrink', 'Hot Drink', 'Sparkling Cocktail', 'Wine Cocktail']))
    glass = SelectField("Glass", description="", choices=pairs(['','cocktail','martini','collins','rocks','highball','flute','shot','shooter','mug']))
    prep = SelectField("Prep", description="", choices=pairs(['','shake', 'stir', 'build', 'throw']))
    ice = SelectField("Ice", description="", choices=pairs(['','cubed','crushed','neat']))

    # sorting options
    # abv, cost, alcohol content
    sorting = SelectWithPlaceholderField("", choices=[
        ('None', "Sort Results..."),
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


class RecipeIngredientForm(BaseForm):
    ingredient = TextField("Ingredient", validators=[validators.InputRequired()])
    quantity = DecimalField("Quantity", validators=[validators.InputRequired()])
    is_optional = BooleanField("Optional")
class RecipeForm(BaseForm):
    name = TextField("Name", description="The recipe name", validators=[validators.InputRequired()])
    info = TextField("Info", description="Additional information about the recipe")
    ingredients = FieldList(FormField(RecipeIngredientForm), min_entries=1, validators=[validators.InputRequired()])
    unit = SelectField("Unit", choices=pairs(VALID_UNITS), validators=[validators.InputRequired()])
    #glass =
    #unit =
    #prep =
    #ice =
    #garnish =

class RecipeListSelector(BaseForm):
    recipes = SelectMultipleField("Available Recipe Lists", description="Select recipe lists to be used for generating a menu",
            choices=[("recipes_schubar.json", "Core Recipes (from @Schubar)"),
                ("IBA_unforgettables.json", "IBA Unforgettables"),
                ("IBA_contemporary_classics.json", "IBA Contemporary Classics"),
                ("IBA_new_era_drinks.json", "IBA New Era Drinks")])

class UploadBarstockForm(BaseForm):
    upload_csv = FileField("Upload a Barstock CSV", [validators.regexp(ur'^[^/\\]\.csv$')])
    replace_existing = BooleanField("Replace existing stock?", default=False)

class BarstockForm(BaseForm):

    categories = 'Spirit,Liqueur,Vermouth,Bitters,Syrup,Dry,Juice,Mixer,Wine,Ice'.split(',')
    # TODO maybe as an "other" then fill...
    types = 'Brandy,Dry Gin,Genever,Amber Rum,White Rum,Dark Rum,Rye Whiskey,Vodka,Orange Liqueur,Dry Vermouth,Sweet Vermouth,Aromatic Bitters,Orange Bitters,Fruit Bitters,Bourbon Whiskey,Tennessee Whiskey,Irish Whiskey,Scotch Whisky,Silver Tequila,Gold Tequila,Mezcal,Aquavit,Amaretto,Blackberry Liqueur,Raspberry Liqueur,Campari,Amaro,Cynar,Aprol,Creme de Cacao,Creme de Menthe,Grenadine,Simple Syrup,Rich Simple Syrup,Honey Syrup,Orgeat,Maple Syrup,Sugar'.split(',')
    def types_list(self):
        return ', '.join(types)
    category = SelectField("Category", validators=[validators.InputRequired()], choices=pairs(categories))
    #type_ = SelectField("Type", validators=[validators.InputRequired()], choices=pairs(types))
    type_ = TextField("Type", description='The broader type that an ingredient falls info, e.g. "Dry Gin" or "Orange Liqueur"', validators=[validators.InputRequired()])
    bottle = TextField("Brand", description='The specific ingredient, e.g. "Bulliet Rye", "Beefeater", "Tito\'s", or "Bacardi Carta Blanca"', validators=[validators.InputRequired()])
    abv = DecimalField("ABV", description='Alcohol by Volume (percentage) of the ingredient, i.e. enter "20" if the ABV is 20%', validators=[validators.InputRequired(), validators.NumberRange(min=0, max=100)])

    unit = SelectField("Unit", choices=pairs([VALID_UNITS[1],VALID_UNITS[0]]+VALID_UNITS[2:]), validators=[validators.InputRequired()])
    size = DecimalField("Size", description="Size of the ingredient in the unit selected", validators=[validators.InputRequired(), validators.NumberRange(min=0, max=20000)])
    price = DecimalField("Price ($)", description="Price paid or approximate market value in USD", validators=[validators.InputRequired(), validators.NumberRange(min=0, max=9999999999)])

class OrderForm(BaseForm):
    notes = TextField("Notes")

class OrderFormAnon(OrderForm):
    name = TextField("Your Name", validators=[validators.InputRequired()])
    email = EmailField("Confirmation Email", validators=[validators.Email("Invalid email address"), validators.InputRequired()])

class LoginForm(BaseForm):
    #name = TextField("Your Name", validators=[validators.InputRequired()])
    email = EmailField("Email", validators=[validators.InputRequired()])
    password = PasswordField("Password", validators=[validators.InputRequired()])

class EditUserForm(BaseForm):
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    nickname = StringField('Nickname')
    venmo_id = StringField('Venmo ID')
    submit = SubmitField('Save Profile')

class CreateBarForm(BaseForm):
    cname = TextField("Bar Unique Name", description="Unique name for the bar", validators=[validators.InputRequired()])
    name = TextField("Bar Display Name", description="Display name for the bar, leave blank to use unique name")
    tagline = TextField("Tagline", description="Tag line or slogan for the bar")
    create_bar = SubmitField("Create Bar", render_kw={"class": "btn btn-success"})

class EditBarForm(BaseForm):
    def __init__(self, *args, **kwargs):
        super(EditBarForm, self).__init__(*args, **kwargs)
        print "GENERATING USER CHOICES"
        choices = [('', '')]+[(user.email, user.get_name_with_email()) for user in User.query.all()]
        self.bartender.choices = choices
        self.owner.choices = choices
    bar_id = HiddenIntField("bar_id", render_kw={})
    name = TextField("Bar Name", description="Display name for the bar")
    tagline = TextField("Tagline", description="Tag line or slogan for the bar")

    ONTEXT = "On"
    OFFTEXT = "Off"
    ONSTYLE = "secondary"
    OFFSTYLE = None

    # TODO use just "bartenders" for the current bar after there's a real syetem
    # for bars to pick bartenders - maybe off the user page
    # user table on dashboard could generate links to edit the user page, user has a selectmultiple for roles
    status = ToggleField("Bar Status", description="Open or close the bar to orders",
            on="Open", off="Closed", onstyle="success", offstyle="danger")
    is_public = ToggleField("Public", description="Make the bar available to browse",
            on="Visible", off="Hidden", onstyle="success", offstyle="danger")
    bartender = SelectField("Assign Bartender On Duty", description="Assign a bartender to receive orders", choices=[])
    owner = SelectField("Assign Bar Owner", description="Assign an owner who can manage the bar's stock and settings", choices=[])

    prices = ToggleField("Prices", description="Show prices",
            on="Included", off="Free", onstyle="success", offstyle="secondary")
    prep_line = ToggleField("Preparation", description="Show preparation instructions",
            on=ONTEXT, off=OFFTEXT, onstyle=ONSTYLE, offstyle=OFFSTYLE)
    examples = ToggleField("Examples", description="Show specific examples for each recipe",
            on=ONTEXT, off=OFFTEXT, onstyle=ONSTYLE, offstyle=OFFSTYLE)
    convert = SelectField("Convert to", choices=[('', 'None')]+pairs(VALID_UNITS))
    markup = DecimalField("Margin", description="Drink markup: price = ceil((base_cost+1)*markup)")
    info = ToggleField("Info", description="Adds info tidbit to recipes",
            on=ONTEXT, off=OFFTEXT, onstyle=ONSTYLE, offstyle=OFFSTYLE)
    origin = ToggleField("Origin", description="Denote drinks originating at Schubar",
            on=ONTEXT, off=OFFTEXT, onstyle=ONSTYLE, offstyle=OFFSTYLE)
    variants = ToggleField("Variants", description="List variants for drinks",
            on=ONTEXT, off=OFFTEXT, onstyle=ONSTYLE, offstyle=OFFSTYLE)
    summarize = ToggleField("Summarize", description="List ingredient names instead of full recipe",
            on=ONTEXT, off=OFFTEXT, onstyle=ONSTYLE, offstyle=OFFSTYLE)
    edit_bar = SubmitField("Commit Changes", render_kw={"class": "btn btn-primary"})
