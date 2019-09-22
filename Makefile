all: compile

PREFIX=~/.local
BIN_DIR=$(PREFIX)/bin
PYTHON_LIB_DIR=$(PREFIX)/lib/python$(shell python3 --version | grep -Po '3\.\d')/site-packages
VIUACT_LIBS_DIR=$(PYTHON_LIB_DIR)/viuact
VIUACT_HEAD_COMMIT=$(shell git rev-parse HEAD)

BUILD_DIR=./build
OUTPUT_DIR=$(BUILD_DIR)/_default
ASM_OUTPUT=a.asm

ASM_BINARY=../viuavm/build/bin/vm/asm
KERNEL_BINARY=../viuavm/build/bin/vm/kernel

.PHONY: test

compile: $(OUTPUT_DIR)/$(ASM_OUTPUT)

$(OUTPUT_DIR)/$(ASM_OUTPUT): hello_world.lisp
	./scripts/cc hello_world.lisp
	$(ASM_BINARY) \
		-o $(OUTPUT_DIR)/a.out \
		$(OUTPUT_DIR)/$(ASM_OUTPUT)

run: $(OUTPUT_DIR)/$(ASM_OUTPUT)
	$(KERNEL_BINARY) $(OUTPUT_DIR)/a.out

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
	cp ./cc.py $(BIN_DIR)/viuact-cc
	cp ./opt.py $(BIN_DIR)/viuact-opt
	cp ./format.py $(BIN_DIR)/viuact-format
	chmod +x $(BIN_DIR)/viuact-cc $(BIN_DIR)/viuact-opt $(BIN_DIR)/viuact-format

pipeline.png: pipeline.dot
	dot -Tpng pipeline.dot > pipeline.png
