import pylatex.config
from pylatex.base_classes import Environment, CommandBase, Arguments
from pylatex.package import Package
from pylatex import Document, MiniPage, LineBreak, VerticalSpace, Section, Subsection, MultiColumn, Command, Center
from pylatex.utils import italic, bold

class TitleEnvironment(Environment):
    _latex_name = 'center'

class ParacolEnvironment(Environment):
    _latex_name = 'paracol'
    packages = [Package('paracol')]

class SwitchColumn(CommandBase):
    _latex_name = 'switchcolumn'


def generate_title(title, subtitle):
    titleblock = Center()
    titleblock.append(Command('LARGE'))
    titleblock.append(bold(title))
    titleblock.append(Command('\\'))
    titleblock.append(Command('small'))
    titleblock.append(italic(subtitle))
    titleblock.append(Command('\\'))
    titleblock.append(Command('hrulefill'))
    return titleblock


def add_to_column(paracols, recipes):
    for recipe in recipes:
        #with doc.create(Subsection(recipe.name, numbering=False, width=r"0.5\textwidth")):
        paracols.append(bold(recipe.name +'\n'))
        if recipe.info:
            paracols.append(italic(recipe.info +'\n'))
        for item in recipe.ingredients:
            paracols.append(item +'\n')
        paracols.append('\n')

def generate_recipes_pdf(recipes, output_filename):

    print "Generating {}.tex".format(output_filename)
    pylatex.config.active = pylatex.config.Version1(indent=False)
    geometry_options = {"margin": "0.5in"}
    doc = Document(geometry_options=geometry_options)
    doc.change_document_style("empty")

    doc.append(generate_title('SchuBar', 'I really need a tagline'))

    ncols = 3
    paracols = ParacolEnvironment(arguments=Arguments(ncols))
    add_to_column(paracols, recipes[::ncols])
    paracols.append(SwitchColumn())
    add_to_column(paracols, recipes[1::ncols])
    paracols.append(SwitchColumn())
    add_to_column(paracols, recipes[2::ncols])
    doc.append(paracols)

    print "Compiling {}.pdf".format(output_filename)
    doc.generate_pdf(output_filename, clean_tex=False)
    print "Done"

