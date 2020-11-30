#!/usr/bin/env python3

import os
import re
import subprocess
import sys

from viuact.util.colors import (colorise, colorise_wrap,)


# import colored
# for each in colored.colors.names:
#     print(colored.fg(each.lower()) + each + colored.attr('reset'))
# exit(0)
COLOR_DEFAULT_HIGHLIGHT = 'white'
COLOR_TEST_COUNTER = 'green_yellow'
COLOR_OK = 'green'
COLOR_FAIL = 'red'
COLOR_MEH = 'chartreuse_1'


class Test_error(Exception):
    pass
class Missing_check_file(Test_error):
    pass
class Compilation_failed(Test_error):
    pass
class Assembly_failed(Test_error):
    pass
class Execution_failed(Test_error):
    pass
class Check_failed(Test_error):
    pass


def detect_test_kind(test_source_path):
    base, _ = os.path.splitext(test_source_path)

    test_kinds = (
        'txt',  # Check output of running program.
        'asm',  # Check output of the compiler.
    )

    for kind in test_kinds:
        check_file = '{}.{}'.format(base, kind)
        if os.path.isfile(check_file):
            return (kind, check_file,)

    return (None, None,)

def run_test_case(test_case, test_counter, pad_test_counter, verbose):
    kind, check_file = detect_test_kind(test_case)
    if kind is None:
        print('{}: {} (no check file: .txt, .asm, etc.)'.format(
            colorise(COLOR_FAIL, 'aborted'),
            colorise(COLOR_DEFAULT_HIGHLIGHT, test_case),
        ))
        raise Missing_check_file()

    print('  case  {}: {}'.format(
        colorise(COLOR_TEST_COUNTER, pad_test_counter(test_counter + 1)),
        colorise(COLOR_DEFAULT_HIGHLIGHT, test_case),
    ), end='')

    compilation = subprocess.Popen(
        args = ('viuact', 'cc', test_case,),
        stdout = subprocess.DEVNULL,
        stderr = subprocess.PIPE,
    )
    (_, stderr,) = compilation.communicate()
    result = compilation.wait()
    if result != 0:
        if verbose:
            print()
            print('  check file: {}'.format(colorise(COLOR_DEFAULT_HIGHLIGHT, check_file)))
            print('  status:     {}'.format(colorise(COLOR_FAIL, 'fail')))
            print('  reason:     compilation failed')
        else:
            print(' [{}: compilation failed]'.format(colorise(COLOR_FAIL, 'fail')))

        print('------------------ 8< -------------------')
        print(stderr.decode('utf-8'), end='')
        print('------------------ >8 -------------------')

        raise Compilation_failed()

    built_file = os.path.join('build', '_default',
            os.path.splitext(os.path.split(test_case)[1])[0])

    ok = True
    asm_file = '{}.asm'.format(built_file)
    assembly = subprocess.Popen(
        args = ('viuact', 'opt', asm_file,),
        stdout = subprocess.DEVNULL,
        stderr = subprocess.PIPE,
    )
    (_, stderr,) = assembly.communicate()
    result = assembly.wait()
    if result != 0:
        if verbose:
            print()
            print('  check file: {}'.format(colorise(COLOR_DEFAULT_HIGHLIGHT, check_file)))
            print('  status:     {}'.format(colorise(COLOR_FAIL, 'fail')))
            print('  reason:     assembly failed')
        else:
            print(' [{}: assembly failed]'.format(colorise(COLOR_FAIL, 'fail')))

        print('------------------ 8< -------------------')
        print(stderr.decode('utf-8'), end='')
        print('------------------ >8 -------------------')

        raise Assembly_failed()

    bc_file = '{}.bc'.format(built_file)
    run = subprocess.Popen(
        args = ('viua-vm', bc_file,),
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
    )
    (stdout, stderr,) = run.communicate()
    result = run.wait()
    if result != 0:
        if verbose:
            print()
            print('  check file: {}'.format(colorise(COLOR_DEFAULT_HIGHLIGHT, check_file)))
            print('  status:     {}'.format(colorise(COLOR_FAIL, 'fail')))
            print('  reason:     execution failed')
        else:
            print(' [{}: execution failed]'.format(colorise(COLOR_FAIL, 'fail')))

        print('------------------ 8< (stderr) ----------')
        print(stderr.decode('utf-8'), end='')
        print('------------------ 8= (stdout) ----------')
        print(stdout.decode('utf-8'), end='')
        print('------------------ >8 -------------------')

        raise Execution_failed()

    if kind == 'txt':
        expected = ''
        with open(check_file, 'r') as ifstream:
            expected = ifstream.read()
        actual = stdout.decode('utf-8')

        if expected != actual:
            if verbose:
                print()
                print('  check file: {}'.format(colorise(COLOR_DEFAULT_HIGHLIGHT, check_file)))
                print('  status:     {}'.format(colorise(COLOR_FAIL, 'fail')))
                print('  reason:     output failed')
            else:
                print(' [{}: output failed]'.format(colorise(COLOR_FAIL, 'fail')))

            print('------------------ 8< (expected) --------')
            print(expected, end='')
            print('------------------ 8= (actual) ----------')
            print(actual, end='')
            print('------------------ >8 -------------------')

            raise Check_failed()

    print(' [ {} ]'.format(colorise(COLOR_OK, 'ok')))
    if verbose:
        print('  cc  [{}] to {}'.format(
            colorise(COLOR_OK, 'ok'),
            asm_file,
        ))
        print('  asm [{}] to {}'.format(
            colorise(COLOR_OK, 'ok'),
            bc_file,
        ))

def main(args):
    tests_to_run = list(map(lambda _: _.strip(), sys.stdin.readlines()))
    test_name_pad = max(map(lambda _: len(_), tests_to_run))

    fail_fast = True
    verbose = False

    suite_result = 0

    test_counter_padding = len(str(len(tests_to_run)))
    pad_test_counter = lambda n: '{{:{}}}'.format(test_counter_padding).format(n)

    print('running {} test(s)...'.format(colorise(COLOR_DEFAULT_HIGHLIGHT, len(tests_to_run))))

    test_counter = 0
    test_ok_counter = 0
    for test_case in tests_to_run:
        try:
            run_test_case(test_case, test_counter, pad_test_counter, verbose)
            test_ok_counter += 1
        except Missing_check_file:
            suite_result = 2
            break
        except (Compilation_failed, Assembly_failed, Execution_failed,
                Check_failed,):
            suite_result = 1
            if fail_fast:
                break

        test_counter += 1

    success_rate = ((test_ok_counter / len(tests_to_run)) * 100.0)
    print('result: {} test(s) finished, {}% success rate'.format(
        colorise(COLOR_MEH, pad_test_counter(test_counter)),
        colorise(
            (COLOR_OK if success_rate >= 100 else COLOR_FAIL),
            '{:5.2f}'.format(success_rate),
        ),
    ))

    return suite_result

exit(main(sys.argv[1:]))
