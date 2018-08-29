""" Helper utils to compose objects as blobs of html
"""
import yattag

import util
from recipe import QuantizedIngredient

def close(content, tag, **kwargs):
    if "class_" in kwargs:
        kwargs["class"] = kwargs["class_"]
    if "klass" in kwargs:
        kwargs["class"] = kwargs["klass"]
    attributes = ' '.join(['{}="{}"'.format(k, v) for k, v in kwargs.iteritems()])
    return '<{0} {2}>{1}</{0}>'.format(tag, content, attributes)

def em(content, **kwargs):
    return close(content, 'em', **kwargs)
def small(content, **kwargs):
    return close(content, 'small', **kwargs)
def sup(content, **kwargs):
    return close(content, 'sup', **kwargs)
def small_br(content, **kwargs):
    return small(content+'<br>', **kwargs)
def wrap_link(link, content, **kwargs):
    return '<a href={}>{}</a>'.format(link, content, **kwargs)

def recipe_as_html(recipe, display_opts, order_link=None, condense_ingredients=False, fancy=True, convert_to=None):
    """ use yattag lib to build an html blob contained in a div for the recipe"""
    doc, tag, text, line = yattag.Doc().ttl()

    """
            "https://upload.wikimedia.org/wikipedia/commons/3/3a/Cocktail_Glass_%28Martini%29.svg"
            "https://upload.wikimedia.org/wikipedia/commons/c/c8/Highball_Glass_%28Tumbler%29.svg"
            "https://upload.wikimedia.org/wikipedia/commons/4/4c/Old_Fashioned_Glass.svg"
            "https://upload.wikimedia.org/wikipedia/commons/6/6b/Irish_Coffee_Glass_%28Footed%29.svg"
            "https://upload.wikimedia.org/wikipedia/commons/4/4e/Wine_Glass_%28White%29.svg"
            "https://upload.wikimedia.org/wikipedia/commons/a/ac/Shot_Glass_%28Standard%29.svg"
            "https://upload.wikimedia.org/wikipedia/commons/1/1e/Flute_Glass.svg"
    """

    glassware = {
            "cocktail":    "/static/glassware/coupe.svg",
            "martini":     "/static/glassware/martini.svg",
            "highball":    "/static/glassware/highball.svg",
            "collins":     "/static/glassware/collins.svg",
            "hurricane":   "/static/glassware/highball.svg",
            "rocks":       "/static/glassware/rocks.svg",
            "copper mug":  "/static/glassware/rocks.svg",
            "tiki":        "/static/glassware/rocks.svg",
            "flute":       "/static/glassware/flute.svg",
            "glencairn":   "/static/glassware/glencairn.svg",
            "mug":         "https://upload.wikimedia.org/wikipedia/commons/6/6b/Irish_Coffee_Glass_%28Footed%29.svg",
            "wine":        "https://upload.wikimedia.org/wikipedia/commons/4/4e/Wine_Glass_%28White%29.svg",
            "shot":        "https://upload.wikimedia.org/wikipedia/commons/a/ac/Shot_Glass_%28Standard%29.svg",
            "shooter":     "https://upload.wikimedia.org/wikipedia/commons/a/ac/Shot_Glass_%28Standard%29.svg",
            }

    if convert_to:
        recipe.convert(convert_to)

    main_tag = 'div'
    extra_kwargs = {}
    if order_link:
        main_tag = 'a'
        extra_kwargs = {"href": order_link}
    with tag(main_tag, id=recipe.name, klass="card card-body", **extra_kwargs):
        # embed glass image in name line
        name_line = []
        # attempt hack for keeping text aligned right of image when wrapping
        if fancy:
            name_line.append('<div class="clearfix" style="vertical-align:middle;">')
            name_line.append('<img src={} style="height:2.2em; float:left;">'.format(glassware.get(recipe.glass)))
        name_line.append(recipe.name)
        if display_opts.origin and 'schubar original' in recipe.origin.lower():
            name_line.append(sup('*'))
        if display_opts.prices and recipe.max_cost:
            price = util.calculate_price(recipe.max_cost, display_opts.markup)
            price = '&{};{}{}'.format('nbsp' if fancy else 'mdash', sup('$'), price)
            if fancy:
                name_line.append(close(price, 'p', style="float:right"))
            else:
                name_line.append(price)
        if fancy:
            name_line.append("</div><!-- recipe name text -->")
            name_line = close(''.join(name_line), 'h4', class_="card-title",
                style="margin-left:-0.35em; vertical-align:middle;") # tweak to the left
        else:
            name_line = close(''.join(name_line), 'h4')
        doc.asis(name_line)

        if display_opts.prep_line:
            doc.asis(small_br(recipe.prep_line(extended=True, caps=False)))

        if display_opts.info and recipe.info:
            doc.asis(small_br(em(recipe.info)))

        if condense_ingredients:
            ingredients = ', '.join([str(ingredient.specifier) for ingredient in recipe.ingredients
                    if isinstance(ingredient, QuantizedIngredient)])
            doc.asis(ingredients+'<br>')
        else:
            with tag('ul', id='ingredients'):
                for item in recipe.ingredients:
                    line('li', item.str(), type="none")

        if display_opts.variants:
            if condense_ingredients:
                # also need these to not be indented
                for variant in recipe.variants:
                    doc.asis(small(em(variant)))
            else:
                with tag('ul', id='variants'):
                    for variant in recipe.variants:
                        with tag('small'):
                            with tag('li', type="none"):
                                line('em', variant)

        if display_opts.examples and recipe.examples:# and recipe.name != 'The Cocktail':
            # special display for recipe with examples
            # TODO pull out bitters into supplimental list
            if display_opts.prices:
                for e in sorted(recipe.examples, key=lambda x: x.cost):
                    markup = 1.1+display_opts.markup if recipe.name == "A Dram" else display_opts.markup
                    fields = {
                            'cost': util.calculate_price(e.cost, markup),
                            'abv': e.abv,
                            'bottles': e.bottles
                            }
                    doc.asis(small_br("${cost:>3.0f} | {abv:.1f}% | {bottles}".format(**fields)))
            else:
                for e in recipe.examples:
                    doc.asis(small_br("${cost:.2f} | {abv:.2f}% | {std_drinks:.2f} | {bottles}".format(**e._asdict())))

    return unicode(doc.getvalue())

def as_table(objects, headings, cells, formatters, outer_div="", table_id="", table_cls="table", thead_cls="", tbody_cls=""):
    """ Generate HTML table where objects are instances of db.Models
    headings, cells, formatters are three lists of equal length,
    where headings are the table headings, cells are the attributes to put in those cells,
    and formatters are a list of formatter callables to apply to the arguments
    table_cls, thead_cls, tbody_cls are class tags to apply to those elements
    """
    doc, tag, text, line = yattag.Doc().ttl()
    with tag('div', klass=outer_div):
        with tag('table', klass=table_cls, id=table_id):
            with tag('thead', klass=thead_cls):
                with tag('tr'):
                    for heading in headings:
                        line('th', heading, scope="col")
            with tag('tbody', klass=tbody_cls):
                for obj in objects:
                    with tag('tr'):
                        for cell, formatter in zip(cells, formatters):
                            doc.asis(close(formatter(getattr(obj, cell)), 'td'))
    return unicode(doc.getvalue())

def users_as_table(users):
    headings = "ID,Email,First,Last,Nickname,Logins,Last,Confirmed,Roles,Orders".split(',')
    cells = "id,email,first_name,last_name,nickname,login_count,last_login_at,confirmed_at,get_role_names,orders".split(',')
    formatters = [str, str, str, str, str, str, str, str, lambda x: x(), len]
    return as_table(users, headings, cells, formatters, outer_div="table-responsive-sm", table_cls="table table-sm")

def yes_no(b):
    return 'yes' if b else 'no'

def orders_as_table(orders):
    headings = "ID,Timestamp,Confirmed,User ID,Bar ID,Recipe".split(',')
    cells = "id,timestamp,confirmed,user_id,bar_id,recipe_name".split(',')
    formatters = [str, str, yes_no, str, str, str]
    return as_table(orders, headings, cells, formatters, outer_div="table-responsive-sm", table_cls="table table-sm")

def bars_as_table(bars):
    headings = "ID,Name,CName,Total Orders".split(',')
    cells = "id,name,cname,orders".split(',')
    formatters = [str,str,str,len]
    return as_table(bars, headings, cells, formatters, outer_div="table-responsive-sm", table_cls="table table-sm")

def ingredients_as_table(ingredients):
    headings = "Category,Type,Bottle,In Stock,ABV,Size (oz),$,$/oz".split(',')
    cells = "Category,Type,Bottle,instock_toggle,Proof,Size_oz,Price_Paid,Cost_per_oz".split(',')
    # make cell yellow if out?
    def as_money(s):
        return '${:.2f}'.format(s)
    formatters = [
            str, str, str, lambda x: x(),
            lambda x: '{:.1f}%'.format(x/2.0),
            lambda x: '{:.1f}'.format(x), as_money, as_money]
    return as_table(ingredients, headings, cells, formatters, table_id="ingredient_table", table_cls="table table-sm")

