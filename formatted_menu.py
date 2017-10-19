import pylatex.config
from pylatex import Document, MiniPage, LineBreak, VerticalSpace, Section, Subsection, MultiColumn
from pylatex.utils import italic, bold


def format_recipes(recipes, output_filename):

    pylatex.config.active = pylatex.config.Version1(indent=False)

    geometry_options = {"margin": "0.5in"}
    doc = Document(geometry_options=geometry_options)

    doc.change_document_style("empty")
    r'''
    \begin{document}
       \begin{center}
           \LARGE \textbf{SchuBar Menu} \\
           \small \textit{I really need a tagline} \\
           \hrulefill
       \end{center}
    '''
    with doc.create(Section('SchuBar', numbering=False)):
        cols = MultiColumn()

    with doc.create(Section('SchuBar', numbering=False)):
        for i, recipe in enumerate(recipes[:8], 1):
            with doc.create(Subsection(recipe.name, numbering=False, width=r"0.5\textwidth")):
                #doc.append(bold(recipe.name))
                #doc.append("\n")
                if recipe.info:
                    doc.append(italic(recipe.info))
                    doc.append("\n")

                for item in recipe.ingredients:
                    doc.append(item)
                    doc.append("\n")

            #if (i % 2) == 0:
                #doc.append(VerticalSpace("30pt"))
                #doc.append(LineBreak())

    doc.generate_pdf(output_filename, clean_tex=False)

