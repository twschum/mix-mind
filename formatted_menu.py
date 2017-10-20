import pylatex.config
from pylatex.base_classes import Environment, CommandBase, Arguments
from pylatex.package import Package
from pylatex import Document, MiniPage, LineBreak, VerticalSpace, Section, Subsection, MultiColumn, Command, Center, MediumText, LargeText, NoEscape, Head, Foot, PageStyle
from pylatex.utils import italic, bold, NoEscape

class TitleEnvironment(Environment):
    _latex_name = 'center'

class ParacolEnvironment(Environment):
    _latex_name = 'paracol'
    packages = [Package('paracol')]

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
    return recipe_page


def generate_recipes_pdf(recipes, output_filename):
    """ Generate a .tex and .pef from the recipes given
    recipes is an ordered list of RecipeTuple namedtuples
    """

    print "Generating {}.tex".format(output_filename)
    pylatex.config.active = pylatex.config.Version1(indent=False)


    # Document setup
    doc_opts = {
        'geometry_options':  {"margin": "0.5in"}
    }
    doc = Document(**doc_opts)
    #doc.documentclass = Command('documentclass', options=Options('10pt', 'portrait', 'letterpaper'))

    # http://www.tug.dk/FontCatalogue/computermoderntypewriterproportional/
    doc.preamble.append(Command(r'renewcommand*\ttdefault', extra_arguments='cmvtt'))
    doc.preamble.append(Command(r'renewcommand*\familydefault', extra_arguments=NoEscape(r'\ttdefault')))

    footer = PageStyle("footnotekey", footer_thickness=0.5)
    with footer.create(Foot('C')):
        footer.append(Command('dag'))
        footer.append("= a Schubar Original")
        footer.append(VerticalSpace('12pt'))
        footer.append(Command('ddag'))
        footer.append("= a Schubar Adaptation")
    doc.preamble.append(footer)
    doc.change_document_style("footnotekey")

    doc.append(generate_title('SchuBar', 'I really need a tagline'))

    # Columns setup and fill
    ncols = 3
    paracols = ParacolEnvironment(arguments=Arguments(ncols))
    paracols.append(Command('setcolumnwidth', arguments=Arguments(NoEscape(r'0.23\textwidth,0.23\textwidth,0.23\textwidth')))) # TODO this...
    for i, recipe in enumerate(recipes, 1):
        paracols.append(format_recipe(recipe))
        switch = 'switchcolumn'
        #switch += '*' if (i % ncols) == 0 else ''
        paracols.append(Command(switch))
    doc.append(paracols)

    r'''
    The paracol environment may also start with a
    spanning text by specifying it as the optional argument
    of \begin{paracol}. For example, at the
    beginning of this document, the author put;
    \begin{paracol}{2}[\section{Introduction}]
    add_to_column(paracols, recipes[::ncols])
    paracols.append(SwitchColumn())
    add_to_column(paracols, recipes[1::ncols])
    paracols.append(SwitchColumn())
    add_to_column(paracols, recipes[2::ncols])
    '''

    print "Compiling {}.pdf".format(output_filename)
    doc.generate_pdf(output_filename, clean_tex=False)
    print "Done"
