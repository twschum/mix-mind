from pylatex import Document, MiniPage, LineBreak, VerticalSpace
from pylatex.utils import italic, bold


def format_recipes(recipes, output_filename):
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

    for i, recipe in enumerate(recipes[:8], 1):
        with doc.create(MiniPage(width=r"0.5\textwidth")):
            doc.append(bold(recipe.name))
            doc.append("\n")
            if recipe.info:
                doc.append(italic(recipe.info))
                doc.append("\n")

            for item in recipe.ingredients:
                doc.append(item)
                doc.append("\n")

        if (i % 2) == 0:
            doc.append(VerticalSpace("30pt"))
            doc.append(LineBreak())

    doc.generate_pdf(output_filename, clean_tex=False)

