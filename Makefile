all: compile

BUILD_DIR=./build
OUTPUT_DIR=$(BUILD_DIR)/_default
ASM_OUTPUT=a.asm

.PHONY: test

compile: $(OUTPUT_DIR)/$(ASM_OUTPUT)

$(OUTPUT_DIR)/$(ASM_OUTPUT): hello_world.lisp
	./scripts/cc hello_world.lisp
	../core/viuavm/build/bin/vm/asm \
		-o $(OUTPUT_DIR)/a.out \
		$(OUTPUT_DIR)/$(ASM_OUTPUT)

run: $(OUTPUT_DIR)/$(ASM_OUTPUT)
	../core/viuavm/build/bin/vm/kernel $(OUTPUT_DIR)/a.out

clean:
	@rm -rf $(OUTPUT_DIR)/

test:
	@mkdir -p $(BUILD_DIR)
	rm -r $(BUILD_DIR)
	python3 ./tests.py --all
