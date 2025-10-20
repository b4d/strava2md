PYTHON = $$(command -v python3)
OPEN = $$(command -v xdg-open) || $$(command -v open)

any:
	@echo "run \"make env\" for creating test environment"
	@echo "run \"make test\" for testing (requires ACTIVITY_ID and xdg-open)"
	
.PHONY: create_venv install_deps_in_venv env test
create_venv:
	@$(PYTHON) -m venv venv

install_deps_in_venv: 
	. venv/bin/activate && pip install -r requirements.txt

env: create_venv install_deps_in_venv

test:
ifndef ACTIVITY_ID
	$(error ACTIVITY_ID is not set)
endif
	@rm -rf Activities/*
	@. venv/bin/activate && python3 stravaapi.py -i $$ACTIVITY_ID --descrlimit -1
	@. venv/bin/activate && python3 utils/page2html.py --input Activities/*$$ACTIVITY_ID.md --output Activities/index.html 
	@DIR=$$(find Activities/* -type d); mv Activities/index.html $$DIR/index.html
	@FILE=$$(find Activities/*/index.html -type f); $(OPEN) $$FILE