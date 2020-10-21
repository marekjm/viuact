import enum
import hashlib
import os

import viuact.util.log
import viuact.env
import viuact.forms
import viuact.typesystem.t
import viuact.typesystem.state

from viuact.emit import (emit_expr,)
from viuact.ops import (
    Register_set,
    Slot,
    Move,
    Verbatim,
)
from viuact.util.type_annotations import T, I, Alt


EXEC_MODULE = '<main>'


def typeof(value):
    return str(type(value))[8:-2]


class Module_info:
    def __init__(self, name, source_file):
        self._name = name
        self._source_file = source_file

        self._functions = {}
        self._function_signatures = {}

        self._enums = {}
        self._records = {}
        self._exceptions = {}

        self._imports = {}

    def name(self):
        return self._name

    def make_fn(self, name, parameters):
        n = '{}/{}'.format(name, len(parameters))
        if n not in self._function_signatures:
            raise viuact.errors.No_signature_for_function(
                pos = name.tok().at(),
                fn = n,
            )

        self._functions[n] = {
            'local': True,
            'from': (None, None,),  # module name, containing file
            'parameters': parameters,
            'base_name': str(name),
            'arity': len(parameters),
        }
        # viuact.util.log.print('module info [{}]: visible local fn {}'.format(
        #     self._name,
        #     n,
        # ))
        return self

    def make_fn_signature(self, name, parameters, return_type, template_parameters):
        n = '{}/{}'.format(str(name), len(parameters))
        self._function_signatures[n] = {
            'parameters': parameters,
            'base_name': str(name),
            'arity': len(parameters),
            'return': return_type,
            'template_parameters': template_parameters,
        }
        return self

    def signature(self, fn_name):
        return self._function_signatures[fn_name]

    def fns(self, local = None, imported = None):
        res = []
        for k, v in self._functions.items():
            if (local is None) or (local is True and v['local']):
                res.append((k, v,))
                continue
            if (imported is None) or (imported is True and not v['local']):
                res.append((k, v,))
                continue
        return res

    def make_enum(self, name, fields, template_parameters):
        if len(template_parameters) > 1:
            raise viuact.errors.Fail(
                name.tok().at(),
                'FIXME enums support at most one type parameter',
            )
        self._enums[str(name)] = {
            'fields': {
                str(f.name()) : {
                    'index': i,
                    'field': f,
                }
                for i, f
                in enumerate(fields)
            },
            'template_parameters': template_parameters,
        }
        return self

    def enum(self, name):
        # FIXME error checking
        return self._enums[str(name)]

    def enums(self):
        return list(self._enums.keys())

    def make_record(self, name, fields):
        self._records[str(name)] = {
            'fields': {
                str(f.name()) : f.type()
                for f
                in fields
            },
        }

    def record(self, name):
        return self._records[str(name)]

    def records(self):
        return list(self._records.keys())

    def make_exception(self, tag, value):
        self._exceptions[str(tag)] = value
        return self

    def exception(self, name):
        # FIXME error checking
        return self._exceptions[str(name)]

    def make_import(self, path):
        def find_file_impl(path, extension):
            ld_path = viuact.env.library_path().split(':')

            file_name = '{}.{}'.format(path.replace('::', '/'), extension)

            for each in ld_path:
                candidate = os.path.join(each, file_name)
                if os.path.isfile(candidate):
                    return candidate

            return None

        find_interface_file = lambda p: find_file_impl(p, 'vti')

        interface_file = find_interface_file(path)
        viuact.util.log.raw(interface_file)

        source_text = ''
        with open(interface_file, 'r') as ifstream:
            source_text = ifstream.read()

        tokens = viuact.lexer.lex(source_text)
        forms = viuact.parser.parse(tokens)
        mod = cc_impl_prepare_module(path, interface_file, forms)

        self._imports[path] = mod

        return path

    def imported(self, path):
        return self._imports[path]

class Scope:
    def __init__(self, state):
        self.state = state

    def __enter__(self):
        return self.state

    def __exit__(self, *args):
        self.state.erase()
        self.state._parent._active = True

    def exit(self, *args):
        self.__exit__(*args)

class State:
    def __init__(self, fn, upper = None, parent = None, special = 0, types =
            None):
        self._fn = fn           # Name of the function for which this state was
                                # created.
        self._special = special # General purpose counter for special events.

        self._upper = upper     # Used for closures.
        self._parent = parent   # Parent scope, e.g. for function call
                                # arguments.
        self._next_slot_index = {
            Register_set.LOCAL: 1,
        }
        self._named_slots = {}
        self._allocated_slots = []
        self._freed_slots = []
        self._cancelled_slots = []
        self._permanent_slots = set()

        self._types = (viuact.typesystem.state.State() if types is None else types)

        # State is active it represents the innermost scope of the currently
        # compiled function. Only active state may be mutated, i.e. it is an
        # error to allocate, deallocate, cancel, etc. slots in an inactive
        # state.
        self._active = True

        if parent is not None:
            for k, v in self._parent._next_slot_index.items():
                self._next_slot_index[k] = v

    def assert_active(self, wanted = True):
        if (self._active != wanted):
            raise viuact.errors.Mutation_of_inactive_state()

    def as_active(self, fn, *args, **kwargs):
        a = self._active
        self._active = True
        result = fn(self, *args, **kwargs)
        self._active = a
        return result

    def push_pressure(self, register_set):
        if self._parent is None:
            return
        n = self._next_slot_index[register_set]
        p = self._parent._next_slot_index[register_set]
        self._parent._next_slot_index[register_set] = max(n, p)
        self._parent.push_pressure(register_set)

    def push_deallocations(self):
        if self._parent is None:
            return

        self._parent._cancelled_slots.extend(self._cancelled_slots)
        self._cancelled_slots.clear()

        self._parent._freed_slots.extend(self._freed_slots)
        self._freed_slots.clear()

        self._parent.push_deallocations()

    def deallocate_slot(self, slot):
        self.assert_active()
        if slot.is_void():
            return

        try:
            if slot in self._freed_slots:
                raise viuact.errors.Double_deallocation(slot)
            if slot in self._cancelled_slots:
                raise viuact.errors.Deallocation_of_cancelled(slot)
            self._allocated_slots.remove((slot.index, slot.register_set,))
            if slot.name in self._named_slots:
                del self._named_slots[slot.name]
            self.remove_type(slot)
            self._freed_slots.append(slot)
        except ValueError:
            if self._parent:
                self._parent.as_active(State.deallocate_slot, slot)
            else:
                raise
        return self

    def deallocate_slot_if_anonymous(self, slot):
        if slot.is_anonymous():
            self.deallocate_slot(slot)
        return self

    def mark_permanent(self, slot):
        self.assert_active()
        self._permanent_slots.add(slot.to_string())

    def is_permanent(self, slot):
        return (slot.to_string() in self._permanent_slots)

    def cancel_slot(self, slot):
        self.assert_active()
        if slot.is_void():
            return self

        try:
            if slot in self._cancelled_slots:
                raise viuact.errors.Double_cancel(slot)
            if slot in self._freed_slots:
                raise viuact.errors.Cancel_of_deallocated(slot)
            if self.is_permanent(slot):
                return self
            self._allocated_slots.remove((slot.index, slot.register_set,))
            if slot.name in self._named_slots:
                del self._named_slots[slot.name]
            self._cancelled_slots.append(slot)
        except ValueError:
            if self._parent:
                self._parent.as_active(State.cancel_slot, slot)
            else:
                raise
        return self

    def find_free_slot(self, register_set):
        for each in self._cancelled_slots:
            if each.register_set == register_set:
                self._cancelled_slots.remove(each)
                return each
        for each in self._freed_slots:
            if each.register_set == register_set:
                self._freed_slots.remove(each)
                return each
        if self._parent is not None:
            return self._parent.find_free_slot(register_set)
        return None

    def insert_allocated(self, slot):
        self.assert_active()
        self._allocated_slots.append( (slot.index, slot.register_set,) )
        return self

    def allocate_slot(self, register_set):
        self.assert_active()
        found_freed = self.find_free_slot(register_set)
        i = None
        if found_freed is None:
            i = self._next_slot_index[register_set]
            self._next_slot_index[register_set] += 1
            self.push_pressure(register_set)
        else:
            i = found_freed.index
        self._allocated_slots.append( (i, register_set,) )
        return i

    def all_allocated_slots(self):
        slots = self._allocated_slots[:]
        if self._parent is not None:
            slots.extend(self._parent.all_allocated_slots())
        return slots
    def all_freed_slots(self):
        slots = self._freed_slots[:]
        if self._parent is not None:
            slots.extend(self._parent.all_freed_slots())
        return slots
    def all_cancelled_slots(self):
        slots = self._cancelled_slots[:]
        if self._parent is not None:
            slots.extend(self._parent.all_cancelled_slots())
        return slots

    def get_slot(self, name, register_set = Register_set.DEFAULT):
        self.assert_active()
        if name is not None and type(name) is not str:
            raise TypeError('cannot use {} to name a slot'.format(
                typeof(name),
            ))

        slot = Slot(
            name,
            self.allocate_slot(register_set),
            register_set,
        )

        # Use None as name to create anonymous slots.
        if name is not None:
            self._named_slots[name] = slot

        return slot

    def get_anonymous_slot(self, register_set = Register_set.DEFAULT):
        self.assert_active()

        slot = Slot(
            None,
            self.allocate_slot(register_set),
            register_set,
        )

        return slot

    def get_disposable_slot(self, register_set = Register_set.DEFAULT):
        self.assert_active()

        slot = Slot(
            None,
            self.allocate_slot(register_set),
            register_set,
        )

        return slot.as_disposable()

    def slot_of(self, name):
        try:
            return self._named_slots[name]
        except KeyError:
            if self._parent is None:
                raise
            return self._parent.slot_of(name)

    def name_slot(self, slot, name):
        x = (slot.index, slot.register_set,)
        if x not in self._allocated_slots:
            if self._parent:
                return self._parent.name_slot(slot, name)
            raise KeyError(slot.to_string())
        self._named_slots[name] = slot
        return self

    def actual_pressure(self, register_set):
        n = self._next_slot_index[register_set]
        a = self._allocated_slots
        f = list(filter(
            lambda i: i.register_set == register_set, self._freed_slots))

        a = (max(list(map(lambda x: x[0], a))) if a else None)
        f = (max(list(map(lambda x: x.index, f))) if f else None)

        if a is not None:
            a = (a + 1)
        if f is not None:
            f = (f + 1)

        # By default, use the pressure from the next slot as this is exactly the
        # number we should use in the most pessimistic case.
        pressure = n

        # However, if we have information about allocations let's just use the
        # maximum index of allocated slots. This will be more accurate and we
        # will not waste registers.
        if a is not None:
            pressure = a

        # To get an even better value for the actual pressure, let's consult the
        # deallocated registers (if any). If a register was deallocated it must
        # have been used at some point so its index should be taken into
        # account.
        #
        # BEWARE, though! Instead of blindly overwriting the pressure value we
        # should take a max() from freed and allocated indexes. It is possible
        # that the slot with the maximum index was not deallocated until the end
        # of the function.
        if f is not None:
            pressure = max(f, (a or 0))

        return max(pressure, n)

    def scoped(self):
        self._active = False
        s = State(
            fn = self.fn(),
            parent = self,
            special = self._special,
            types = self._types,
        )
        return Scope(s)

    def erase(self):
        self.assert_active()
        for each in self._allocated_slots:
            i, r = each
            self.deallocate_slot(Slot(
                name = None,
                index = i,
                register_set = r,
            ))
        self.push_deallocations()
        self._parent._special = self._special

    def fn(self):
        return self._fn

    def special(self):
        n = self._special
        self._special += 1
        return n

    def _set_type_of(self, slot, t):
        if type(slot) is not Slot:
            raise TypeError('cannot set type of non-slot {}: {}'.format(
                typeof(slot),
                slot,
            ))
        if slot.is_void():
            raise TypeError('cannot set type of void slot')
        key = slot.to_string()
        if (slot.index, slot.register_set,) not in self._allocated_slots:
            raise KeyError(slot.to_string())
        return self._types.store(key, t)

    def _get_type_of(self, slot):
        if type(slot) is not Slot:
            raise TypeError('cannot get type of non-slot {}: {}'.format(
                typeof(slot),
                slot,
            ))
        if slot.is_void():
            raise TypeError('cannot get type of void slot')
        key = slot.to_string()
        if (slot.index, slot.register_set,) not in self._allocated_slots:
            raise viuact.errors.Read_of_untyped_slot(slot)
        t = self._types.load(key)
        return t

    def type_of(self, slot, t = None):
        try:
            if t is None:
                return self._get_type_of(slot)
            else:
                return self._set_type_of(slot, t)
        except (KeyError, viuact.errors.Read_of_untyped_slot,):
            if self._parent:
                return self._parent.type_of(slot, t)
            else:
                raise

    def remove_type(self, slot):
        self.assert_active()
        if type(slot) is str:
            self._types.erase(slot)
        elif type(slot) is Slot:
            if slot.is_void():
                raise None
            key = None
            if slot.is_anonymous():
                key = slot.to_string()
            else:
                key = slot.name
            try:
                self._types.erase(key)
            except KeyError:
                # The slot has no type assigned.
                pass
        else:
            raise None

    def unify_types(self, a, b):
        return viuact.typesystem.state.unify(
            state = self._types,
            left = a,
            right = b,
        )

    def store(self, key, t):
        return self._types.store(key, t)

    def register_template_variable(self, p):
        return self._types.register_type(p)


class Fn_cc:
    def __init__(self, name):
        self.name = name
        self.body = []

    def append(self, line):
        self.body.append(line)
        return self

class CC_out:
    def __init__(self, main):
        self.main = main
        self.nested = {}


def cc_fn(mod, fn):
    viuact.util.log.debug('cc.fn: {}::{}/{}'.format(
        mod.name(),
        fn.name(),
        len(fn.parameters()),
    ))

    fn_name = '{}/{}'.format(fn.name(), len(fn.parameters()))
    main_fn_name = (
        '{}::{}'.format(mod.name(), fn_name)
        if mod.name() != EXEC_MODULE else
        fn_name)
    signature = mod.signature(fn_name)

    types = viuact.typesystem.state.State()
    blueprint = {}
    for each in signature['template_parameters']:
        t = viuact.typesystem.t.Template(each.name()[1:])
        blueprint[t] = types.register_type(t)
    st = State(fn = main_fn_name, types = types)

    main_fn = Fn_cc(main_fn_name)
    out = CC_out(main_fn)

    for i, each in enumerate(fn.parameters()):
        source = Slot.make_anonymous(i, Register_set.PARAMETERS)
        label = (
            str(each)[1:]
            if type(each) is viuact.forms.Labelled_parameter else
            str(each)
        )
        dest = st.get_slot(label)
        param = signature['parameters'][i].concretise(blueprint)
        st.type_of(dest, param)
        main_fn.append(Move.make_move(
            source = source,
            dest = dest,
        ))

    result_slot = Slot(None, 0, Register_set.LOCAL)
    st.insert_allocated(result_slot)
    st.mark_permanent(result_slot)
    try:
        result = emit_expr(
            mod = mod,
            body = main_fn,
            st = st,
            result = result_slot,
            expr = fn.body(),
        )
    except Exception:
        viuact.util.log.error('during compilation of {}'.format(main_fn_name))
        viuact.util.log.error('dumping body emitted so far')
        for each in main_fn.body:
            viuact.util.log.raw(each.to_string())
        raise
    if result != result_slot:
        main_fn.append(Move.make_move(
            dest = result_slot,
            source = result,
        ))

    try:
        return_t = signature['return'].concretise(blueprint)
        st.unify_types(return_t, st.type_of(result))
    except viuact.typesystem.state.Cannot_unify:
        raise viuact.errors.Bad_returned_type(
            (0, 0,),  # FIXME add position
            # signature['return'],
            fn_name,
            signature['return'],
            st.type_of(result),
        )
        raise 0

    try:
        # st._types.dump()
        pass
    except RecursionError:
        viuact.util.log.error(
            'a type refers to itself (check template variables dump)')
        raise viuact.errors.Fail(
            (0, 0,),
            'infinite loop encountered during type dump'
        )

    main_fn.body.insert(0, Verbatim(''))
    main_fn.body.insert(0, Verbatim('allocate_registers %{} local'.format(
        # st.static_pressure(),
        st.actual_pressure(Register_set.LOCAL),
    )))
    main_fn.append(Verbatim('return'))

    return out

def cc_type(mod, form):
    # FIXME Add checks if used types were defined before.
    # FIXME Add checks for used template parameters - if they are defined by the
    # val expression.
    if type(form) is viuact.forms.Type_name:
        name = str(form.name())

        if name[0] == "'":
            return viuact.typesystem.t.Template(
                name = name[1:],
            )
        elif name == 'void':
            return viuact.typesystem.t.Void()
        else:
            parameters = [cc_type(mod, each) for each in form.parameters()]
            return viuact.typesystem.t.Value(
                name = name,
                templates = tuple(parameters),
            )
    if type(form) is viuact.forms.Fn_type:
        return_type = cc_type(mod, form.return_type())
        parameter_types = []
        for x in form.parameter_types():
            parameter_types.append(cc_type(mod, x))

        return viuact.typesystem.t.Fn(
            rt = return_type,
            pt = tuple(parameter_types),
            templates = (),
        )
    viuact.util.log.error('cannot compile type from: {} [{}]'.format(
        str(form),
        typeof(form),
    ))
    raise viuact.errors.Internal_compiler_error()


INDENT = '    '

def signature_to_string(full_name, sig):
    tp = sig['template_parameters']
    fp = sig['parameters']
    rt = sig['return']

    fmt = '(val {name} ({fp}) -> {rt})'
    if tp:
        fmt = '(val ({tp}) {name} ({fp}) -> {rt})'

    template_parameters = ' '.join(map(lambda x: x.to_string(), tp))

    formal_parameters = ' '.join(map(lambda x: x.to_string(), fp))
    return_type = rt.to_string()

    return fmt.format(
        tp = template_parameters,
        name = full_name,
        fp = formal_parameters,
        rt = return_type,
    )

def signature_of_enum_to_string(name, sig, indent):
    fmt = '(enum {} (\n{}\n))'

    fields = []
    for f, v in sorted(sig['fields'].items(), key = lambda x: x[1]['index']):
        if v['field'].bare():
            fields.append((INDENT * (indent + 1)) + '{}'.format(f))
        else:
            fields.append((INDENT * (indent + 1)) + '({} {})'.format(f, v['field'].value()))

    return fmt.format(name, '\n'.join(fields))

def signature_of_record_to_string(name, sig, indent):
    fmt = '(type {} {{\n{}\n}})'

    fields = []
    viuact.util.log.raw(sig)
    for f, v in sig['fields'].items():
        fields.append((INDENT * (indent + 1)) + '(val {} {})'.format(
            f,
            str(v),
        ))

    return fmt.format(name, '\n'.join(fields))


def cc_impl_prepare_module(module_name, source_file, forms):
    mod = Module_info(module_name, source_file)

    for each in filter(lambda x: type(x) is viuact.forms.Import, forms):
        try:
            mod.make_import(each.path())
        except Exception:
            viuact.util.log.error('during import of {}'.format(
                viuact.util.colors.colorise_repr('white', each.path())
            ))
            raise


    for each in filter(lambda x: type(x) is viuact.forms.Enum, forms):
        mod.make_enum(
            name = each.name(),
            fields = each.fields(),
            template_parameters = [
                viuact.typesystem.t.Template(
                    name = str(t)[1:],
                )
                for t
                in each.template_parameters()
            ],
        )

    for each in filter(lambda x: type(x) is viuact.forms.Record_definition, forms):
        mod.make_record(
            name = each.tag(),
            fields = each.fields(),
        )

    for each in filter(lambda x: type(x) is viuact.forms.Exception_definition, forms):
        mod.make_exception(
            tag = each.tag(),
            value = each.value(),
        )

    for each in filter(lambda x: type(x) is viuact.forms.Val_fn_spec, forms):
        mod.make_fn_signature(
            name = each.name(),
            parameters = [cc_type(mod, t) for t in each.parameter_types()],
            return_type = cc_type(mod, each.return_type()),
            template_parameters = [
                cc_type(mod, t) for t in each.template_parameters()],
        )

    for each in forms:
        if type(each) is not viuact.forms.Fn:
            continue
        mod.make_fn(
            name = each.name(),
            parameters = each.parameters(),
        )

    return mod

def cc_impl_emit_functions(mod, forms):
    fns = []

    for each in filter(lambda x: type(x) is viuact.forms.Fn, forms):
        out = cc_fn(mod, each)
        fns.append({ 'name': out.main.name, 'out': out, 'raw': each, })

    return fns

def cc_impl_save_implementation(mod, fns, build_directory, output_file):
    with open(os.path.join(build_directory, output_file), 'w') as ofstream:
        print = lambda s: ofstream.write('{}\n'.format(s))
        print(';')
        if mod.name() == EXEC_MODULE:
            print('; Function definitions')
        else:
            print('; Function definitions for module {}'.format(mod.name()))
        print(';')

        for each in fns:
            out = each['out']

            print('')

            sig = mod.signature(out.main.name.split('::')[-1])
            print('; {}'.format(signature_to_string(out.main.name.split('/')[0], sig)))

            print('.function: {}'.format(out.main.name))
            for line in out.main.body:
                print('    {}'.format(line.to_string()))
            print('.end')

def cc_impl_save_interface(mod, file_paths, roots):
    source_file, output_file = file_paths
    source_root, build_directory = roots

    src_interface_file = '{}.vti'.format(source_file.rsplit('.', maxsplit=1)[0])
    out_interface_file = '{}.vti'.format(output_file.rsplit('.', maxsplit=1)[0])
    if os.path.isfile(os.path.join(source_root, src_interface_file)):
        shutil.copyfile(
            src = os.path.join(source_root, src_interface_file),
            dst = os.path.join(build_directory, out_interface_file),
        )
        return

    out_interface_path = os.path.join(build_directory, out_interface_file)
    with open(out_interface_path, 'w') as ofstream:
        print = lambda s: ofstream.write('{}\n'.format(s))
        print(';')
        print('; This interface file was automatically generated.')
        print(';')

        print('')
        for each in mod.enums():
            sig = mod.enum(each)
            print(signature_of_enum_to_string(each, sig, 0))

        print('')
        for each in mod.records():
            sig = mod.record(each)
            print(signature_of_record_to_string(each, sig, 0))

        print('')
        for each in mod.fns(local = True):
            fn, _ = each
            sig = mod.signature(fn)
            print(signature_to_string(sig['base_name'], sig))

def cc(source_root, source_file, module_name, forms, build_directory):
    base_output_file = (os.path.splitext(source_file)[0] + '.asm')
    output_file = os.path.normpath(base_output_file)

    viuact.util.log.debug('cc: [{}]/{} -> {}/{}'.format(
        source_root,
        source_file,
        build_directory,
        output_file,
    ))

    mod = cc_impl_prepare_module(module_name, source_file, forms)
    fns = cc_impl_emit_functions(mod, forms)

    output_directory = os.path.split(os.path.join(build_directory, output_file))[0]
    os.makedirs(output_directory, exist_ok = True)

    cc_impl_save_implementation(mod, fns, build_directory, output_file)
    if module_name != EXEC_MODULE:
        cc_impl_save_interface(
            mod,
            (source_file, output_file,),
            (source_root, build_directory,),
        )
