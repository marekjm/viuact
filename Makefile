PREFIX=~/.local
BIN_DIR=$(PREFIX)/bin
PYTHON_LIB_DIR=$(PREFIX)/lib/python$(shell python3 --version | grep -Po '3\.\d+')/site-packages
VIUACT_LIBS_DIR=$(PYTHON_LIB_DIR)/viuact

VIUACT_HEAD_COMMIT=$(shell git rev-parse HEAD)
VIUACT_CODE_HASH=$(shell (find ./viuact -name '*.py' | sort | xargs -n 1 cat ; \
	cat cc.py format.py front.py opt.py) | sha384sum | cut -d' ' -f1)

BUILD_DIR=./build
OUTPUT_DIR=$(BUILD_DIR)/_default
ASM_OUTPUT=a.asm

ASM_BINARY=viua-asm
KERNEL_BINARY=viua-vm

.PHONY: test

all: test

clean:
	@rm -rf $(OUTPUT_DIR)/

test:
	@mkdir -p $(BUILD_DIR)
	rm -r $(BUILD_DIR)
	python3 ./tests.py --all

install:
	@mkdir -p $(BIN_DIR)
	@mkdir -p $(VIUACT_LIBS_DIR)
	cp ./viuact/*.py $(VIUACT_LIBS_DIR)/
	@sed -i "s/'HEAD'/'$(VIUACT_HEAD_COMMIT)'/" $(VIUACT_LIBS_DIR)/__init__.py
	@sed -i "s/__code__ = 'CODE'/__code__ = '$(VIUACT_CODE_HASH)'/" $(VIUACT_LIBS_DIR)/__init__.py
	cp ./cc.py $(BIN_DIR)/viuact-cc
	cp ./opt.py $(BIN_DIR)/viuact-opt
	cp ./format.py $(BIN_DIR)/viuact-format
	cp ./front.py $(BIN_DIR)/viuact
	chmod +x \
		$(BIN_DIR)/viuact-cc \
		$(BIN_DIR)/viuact-opt \
		$(BIN_DIR)/viuact-format \
		$(BIN_DIR)/viuact
	@mkdir -p ~/.local/lib/viuact
	cp -Rv ./stdlib/Std/* ~/.local/lib/viuact/Std
	@mkdir -p ~/.local/share/viuact/switch/init/
	cp -Rv switch/init/* ~/.local/share/viuact/switch/init/

watch-test:
	find . -name '*.py' | entr -c make test

watch-install:
	( \
		find . -name '*.py' ; \
		find ./stdlib -name '*.i' ; \
		find ./switch -type f \
	) | entr -cs \
		"make install && dd if=/dev/urandom count=512 2>/dev/null | sha384sum"

pipeline.png: pipeline.dot
	dot -Tpng pipeline.dot > pipeline.png
