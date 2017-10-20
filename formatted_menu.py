import pylatex.config
from pylatex.base_classes import Environment, CommandBase, Arguments, Options
from pylatex.package import Package
from pylatex import Document, Command, Section, Subsection, Subsubsection, MiniPage, \
        LineBreak, VerticalSpace, HorizontalSpace, Head, Foot, PageStyle, Center, Itemize, HFill, \
        FlushRight, FlushLeft, NewPage, \
        FootnoteText, SmallText, MediumText, LargeText, HugeText
from pylatex.utils import italic, bold, NoEscape

import time

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


def generate_title(title, subtitle):
    titleblock = Center()
    titleblock.append(titletext(bold(title)))
    titleblock.append(command('\\'))
    titleblock.append(footnotetext(italic(subtitle)))
    titleblock.append(command('\\'))
    titleblock.append(hrulefill())
    titleblock.append('\n')
    return titleblock

def append_liquor_list(doc, df, own_page):
    if own_page:
        doc.append(NewPage())
    bottles = df[df.Category.isin(['Spirit', 'Vermouth', 'Liqueur'])][['Bottle', 'Type']]
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
            cols.append(LargeText(italic(item+'\n')))

    doc.append(listing)


def format_recipe(recipe, show_price=False, show_examples=False, markup=1):
    """ Return the recipe in a paragraph in a samepage
    """
    recipe_page = SamepageEnvironment()
    # set up drink name
    name_line = LargeText(recipe.name)
    if 'schubar original' in recipe.origin.lower():
        name_line.append(superscript(Command('dag')))
    elif 'schubar adaptation' in recipe.origin.lower():
        name_line.append(superscript(Command('ddag')))
    if show_price and recipe.max_cost:
        price = int(((recipe.max_cost+1) * markup) +1) # Addative or multiplicative markups?
        name_line.append(DotFill())
        name_line.append(superscript('$'))
        name_line.append(price)
    name_line.append('\n')
    recipe_page.append(name_line)

    if recipe.info:
        recipe_page.append(italic(recipe.info +'\n'))
    for item in recipe.ingredients:
        recipe_page.append(item +'\n')

    for variant in recipe.variants:
        recipe_page.append(HorizontalSpace('8pt'))
        recipe_page.append(italic(variant +'\n')) # TODO real indenting

    if show_examples and recipe.examples and recipe.name != 'The Cocktail':
        for e in recipe.examples:
            recipe_page.append(FootnoteText("${cost:.2f} | {bottles}\n".format(**e)))

    recipe_page.append(Command('par'))
    return recipe_page


def generate_recipes_pdf(recipes, output_filename, ncols, align_names=True, debug=False, prices=False, markup=False, examples=False, liquor_df=None):
    """ Generate a .tex and .pef from the recipes given
    recipes is an ordered list of RecipeTuple namedtuples
    """

    print "Generating {}.tex".format(output_filename)
    pylatex.config.active = pylatex.config.Version1(indent=False)

    # Determine some settings based on the number of cols
    if ncols == 1:
        side_margin = '2.0in'
        colsep = '44pt'
    elif ncols == 2:
        side_margin = '1.0in'
        colsep = '50pt'
    elif ncols == 3:
        side_margin = '0.5in'
        colsep = '44pt'
    else:
        side_margin = '0.5in'
        colsep = '30pt'

    # Document setup
    doc_opts = {
        'geometry_options': {
            'top': '1.0in',
            'bottom': '0.75in',
            'left': side_margin,
            'right': side_margin,
            'showframe': debug,
        }
    }
    doc = Document(**doc_opts)
    doc.documentclass = Command('documentclass', options=Options('11pt', 'portrait', 'letterpaper'), arguments=Arguments('article'))

    # http://www.tug.dk/FontCatalogue/computermoderntypewriterproportional/
    doc.preamble.append(Command(r'renewcommand*\ttdefault', extra_arguments='cmvtt'))
    doc.preamble.append(Command(r'renewcommand*\familydefault', extra_arguments=NoEscape(r'\ttdefault')))

    # Header with title, tagline, page number right, date left
    # Footer with key to denote someting about drinks
    title = '@Schubar'
    tagline = 'Get Fubar at Schubar, but, like, in a classy way'
    tagline = 'Get Fubar at Schubar on the good stuff'
    hf = PageStyle("schubarheaderfooter", header_thickness=0.4, footer_thickness=0.4)
    with hf.create(Head('L')):
        hf.append(TitleText(title))
        hf.append(Command('\\'))
        hf.append(FootnoteText(italic(tagline)))
    with hf.create(Foot('R')):
        hf.append(FootnoteText(Command('thepage')))
    with hf.create(Head('R')):
        hf.append(FootnoteText(time.strftime("%b %d, %Y")))
    with hf.create(Foot('C')):
        hf.append(NoEscape(r"\dag Schubar Original,  \ddag Schubar Adaptation"))#,  *bla, bla raw eggs"))
    doc.preamble.append(hf)
    doc.change_document_style("schubarheaderfooter")

    # Columns setup and fill
    doc.append(VerticalSpace('0pt'))
    paracols = add_paracols_environment(doc, ncols, colsep, sloppy=False)
    for i, recipe in enumerate(recipes, 1):
        paracols.append(format_recipe(recipe, show_price=prices, show_examples=examples, markup=markup))
        switch = 'switchcolumn'
        if align_names:
            switch += '*' if (i % ncols) == 0 else ''
        paracols.append(Command(switch))

    # TODO dont this
    append_liquor_list(doc, liquor_df, own_page=False)

    print "Compiling {}.pdf".format(output_filename)
    doc.generate_pdf(output_filename, clean_tex=False)
    print "Done"
