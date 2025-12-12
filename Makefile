DOCS_SOURCE := .
DOCS_BUILD := $(DOCS_SOURCE)/_build

docs: ## Build HTML documentation (default).
	@$(MAKE) docs-html

html: docs-html

docs-html: ## Build documentation as static HTML.
	@uvx --from=sphinx --with=myst-parser sphinx-build $(DOCS_SOURCE) $(DOCS_BUILD)/html -b html -W

epub: docs-epub

docs-epub: ## Build documentation as EPUB.
	@uvx --from=sphinx --with=myst-parser sphinx-build $(DOCS_SOURCE) $(DOCS_BUILD)/epub -b epub -W

docs-open open: docs-html ## Build docs and open them in the browser.
	@uv run -m webbrowser ./_build/html/index.html

.PHONY: help
help:
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z_.-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

.DEFAULT_GOAL := help
