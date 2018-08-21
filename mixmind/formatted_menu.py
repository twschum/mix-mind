import pylatex.config
from pylatex.base_classes import Environment, CommandBase, Arguments, Options
from pylatex.package import Package
from pylatex import Document, Command, Section, Subsection, Subsubsection, MiniPage, \
        LineBreak, VerticalSpace, HorizontalSpace, Head, Foot, PageStyle, Center, Itemize, HFill, \
        FlushRight, FlushLeft, NewPage, \
        FootnoteText, SmallText, MediumText, LargeText, HugeText
from pylatex.utils import italic, bold, NoEscape
import yattag
import time

from recipe import QuantizedIngredient
import util

class TitleText(HugeText):
    _latex_name = 'LARGE'

class ParacolEnvironment(Environment):
    _latex_name = 'paracol'
    packages = [Package('paracol')]
class SloppyParacolsEnvironment(Environment):
    _latex_name = 'sloppypar'
def add_paracols_environment(doc, ncols, columnsep, sloppy=True):
    doc.append(Command('setlength', NoEscape('\columnsep'), extra_arguments=Arguments(columnsep)))
    paracols = ParacolEnvironment(arguments=Arguments(ncols))
    if sloppy:
        sloppy = SloppyParacolsEnvironment()
        doc.append(sloppy)
    doc.append(paracols)
    return paracols

class HRuleFill(CommandBase):
    _latex_name = 'hrulefill'

class DotFill(CommandBase):
    _latex_name = 'dotfill'

class SamepageEnvironment(Environment):
    _latex_name = 'samepage'

class SwitchColumn(CommandBase):
    # starred for synchronization
    _latex_name = 'switchcolumn*'

class Superscript(CommandBase):
    _latex_name = 'textsuperscript'
def superscript(item):
    return Superscript(arguments=item)


def append_liquor_list(doc, df, own_page):
    # TODO no interaction with dataframe?
    bottles = df[df.Category.isin(['Spirit', 'Vermouth', 'Liqueur'])][['Bottle', 'Type']]
    if own_page:
        print "Appending list as new page"
        doc.append(NewPage())
    listing = SamepageEnvironment()
    block = Center()
    if not own_page:
        block.append(HRuleFill())
        block.append(Command('\\'))
    block.append(VerticalSpace('16pt'))
    block.append(TitleText("Included Ingredients"))
    block.append(Command('\\'))
    listing.append(block)
    listing.append(VerticalSpace('12pt'))

    cols = add_paracols_environment(listing, 2, '8pt', sloppy=False)
    with cols.create(FlushRight()):
        for item in bottles.Bottle:
            cols.append(LargeText(item))
            cols.append(Command('\\'))
    cols.append(Command('switchcolumn'))
    with cols.create(FlushLeft()):
        for item in bottles.Type:
            cols.append(LargeText(italic(item)))
            cols.append(Command('\\'))

    doc.append(listing)


def format_recipe(recipe, display_opts):
    """ Return the recipe in a paragraph in a samepage
    """
    recipe_page = SamepageEnvironment()
    name_line = LargeText(recipe.name)

    if display_opts.origin and 'schubar original' in recipe.origin.lower():
        name_line.append(superscript('*'))
        #name_line.append(superscript(NoEscape('\dag')))

    if display_opts.prices and recipe.max_cost:
        price = util.calculate_price(recipe.max_cost, display_opts.markup)
        name_line.append(DotFill())
        name_line.append(superscript('$'))
        name_line.append(price)
    name_line.append('\n')
    recipe_page.append(name_line)

    if display_opts.prep_line:
        recipe_page.append(FootnoteText(recipe.prep_line(extended=True, caps=False)+'\n'))

    if display_opts.info and recipe.info:
        recipe_page.append(SmallText(italic(recipe.info +'\n')))
    for item in recipe.ingredients:
        recipe_page.append(item.str() +'\n')

    if display_opts.variants:
        for variant in recipe.variants:
            recipe_page.append(HorizontalSpace('8pt'))
            recipe_page.append(SmallText(italic(variant +'\n')))

    if display_opts.examples and recipe.examples:# and recipe.name != 'The Cocktail':
        for e in recipe.examples:
            recipe_page.append(FootnoteText("${cost:.2f} | {abv:.2f}% | {std_drinks:.2f} | {bottles}\n".format(**e._asdict())))

    recipe_page.append(Command('par'))
    return recipe_page

def format_recipe_html(recipe, display_opts, order_link=None, condense_ingredients=False):
    """ use yattag lib to build an html blob contained in a div for the recipe"""
    doc, tag, text, line = yattag.Doc().ttl()

    def close(s, tag, **kwargs):
        kwargs = ' '.join(['{}={}'.format(k, v) for k, v in kwargs.iteritems()])
        return '<{0} {2}>{1}</{0}>'.format(tag, s, kwargs)
    def em(s, **kwargs):
        return close(s, 'em', **kwargs)
    def small(s, **kwargs):
        return close(s, 'small', **kwargs)
    def sup(s, **kwargs):
        return close(s, 'sup', **kwargs)
    def small_br(s, **kwargs):
        return small(s+'<br>', **kwargs)
    def wrap_link(link, s, **kwargs):
        return '<a href={}>{}</a>'.format(link, s, **kwargs)

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

    with tag('div', id=recipe.name, klass="card-body"):
        # embed glass image in name line
        name_line = []
        # attempt hack for keeping text aligned right of image when wrapping
        name_line.append('<div class="clearfix" style="vertical-align:middle;">')
        name_line.append('<img src={} style="height:2.2em; float:left;">'.format(glassware.get(recipe.glass)))
        # link to order includes name and image
        name_line.append(recipe.name)
        if order_link:
            name_line = [wrap_link(order_link, ''.join(name_line))]
        if display_opts.origin and 'schubar original' in recipe.origin.lower():
            name_line.append(sup('*'))
        if display_opts.prices and recipe.max_cost:
            price = util.calculate_price(recipe.max_cost, display_opts.markup)
            price = '&nbsp;{}{}'.format(sup('$'), price)
            name_line.append(close(price, 'p', style="float:right"))
        name_line.append("</div><!-- recipe name text -->")
        name_line = close(''.join(name_line), 'h4',
            **{"class": "card-title",
            "style": "margin-left:-0.35em; vertical-align:middle;"}) # tweak to the left
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
                    markup = 0.25+display_opts.markup if recipe.name == "A Dram" else display_opts.markup
                    fields = {
                            'cost': util.calculate_price(e.cost, markup),
                            'abv': e.abv,
                            'bottles': e.bottles
                            }
                    doc.asis(small_br("${cost:>3.0f} | {abv:.1f}% | {bottles}".format(**fields)))
            else:
                for e in recipe.examples:
                    doc.asis(small_br("${cost:.2f} | {abv:.2f}% | {std_drinks:.2f} | {bottles}".format(**e._asdict())))
            #doc.asis('<br>')

    return unicode(doc.getvalue())

def setup_header_footer(doc, pdf_opts, display_opts):
    # Header with title, tagline, page number right, date left
    # Footer with key to denote someting about drinks
    title = pdf_opts.title or '@Schubar'
    if display_opts.prices:
        tagline = 'Tips never required, always appreciated'
        tagline = pdf_opts.tagline or 'Tips for your drinks never required, always appreciated'
    else:
        tagline = 'Get Fubar at Schubar on the good stuff'
        tagline = pdf_opts.tagline or 'Get Fubar at Schubar, but, like, in a classy way'
    hf = PageStyle("schubarheaderfooter", header_thickness=0.4, footer_thickness=0.4)
    with hf.create(Head('L')):
        hf.append(TitleText(title))
        hf.append(Command('\\'))
        hf.append(FootnoteText(italic(tagline)))
    with hf.create(Head('R')):
        hf.append(FootnoteText(time.strftime("%b %d, %Y")))
    if display_opts.origin:
        with hf.create(Foot('L')):
            hf.append(superscript("*"))
            #hf.append(superscript(NoEscape("\dag")))
            hf.append(FootnoteText(r"Schubar Original"))
    with hf.create(Foot('C')):
        if display_opts.prices:
            hf.append(HorizontalSpace('12pt'))
            hf.append(FootnoteText(NoEscape(r"\$ amount shown is recommended tip, calculated from cost of ingredients")))
    with hf.create(Foot('R')):
        hf.append(FootnoteText(Command('thepage')))
    doc.preamble.append(hf)
    doc.change_document_style("schubarheaderfooter")


def generate_recipes_pdf(recipes, pdf_opts, display_opts, ingredient_df):
    """ Generate a .tex and .pef from the recipes given
    recipes is an ordered list of RecipeTuple namedtuples
    """

    print "Generating {}.tex".format(pdf_opts.pdf_filename)
    pylatex.config.active = pylatex.config.Version1(indent=False)

    # Determine some settings based on the number of cols
    if pdf_opts.ncols == 1:
        side_margin = '1.75in'
        colsep = '44pt'
    elif pdf_opts.ncols == 2:
        side_margin = '0.8in'
        colsep = '50pt'
    elif pdf_opts.ncols == 3:
        side_margin = '0.5in'
        colsep = '44pt'
    else:
        side_margin = '0.5in'
        colsep = '30pt'

    # Document setup
    doc_opts = {
        'geometry_options': {
            'showframe': pdf_opts.debug,
            'left': side_margin,
            'right': side_margin,
            'top': '0.4in',
            'bottom': '0.2in',
            'headheight': '29pt',
            'includehead': True,
            'includefoot': True,
        }
    }
    doc = Document(**doc_opts)
    doc.documentclass = Command('documentclass', options=Options('11pt', 'portrait', 'letterpaper'), arguments=Arguments('article'))

    # http://www.tug.dk/FontCatalogue/computermoderntypewriterproportional/
    doc.preamble.append(Command(r'renewcommand*\ttdefault', extra_arguments='cmvtt'))
    doc.preamble.append(Command(r'renewcommand*\familydefault', extra_arguments=NoEscape(r'\ttdefault')))

    # apply a header and footer to the document
    setup_header_footer(doc, pdf_opts, display_opts)

    # Columns setup and fill
    paracols = add_paracols_environment(doc, pdf_opts.ncols, colsep, sloppy=False)
    for i, recipe in enumerate(recipes, 1):
        paracols.append(format_recipe(recipe, display_opts))
        switch = 'switchcolumn'
        if pdf_opts.align:
            switch += '*' if (i % pdf_opts.ncols) == 0 else ''
        paracols.append(Command(switch))

    # append a page on the ingredients
    if pdf_opts.liquor_list or pdf_opts.liquor_list_own_page:
        append_liquor_list(doc, ingredient_df, own_page=pdf_opts.liquor_list_own_page)

    print "Compiling {}.pdf".format(pdf_opts.pdf_filename)
    doc.generate_pdf(pdf_opts.pdf_filename, clean_tex=False)
    print "Done"
    return True

def filename_from_options(pdf_opts, display_opts, base_name='drinks'):
    opts_tag = "{}c".format(pdf_opts.ncols)
    opts_tag += 'l' if pdf_opts.liquor_list else ''
    opts_tag += 'L' if pdf_opts.liquor_list_own_page else ''
    opts_tag += 'A' if pdf_opts.align else ''
    opts_tag += 'D' if pdf_opts.debug else ''
    opts_tag += '_'
    opts_tag += 'p{}m'.format(int(display_opts.markup)) if display_opts.prices else ''
    opts_tag += 'e' if display_opts.examples else ''
    opts_tag += 'a' if display_opts.all_ingredients else ''
    opts_tag += 'p' if display_opts.prep_line else ''
    opts_tag += 'v' if display_opts.variants else ''
    opts_tag += 'o' if display_opts.origin else ''
    return '_'.join([base_name, opts_tag])

