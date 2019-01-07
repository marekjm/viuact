VIUAC_DUMP_INTERMEDIATE=tokens,exprs python3 ./src/viuact-cc.py --mode exec ./shenanigans/kitchen_sink.lisp
python3 ./src/viuact-opt.py ./build/_default/kitchen_sink.asm
