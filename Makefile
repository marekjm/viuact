all: compile

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
