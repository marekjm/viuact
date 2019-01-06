#!/usr/bin/env python3

import os
import subprocess
import sys


TESTS = (
    'anonymous_values',
    'closure_holds_state',
    'closure',
    'compound_expr',
    'fibonacci',
    'fn_in_a_module',
    'function_call',
    'hello_world',
    'let_binding_of_call_result',
    'nested_fn',
    'separate_module',
    'struct',
    'nested_struct',
    'struct_field_access',
    'struct_field_update',
    'simple_message_exchange',
    'tailcall',
)


def run_test(test_name):
    HEADER_TEST = '[ test ]: {}...'.format(test_name)
    HEADER_OK   = '[  ok  ]: {}...'.format(test_name)
    HEADER_FAIL = '[ fail ]: {}...'.format(test_name)

    print(HEADER_TEST)

    make_stage = subprocess.Popen(
        args = ('bash', './ex/{}.sh'.format(test_name), 'make'),
        stdout = subprocess.PIPE,
        env = {
            'VIUAVM_ASM_COLOUR': 'always',
        },)
    make_stage_stdout, make_stage_stderr = make_stage.communicate()
    make_stage_exit = make_stage.returncode
    if make_stage_exit:
        print(make_stage_stdout.decode('utf-8'))
        print(HEADER_FAIL)
        exit(1)

    expected_output_file = os.path.join('.', 'ex', '{}.text'.format(test_name))
    expected_output = ''
    with open(expected_output_file, 'r') as ifstream:
        expected_output = ('running {}...\n'.format(test_name) + ifstream.read())

    run_stage = subprocess.Popen(('bash', './ex/{}.sh'.format(test_name), 'run'), stdout=subprocess.PIPE)
    run_stage_stdout, run_stage_stderr = run_stage.communicate()
    run_stage_exit = run_stage.returncode

    run_stage_stdout = run_stage_stdout.decode('utf-8')

    if run_stage_exit:
        print(run_stage_stdout)
        print(HEADER_FAIL)
        exit(1)

    if run_stage_stdout != expected_output:
        print(run_stage_stdout)
        print(HEADER_FAIL)
        exit(1)

    print(HEADER_OK)


def main(args):
    tests_to_run = ()
    if '--all' in args:
        tests_to_run = TESTS
    else:
        tests_to_run = tuple(args)

    print('Tests to run ({}):'.format(len(tests_to_run)))
    print('\n'.join(map(lambda each: '    {}'.format(each), tests_to_run)))
    print()

    for each in tests_to_run:
        try:
            run_test(each)
        except Exception as e:
            print('[ fail ]: {}'.format(each))
            raise


main(sys.argv[1:])
