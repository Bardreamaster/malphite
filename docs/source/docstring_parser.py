# From https://github.com/sphinx-extensions2/sphinx-autodoc2/issues/33#issuecomment-2684177928
from docutils import nodes
from myst_parser.parsers.sphinx_ import MystParser
from sphinx.ext.napoleon import docstring


class NapoleonParser(MystParser):
    def parse(self, input_string: str, document: nodes.document) -> None:
        # Get the Sphinx configuration
        config = document.settings.env.config

        parsed_content = str(
            docstring.GoogleDocstring(
                str(docstring.NumpyDocstring(input_string, config)),
                config,
            )
        )
        return super().parse(parsed_content, document)


Parser = NapoleonParser
