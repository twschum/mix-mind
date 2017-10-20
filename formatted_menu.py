import pylatex.config
from pylatex.base_classes import Environment, CommandBase, Arguments, Options
from pylatex.package import Package
from pylatex import Document, Command, Section, Subsection, Subsubsection, MiniPage, \
        LineBreak, VerticalSpace, Head, Foot, PageStyle, Center, \
        FootnoteText, SmallText, MediumText, LargeText, HugeText
from pylatex.utils import italic, bold, NoEscape


class TitleText(HugeText):
    _latex_name = 'LARGE'

class ParacolEnvironment(Environment):
    _latex_name = 'paracol'
    packages = [Package('paracol')]
class SloppyParacolsEnvironment(Environment):
    _latex_name = 'sloppypar'
def add_paracols_environment(doc, ncols):
    sloppy = SloppyParacolsEnvironment()
    paracols = ParacolEnvironment(arguments=Arguments(ncols))
    doc.append(sloppy)
    doc.append(paracols)
    return paracols


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
    titleblock.append(Command('LARGE'))
    titleblock.append(bold(title))
    titleblock.append(Command('\\'))
    titleblock.append(Command('small'))
    titleblock.append(italic(subtitle))
    titleblock.append(Command('\\'))
    titleblock.append(Command('hrulefill'))
    titleblock.append('\n')
    return titleblock


def add_to_column(paracols, recipes):
    for recipe in recipes:
        paracols.append(format_recipe(recipe))


def format_recipe(recipe):
    """ Return the recipe in a paragraph in a samepage
    """
    recipe_page = SamepageEnvironment()
    # set up drink name
    name_line = LargeText(recipe.name)
    if 'schubar original' in recipe.origin.lower():
        name_line.append(superscript(Command('dag')))
    elif 'schubar adaptation' in recipe.origin.lower():
        name_line.append(superscript(Command('ddag')))
    name_line.append('\n')
    recipe_page.append(name_line)

    if recipe.info:
        #paracols.append(Command('sloppy'))
        recipe_page.append(italic(recipe.info +'\n'))
    for item in recipe.ingredients:
        recipe_page.append(item +'\n')
    recipe_page.append(Command('par'))
    return recipe_page


def generate_recipes_pdf(recipes, output_filename, ncols, align_names=True):
    """ Generate a .tex and .pef from the recipes given
    recipes is an ordered list of RecipeTuple namedtuples
    """

    print "Generating {}.tex".format(output_filename)
    pylatex.config.active = pylatex.config.Version1(indent=False)

    # Determine some settings based on the number of cols
    if ncols == 2:
        side_margin = '1.0in'
        colsep = '80pt'
    elif ncols == 3:
        side_margin = '0.5in'
        colsep = '44pt'

    # Document setup
    doc_opts = {
        'geometry_options': {
            'top': '1.0in',
            'bottom': '1.0in',
            'left': side_margin,
            'right': side_margin,
        }
    }
    doc = Document(**doc_opts)
    doc.documentclass = Command('documentclass', options=Options('11pt', 'portrait', 'letterpaper'), arguments=Arguments('article'))

    # http://www.tug.dk/FontCatalogue/computermoderntypewriterproportional/
    doc.preamble.append(Command(r'renewcommand*\ttdefault', extra_arguments='cmvtt'))
    doc.preamble.append(Command(r'renewcommand*\familydefault', extra_arguments=NoEscape(r'\ttdefault')))

    hf = PageStyle("schubarheaderfooter", header_thickness=0.5, footer_thickness=0.5)
    with hf.create(Head('L')):
        #hf.append(Command('\\'))
        hf.append(TitleText('@Schubar'))
        hf.append('\n')
        hf.append(FootnoteText(italic('I really need a tagline')))
    with hf.create(Foot('C')):
        hf.append(NoEscape(r"\dag Schubar Original,  \ddag Schubar Adaptation"))
    doc.preamble.append(hf)
    doc.change_document_style("schubarheaderfooter")

    #doc.append(generate_title('@Schubar', 'I really need a tagline'))

    doc.append(Command('setlength', NoEscape('\columnsep'), extra_arguments=Arguments('44pt')))
    # Columns setup and fill
    paracols = add_paracols_environment(doc, ncols)
    for i, recipe in enumerate(recipes, 1):
        paracols.append(format_recipe(recipe))
        switch = 'switchcolumn'
        if align_names:
            switch += '*' if (i % ncols) == 0 else ''
        paracols.append(Command(switch))

    print "Compiling {}.pdf".format(output_filename)
    doc.generate_pdf(output_filename, clean_tex=False)
    print "Done"
