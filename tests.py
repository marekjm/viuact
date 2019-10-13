#!/usr/bin/env python3

import json
import os
import subprocess
import sys


TESTS = (
    'anonymous_values',
    'boolean_values',
    'closure',
    'closure_holds_state',
    'compound_expr',
    'deferred_call',
    'enum',
    'enum_in_module',
    'exceptions',
    'fibonacci',
    'fn_in_a_module',
    'function_call',
    'hello_world',
    'higher_order',
    'let_binding_of_call_result',
    'nested_fn',
    'nested_struct',
    'separate_module',
    'simple_message_exchange',
    'struct',
    'struct_field_access',
    'struct_field_update',
    'tailcall',
    'vector',
)


class Failed(Exception):
    pass


def run_test(test_name):
    HEADER_TEST = '[ test ]: {}...'.format(test_name)
    HEADER_OK   = '[  ok  ]: {}'.format(test_name)

    print(HEADER_TEST)

    make_stage = subprocess.Popen(
        args = ('bash', './ex/{}.sh'.format(test_name), 'make'),
        stdout = subprocess.PIPE,
        env = {
            **os.environ,
            'VIUAVM_ASM_COLOUR': 'always',
        },)
    make_stage_stdout, make_stage_stderr = make_stage.communicate()
    make_stage_exit = make_stage.returncode
    if make_stage_exit:
        print(make_stage_stdout.decode('utf-8'))
        raise Failed()

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
        raise Failed()

    if run_stage_stdout != expected_output:
        print(run_stage_stdout)
        raise Failed()

    print(HEADER_OK)


def main(args):
    test_run_state_path = '.tests.state'

    tests_to_run = ()
    current_test_index = 0

    if '--all' in args:
        tests_to_run = TESTS
    elif '--restart' in args:
        if os.path.isfile(test_run_state_path):
            with open(test_run_state_path, 'r') as ifstream:
                state = json.loads(ifstream.read())
                current_test_index = state['last_test']
                tests_to_run = tuple(state['tests_to_run'])
        else:
            tests_to_run = TESTS
    else:
        tests_to_run = (tuple(args) or TESTS)

    no_of_tests_to_run = len(tests_to_run)

    print('Tests to run ({}):'.format(len(tests_to_run)))
    print('\n'.join(map(lambda each: '    {}'.format(each), tests_to_run)))
    print()

    while current_test_index < no_of_tests_to_run:
        each = tests_to_run[current_test_index]
        try:
            run_test(each)
            current_test_index += 1
        except Failed as e:
            print('[ fail ]: {}'.format(each))
            print('failure on test {} of {} ({:0.2f}% passed)'.format(
                current_test_index,
                no_of_tests_to_run,
                ((current_test_index / no_of_tests_to_run) * 100.0),
            ))

            test_run_state = {
                'tests_to_run': tests_to_run,
                'last_test': current_test_index,
            }
            with open(test_run_state_path, 'w') as ofstream:
                ofstream.write(json.dumps(test_run_state))

            exit(1)

    if os.path.isfile(test_run_state_path):
        os.unlink(test_run_state_path)


main(sys.argv[1:])
