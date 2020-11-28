PYTHON_VERSION=$(shell python3 --version | grep -Po '3\.\d+')

PREFIX=~/.local
BIN_DIR=$(PREFIX)/bin
LIB_DIR=$(PREFIX)/lib
SHARE_DIR=$(PREFIX)/share

CORE_DIR=$(LIB_DIR)/viuact-core
SWITCH_TEMPLATE_DIR=$(SHARE_DIR)/viuact/switch

PYTHON_LIB_DIR=$(PREFIX)/lib/python$(PYTHON_VERSION)/site-packages

VIUACT_LIBS_DIR=$(PYTHON_LIB_DIR)/viuact

VIUACT_HEAD_COMMIT=$(shell git rev-parse HEAD)
VIUACT_CODE_HASH=$(shell (find ./viuact -name '*.py' | sort | xargs -n 1 cat ; \
	find ./tools -name '*.py' | sort | xargs -n 1 cat) | sha384sum | cut -d' ' -f1)

BUILD_DIR=./build
OUTPUT_DIR=$(BUILD_DIR)/_default

.PHONY: test

all: test

clean:
	@rm -rf $(OUTPUT_DIR)/

install:
	@mkdir -p $(BIN_DIR)
	@mkdir -p $(LIB_DIR)
	@mkdir -p $(CORE_DIR)
	@mkdir -p $(VIUACT_LIBS_DIR)
	@find . -name '__pycache__' | xargs -n 1 --no-run-if-empty rm -r
	cp -Rv ./viuact/* $(VIUACT_LIBS_DIR)/
	@sed -i "s/'HEAD'/'$(VIUACT_HEAD_COMMIT)'/" $(VIUACT_LIBS_DIR)/__init__.py
	@sed -i "s/__code__ = 'CODE'/__code__ = '$(VIUACT_CODE_HASH)'/" $(VIUACT_LIBS_DIR)/__init__.py
	cp ./tools/cc.py $(CORE_DIR)/viuact-cc
	cp ./tools/opt.py $(CORE_DIR)/viuact-opt
	cp ./tools/format.py $(CORE_DIR)/viuact-format
	cp ./tools/switch.py $(CORE_DIR)/viuact-switch
	cp ./tools/front.py $(BIN_DIR)/viuact
	@sed -i "s%DEFAULT_CORE_DIR = '.*'%DEFAULT_CORE_DIR = '$(CORE_DIR)'%" $(BIN_DIR)/viuact
	chmod +x \
		$(CORE_DIR)/viuact-cc \
		$(CORE_DIR)/viuact-opt \
		$(CORE_DIR)/viuact-format \
		$(CORE_DIR)/viuact-switch \
		$(BIN_DIR)/viuact
	# @mkdir -p $(LIB_DIR)/viuact/Std
	# cp -Rv ./stdlib/Std/* $(LIB_DIR)/viuact/Std
	@mkdir -p $(SWITCH_TEMPLATE_DIR)/init
	cp -Rv switch/init/* $(SWITCH_TEMPLATE_DIR)/init/

watch-test:
	touch trigger.test-suite
	(ls -1 test-suite.py trigger.test-suite ; find ./tests -type f) |\
		entr -cs ./run_tests.sh

watch-install:
	( \
		find . -name '*.py' ; \
		find ./stdlib -name '*.i' ; \
		find ./switch -type f \
	) | entr -cs \
		"make install && dd if=/dev/urandom count=512 2>/dev/null | sha384sum"

pipeline.png: pipeline.dot
	dot -Tpng pipeline.dot > pipeline.png
