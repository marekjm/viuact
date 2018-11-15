all: compile

OUTPUT_DIR=./build/_default
ASM_OUTPUT=a.asm

compile: $(OUTPUT_DIR)/$(ASM_OUTPUT)

$(OUTPUT_DIR)/$(ASM_OUTPUT):
	./scripts/cc hello_world.lisp
	../core/viuavm/build/bin/vm/asm \
		-o $(OUTPUT_DIR)/a.out \
		$(OUTPUT_DIR)/$(ASM_OUTPUT)

run: $(OUTPUT_DIR)/$(ASM_OUTPUT)
	@../core/viuavm/build/bin/vm/kernel $(OUTPUT_DIR)/a.out

clean:
	rm -rfv $(OUTPUT_DIR)/
