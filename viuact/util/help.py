import os
import re
import sys

try:
    import colored
except ImportError:
    colored = None

import viuact.util.colors


FG = re.compile(r'%fg\(([a-z][a-z_]+(?:_[1-4][ab]?)?)\)')
ATTR_RESET = re.compile(r'%r\b')
ARG = re.compile(r'%arg\(([a-z]+(?:[-_][a-z]+)*)\)')
ARG_NO_COLOR = re.compile(r'%a\(([a-z]+(?:[-_][a-z]+)*)\)')
OPT = re.compile(r'%opt\((--[a-z][a-z0-9]+|-[a-z0-9])\)')
TEXT = '%text'
COPYRIGHT = re.compile(r'%copyright\((\d+(?:-\d+)?(?:, \d+(?:-\d+)?)*)\)')

# Set this to 0 to allow stretching to actual terminal width.
MAX_COLUMN_COUNT = 0


colorise = viuact.util.colors.colorise

def clear(s):
    s = re.sub(FG, '', s)
    s = re.sub(ATTR_RESET, '', s)
    s = re.sub(ARG, lambda m: '<{}>'.format(m.group(1)), s)
    s = re.sub(ARG_NO_COLOR, lambda m: '<{}>'.format(m.group(1)), s)
    s = re.sub(OPT, lambda m: '{}'.format(m.group(1)), s)
    s = re.sub(COPYRIGHT, lambda m: 'Copyright © {}'.format(m.group(1)), s)
    return s

def reflow(text, column_count):
    output_lines = []

    def gather_paragraph(source_lines, start):
        paragraph = []

        n = 0
        while (start + n) < len(source_lines):
            line = source_lines[start + n]
            if not line.strip():
                break

            paragraph.append(line)
            n += 1

        def reflow_paragraph(input_lines):
            indent = (len(input_lines[0]) - len(input_lines[0].lstrip()))

            words = ' '.join(map(str.strip, input_lines)).split()

            output_lines = []
            i = 0
            while i < len(words):
                line = []
                line_length = (indent - 1)

                while i < len(words):
                    next_word = words[i]

                    printed_word = clear(next_word)

                    next_line_length = (line_length + 1 + len(printed_word))
                    if (next_line_length < column_count) or not line:
                        line.append(next_word)
                        line_length = next_line_length
                        i += 1
                    else:
                        break
                output_lines.append(line)

            def strech_line(words, indent):
                base = '{}{}'.format((' ' * indent), ' '.join(words))

                base_clear = clear(base)

                if len(base) == column_count:
                    return base

                extra_spaces = (column_count - len(base_clear))
                if extra_spaces > len(words):
                    return base

                indent = (' ' * indent)
                streched = '  '.join(words[:extra_spaces + 1])
                normal =  ' '.join(words[extra_spaces + 1:])

                line = '{}{} {}'.format(indent, streched, normal)

                return line

            return list(map(
                lambda each: strech_line(each, indent), output_lines))

        paragraph = reflow_paragraph(paragraph)

        return (n, paragraph)

    source_lines = text.split('\n')
    i = 0
    while i < len(source_lines):
        line = source_lines[i]
        i += 1

        if line.strip() == TEXT:
            n, paragraph = gather_paragraph(source_lines, i)

            output_lines.extend(paragraph)
            i += n

            continue

        output_lines.append(line)

    return '\n'.join(output_lines)

def print_help(executable, suite, version, text, stream = None, column_count = None):
    stream = (stream if stream is not None else sys.stdout)

    COLUMN_COUNT = (
        column_count
        if column_count is not None else
        (int(os.popen('stty size', 'r').read().split()[1]) - 2)
    )
    if MAX_COLUMN_COUNT:
        COLUMN_COUNT = min((MAX_COLUMN_COUNT, COLUMN_COUNT,))

    man_title = 'Viuact Manual'
    man_executable = '{}(1)'.format(executable.upper())

    man_padding_left = ((COLUMN_COUNT - len(man_title)) // 2)
    man_padding_left -= len(man_executable)

    man_padding_right = COLUMN_COUNT
    man_padding_right -= len(man_title)
    man_padding_right -= man_padding_left
    man_padding_right -= (2 * len(man_executable))

    bottom_padding = (COLUMN_COUNT - 1)
    bottom_padding -= len(suite)
    bottom_padding -= len(version)
    bottom_padding -= len(man_executable)

    MAN_SECTION_COLOR = 'light_red'
    # MAN_CONST_COLOR = 'orange_red_1'
    # MAN_CONST_COLOR = 'red_3b'
    MAN_CONST_COLOR = 'green_3b'
    MAN_VAR_COLOR = 'green_1'

    ARG_COLOR = MAN_VAR_COLOR
    OPT_COLOR = 'white'

    SOURCE_COLOR = 'white'

    text = reflow(text, COLUMN_COUNT)

    colorings = re.findall(FG, text)

    def map_color(color):
        mapped = {
            'man_se': MAN_SECTION_COLOR,
            'man_const': MAN_CONST_COLOR,
            'man_var': MAN_VAR_COLOR,

            'arg': ARG_COLOR,
            'opt': ARG_COLOR,

            'source': SOURCE_COLOR,
            'const': 'orange_red_1',

            'int': 'steel_blue_3',
            'bool': 'steel_blue_3',
            'string': 'steel_blue_3',
        }.get(color, color)
        return mapped

    for color in colorings:
        text = text.replace(
            '%fg({})'.format(color),
            (colored.fg(map_color(color)) if colored else ''))
    text = re.sub(ATTR_RESET, (colored.attr('reset') if colored else ''), text)
    text = re.sub(
        ARG, lambda m: '<{}>'.format(colorise(ARG_COLOR, m.group(1))), text)
    text = re.sub(
        ARG_NO_COLOR, lambda m: '<{}>'.format(m.group(1)), text)
    text = re.sub(
        OPT, lambda m: '{}'.format(colorise(OPT_COLOR, m.group(1))), text)
    text = re.sub(
        COPYRIGHT, lambda m: 'Copyright © {}'.format(m.group(1)), text)

    def format_help(text):
        return text.format(
            executable = executable,
            exec_tool = colorise(
                MAN_CONST_COLOR, executable.replace('-', ' ')),
            exec_blank = (' ' * len(executable)),

            man_exec = man_executable,
            man_title = man_title,
            man_pad_left = (' ' * man_padding_left),
            man_pad_right = (' ' * man_padding_right),

            cmd_ex = colorise(MAN_VAR_COLOR, 'COMMAND'),
            arg_ex = '<{}>'.format(colorise(MAN_VAR_COLOR, 'arg')),
            opt_ex = '<{}>'.format(colorise(MAN_VAR_COLOR, 'option')),

            suite = suite,
            version = version,
            bottom_pad = (' ' * bottom_padding),

            NAME = colorise(MAN_SECTION_COLOR, 'NAME'),
            SYNOPSIS = colorise(MAN_SECTION_COLOR, 'SYNOPSIS'),
            DESCRIPTION = colorise(MAN_SECTION_COLOR, 'DESCRIPTION'),
            COMMANDS = colorise(MAN_SECTION_COLOR, 'COMMANDS'),
            OPTIONS = colorise(MAN_SECTION_COLOR, 'OPTIONS'),
            TOOLS = colorise(MAN_SECTION_COLOR, 'TOOLS'),
            EXAMPLES = colorise(MAN_SECTION_COLOR, 'EXAMPLES'),
            SEE_ALSO = colorise(MAN_SECTION_COLOR, 'SEE ALSO'),
            COPYRIGHT = colorise(MAN_SECTION_COLOR, 'COPYRIGHT'),
        )

    top_line = (
        '{man_exec}{man_pad_left}{man_title}{man_pad_right}{man_exec}\n\n')
    bottom_line = (
        '\n{suite} {version}{bottom_pad}{man_exec}\n')
    stream.write(format_help(top_line))
    stream.write(format_help(text))
    stream.write(format_help(bottom_line))
