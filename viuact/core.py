import enum
import os

import viuact.util.log
import viuact.forms


EXEC_MODULE = '<main>'


class Module_info:
    def __init__(self, name, source_file):
        self._name = name
        self._source_file = source_file

        self._functions = {}

    def name(self):
        return self._name

    def make_fn(self, name, parameters):
        n = '{}/{}'.format(name, len(parameters))
        self._functions[n] = {
            'local': True,
            'from': (None, None,),
            'parameters': parameters,
        }
        print('module info [{}]: visible local fn {}'.format(
            self._name,
            n,
        ))
        return self


class Register_set(enum.Enum):
    LOCAL = 'local'
    PARAMETERS = 'parameters'
    ARGUMENTS = 'arguments'
    VOID = 'void'
    DEFAULT = LOCAL

class Slot:
    IGNORE = '_'

    def __init__(self, name, index, register_set = Register_set.DEFAULT):
        self.name = name
        self.index = index
        self.register_set = register_set

        self._is_pointer = False

    def __eq__(self, other):
        if type(other) is not Slot:
            raise TypeError('cannot compare Slot to {}'.format(
                other.__class__.__name__))
        return ((self.index == other.index)
            and (self.register_set == other.register_set))

    @staticmethod
    def make_void():
        return Slot(
            name = Slot.IGNORE,
            index = None,
            register_set = Register_set.VOID,
        )

    @staticmethod
    def make_anonymous(index, register_set = Register_set.DEFAULT):
        return Slot(
            name = None,
            index = index,
            register_set = register_set,
        )

    def is_void(self):
        return (self.register_set == Register_set.VOID)

    def is_anonymous(self):
        return (self.name is None)

    def is_pointer(self):
        return self._is_pointer

    def as_pointer(self, pointer = True):
        s = Slot(self.name, self.index, self.register_set)
        s._is_pointer = pointer
        return s

    def to_string(self):
        if self.is_void():
            return 'void'
        return '{}{} {}'.format(
            ('*' if self.is_pointer() else '%'),
            self.index,
            self.register_set.value,
        )

class State:
    def __init__(self, upper = None):
        self._upper = upper


def cc_fn(mod, fn):
    print('cc.fn: {}::{}/{}'.format(
        mod.name(),
        fn.name(),
        len(fn.parameters()),
    ))

    st = State()

def cc(source_root, source_file, module_name, forms, output_directory):
    output_file = os.path.normpath(os.path.splitext(source_file)[0] + '.asm')

    print('cc: [{}]/{} -> {}/{}'.format(
        source_root,
        source_file[len(source_root) + 1:],
        output_directory,
        output_file,
    ))

    mod = Module_info(module_name, source_file)

    for each in forms:
        if type(each) is not viuact.forms.Fn:
            continue
        mod.make_fn(
            name = each.name(),
            parameters = each.parameters(),
        )

    function_bodies = {}

    for each in filter(lambda x: type(x) is viuact.forms.Fn, forms):
        out = cc_fn(mod, each)
        print(out)
