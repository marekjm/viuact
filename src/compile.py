#!/usr/bin/env python3

import json
import re
import sys


def group_impl(tokens):
    grouped = [tokens[0]]

    i = 1
    while i < len(tokens):
        each = tokens[i]

        if each == '(':
            g, n = group_impl(tokens[i:])
            grouped.append(g[1:-1])
            i += n

            print('gi', grouped)
            continue

        grouped.append(each)
        i += 1

        if each == ')':
            return grouped, i

    return grouped, i

def group(tokens):
    groups = []

    i = 0
    while i < len(tokens):
        each = tokens[i]

        g, n = group_impl(tokens[i:])
        print('g', g, groups)

        groups.append(g[1:-1])
        i += n

    return groups


class Token:
    def __init__(self, text):
        self._text = text

    def __str__(self):
        return self._text

    def __repr__(self):
        return repr(self._text)

    def __eq__(self, other):
        return self._text == str(other)

    def __len__(self):
        return len(self._text)


def lex(source):
    tokens = []

    def make_token(text):
        return Token(text)

    patterns = [
        re.compile('\('),
        re.compile('\)'),
        re.compile(r'\blet\b'),
        re.compile(r'\bif\b'),
        re.compile(r'\bor\b'),
        re.compile(r'\band\b'),
        re.compile(r'\bnot\b'),
        re.compile('[a-zA-Z][a-zA-Z0-9_]*'),
        re.compile('->'),
        re.compile('='),
        re.compile('"[^"]*?"'),
        re.compile('(0|-?[1-9][0-9]*)'),
        re.compile('\*'),
        re.compile('/'),
        re.compile('\+'),
        re.compile('-'),
        re.compile('<'),
        re.compile('>'),
        re.compile('<='),
        re.compile('>='),
    ]

    i = 0
    while i < len(source):
        match_found = False
        for each in patterns:
            r = re.match(each, source[i:])
            if r is not None:
                match_found = True
                tokens.append(make_token(r.group(0)))
                i += len(tokens[-1])
                break

        if match_found:
            continue

        if source[i].strip() == '':
            i += 1
            continue

        raise Exception('unexpected token', repr(source[i]))

    return tokens


def main(args):
    source_file = args[0]
    source_code = None
    with open(source_file, 'r') as ifstream:
        source_code = ifstream.read()

    tokens = lex(source_code)
    print(tokens)

    groups = group(tokens)
    print(len(groups))
    def encode_groups(obj):
        if isinstance(obj, Token):
            return str(obj)
        raise TypeError(f'Object of type {obj.__class__.__name__} '
                        f'is not JSON serializable')
    print(json.dumps(groups, indent=2, default=encode_groups))

main(sys.argv[1:])
