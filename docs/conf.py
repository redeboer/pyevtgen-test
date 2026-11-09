"""Configuration for the Sphinx documentation builder."""

from importlib.metadata import version as get_version

ORGANIZATION = "redeboer"
REPO_NAME = "pyevtgen-test"
PACKAGE = "pyevtgen"

author = "Common Partial Wave Analysis"
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "undoc-members": True,
}
autodoc_member_order = "bysource"
codeautolink_concat_default = True
copybutton_prompt_is_regexp = True
copybutton_prompt_text = r">>> |\.\.\. "
exclude_patterns = ["**.ipynb_checkpoints", "*build", "examples", "marimo"]
extensions = [
    "jupyterlite_sphinx",
    "myst_nb",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx_codeautolink",
    "sphinx_copybutton",
]
html_show_sourcelink = False
html_show_sphinx = False
html_theme = "sphinx_book_theme"
html_theme_options = {
    "path_to_docs": "docs",
    "repository_branch": "main",
    "repository_url": f"https://github.com/{ORGANIZATION}/{REPO_NAME}",
    "show_navbar_depth": 2,
    "show_toc_level": 2,
    "use_download_button": True,
    "use_edit_page_button": True,
    "use_issues_button": True,
    "use_repository_button": True,
}
html_title = PACKAGE
intersphinx_mapping = {
    "matplotlib": ("https://matplotlib.org/stable", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
    "python": ("https://docs.python.org/3", None),
}
jupyterlite_contents = ["examples"]
jupyterlite_silence = True
myst_enable_extensions = ["colon_fence", "dollarmath", "smartquotes"]
myst_heading_anchors = 3
nb_execution_mode = "cache"
nb_execution_raise_on_error = True
nb_execution_show_tb = True
nb_execution_timeout = -1
nb_output_stderr = "remove"
project = PACKAGE
release = get_version(PACKAGE)
version = release
