# Copyright (c) 2018 ISP RAS (http://www.ispras.ru)
# Ivannikov Institute for System Programming of the Russian Academy of Sciences
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re
import os
import ply.lex as lex
import ply.yacc as yacc

__parser = None
__lexer = None

tokens = (
    'DECLARATION',
    "STRUCTURE",
    "ARRAY",
    "ESC",
    "VALUE",
    "VALUE_LIST",
)
t_ESC = r'\n+'
t_ignore = ''


tmp_value_cache = set()
functions = None
callgraph_update_method = None
function_name_re = re.compile(r"\(?\s*&?\s*(\w+)\s*\)?$")


def t_DECLARATION(t):
    r'declaration:[ ]((?:.|\n)+?);[ ]path:[ ](.+);[ ]type:[ ]global'
    declaration = t.lexer.lexmatch.group(2).replace('\n', ' ')
    path = t.lexer.lexmatch.group(3)
    # This is a prototype of a variable description
    t.value = {
        "declaration": declaration,
        "path": path,
        "type": "global",
        "value": None
    }
    return t


def t_VALUE(t):
    r'([ ]*)value:[ ](.+)\n'
    tab = int(len(t.lexer.lexmatch.group(5)) / 2)
    value = t.lexer.lexmatch.group(6)
    # Simple value with tabs number (for case sensitive) and the value
    t.value = [tab, value]
    return t


def t_VALUE_LIST(t):
    r'([ ]*)value:\n'
    tab = int(len(t.lexer.lexmatch.group(8)) / 2)
    t.value = [tab, []]
    # Return a pair: the number of tabs (for case sensitiveness) and a list for future value to store
    return t


def t_STRUCTURE(t):
    r'([ ]+)field[ ]declaration:[ ](.+);\n'
    tab = int(len(t.lexer.lexmatch.group(10)) / 2)
    declaration = t.lexer.lexmatch.group(11).replace('\n', ' ')
    # Return a dictionary to describe field initialization value
    t.value = [tab, {
        "field": declaration,
        "value": None
    }]
    return t


def t_ARRAY(t):
    r'([ ]+)array[ ]element[ ]index:[ ](\d+)\n'
    tab = int(len(t.lexer.lexmatch.group(13)) / 2)
    index = int(t.lexer.lexmatch.group(14))
    # Return a dictionary to describe an array element initialization value
    t.value = [tab, {
        "index": index,
        "value": None
    }]
    return t


def t_error(t):
    raise TypeError("Unknown text '%s'" % (t.value,))


def p_error(t):
    raise TypeError("Unknown text '%s'" % (t.value,))


def p_variables(p):
    """
    variables : variables variable
              | variable ESC
              | variable
    """
    if len(p) == 3 and isinstance(p[2], dict):
        # Here we have an existing collection of variables (dictionary, see below) and a variable description
        collection = p[1]
        variable = p[2]
    else:
        # In this case we got a variable or a variable and an ESC token
        variable = p[1]
        collection = dict()

    # Check path
    collection.setdefault(variable["path"], list())
    # Add the variable
    collection[variable["path"]].append(variable)

    # We initialize the root collection dictionary there: {path -> [variable1, variable2]}
    p[0] = collection


def p_variable(p):
    """
    variable : DECLARATION ESC value
    """
    # It is a dictionary initialized at the token creation
    variable = p[1]
    # Ignore ESC token
    # Values can be:
    value_description = p[3]

    # First extract value itself, this should be just a pair without tabs
    if isinstance(value_description, list) and value_description[0] == 0:
        value = value_description[1]
    elif isinstance(value_description, list) and value_description[0] == 1 and isinstance(value_description[1], list):
        # This is a compound value
        value = value_description[1]
    else:
        raise ValueError("Not expected value as a variable initialization value: {!r} from {!r}".
                         format(variable['declaration'], variable['path']))

    variable['value'] = value
    p[0] = variable

    # Save all functions referred at initialization of this variable
    commit_functions(p[1]["path"])


def p_value(p):
    """
    value : VALUE_LIST value_list
          | simple_value
    """
    if len(p) == 3:
        # In this case we are sure that this is a collection of different fields and arrays initializations
        # This should be always ready to save value without indentations and other auxiliary data structures
        values_collection = p[2]
        p[0] = values_collection
    else:
        # In this case we just have a single value
        simple_value = p[1]
        p[0] = simple_value


def p_value_list(p):
    """
    value_list : base_value value_list
               | base_value
    """
    # Base  value is a description of a structure or an array initialization, but because of context sensitiveness
    # we may have in the base value other values attached and we will separate them later on the base of tabs numbers
    # This converts base value data structure, which is described in the next function, into a list of values that
    # should be ready to be saved.

    # The list can be represented by two states:
    # 1: It is ready to be saved and this mean that all element idents match each other and we just have a pair of
    #    indentation and the list with values
    # 2: It is not ready to be saved because additional elements will be added later and to track precisely their
    #    indentations we preserve base value structure with elements accumulated in the tail
    def new_item():
        # We got base item and just want to extract its value to save it to the list
        the_last_pair = base_value[1][0]
        rest_items = base_value[1][1:]
        min_indent = base_value[0]

        if min_indent == the_last_pair[0]:
            # Wrap the value and add it to the rest
            item = the_last_pair[1]
            if len(rest_items) == 0:
                return item
            else:
                rest_items.insert(0, item[0])
                return rest_items
        else:
            # In this cse we have incompletely filled base value, just return its second part to avoid any modifications
            return base_value[1]

    base_value = p[1]
    if len(p) == 2:
        # Here we have to make the list be ready to be saved
        bv = new_item()
        value_list = [base_value[0], bv]
    else:
        value_list = p[2]
        if value_list[0] == base_value[0]:
            # If minimal idents are the same - merge the last value
            bv = new_item()
            value_list[1] = bv + value_list[1]
        elif value_list[0] < base_value[0]:
            # We should save base value as a last changed item
            bv = new_item()
            # Now there are two options:
            if isinstance(value_list[1][0], dict):
                # This is state 1 and we have to convert it to base value format for further work
                bv = [base_value[0], bv]
                value_list[1].insert(0, bv)
            elif isinstance(value_list[1][0][0], int) and value_list[1][0][0] == base_value[0]:
                # This is already in state 2 and we have to merge the last added item in the list
                value_list[1][0][1] = bv + value_list[1][0][1]
            elif isinstance(value_list[1][0][0], int) and value_list[1][0][0] < base_value[0]:
                # We have an incomplete the latest element and suddenly get an extra element that cannot be added to it
                # thus we gonna add an extra incomplete element
                bv = [base_value[0], bv]
                value_list[1].insert(0, bv)
            else:
                raise NotImplementedError
        else:
            # This is strange
            raise NotImplementedError

    p[0] = value_list


def p_base_value(p):
    """
    base_value : STRUCTURE value
               | ARRAY value
    """
    # This intermediate base value accumulates recursive initializations of fields and array elements. The logic is the
    # following:
    # This is always a pair: [the_last_indent, values]
    # the_last_indent - the min indentation tabs number
    # values - accumulative list of values, it should be constructed as follows:
    # values = [ last_incomplete_item1, ..., last_incomplete_itemN, last_completely_filled_item1, ..., last_completely_filled_itemN]
    # last_incomplete_item - this is a list [last_indent, values_list]
    # last_completely_filled_itemi - just list of values ready to be saved, its ident should be equal to the_last_indent
    #                                so it is not necessary to save it
    # last_indent - indentation of the lase filled item
    # values_list - either list of values or a single value description

    value = p[2]
    element_initializer = p[1]

    if not isinstance(value[1], list) and value[0] == element_initializer[0]:
        # This is a simple value extracted from the last value initializer, create a data structure for it
        element_initializer[1]['value'] = value[1]

        min_indent = element_initializer[0]
        last_indent = element_initializer[0]
        last_values = [element_initializer[1]]
        tail = []
    elif isinstance(value[1], list):
        last_item = value[1][0]
        rest_items = value[1][1:]
        if value[0] == element_initializer[0] + 1:
            # All values can be consumed and the data structure should be rebased
            # But first prepare the last value
            rest_items.insert(0, last_item)

            # Save all values
            element_initializer[1]['value'] = rest_items

            # As a new base value use the new latest item
            min_indent = element_initializer[0]
            last_indent = element_initializer[0]
            last_values = [element_initializer[1]]
            tail = []
        elif last_item[0] == element_initializer[0] + 1:
            # Rebase only the last changed item because rest items are independent from this value
            element_initializer[1]['value'] = last_item[1]

            min_indent = value[0]
            last_indent = element_initializer[0]
            last_values = [element_initializer[1]]
            tail = rest_items
        else:
            # Indents do not match each other
            raise NotImplementedError
    else:
        # Seems that indents do not match each other
        raise NotImplementedError

    # Before return do sanity check that we cannot wrap more elements in case of an incomplete values added before
    if len(tail) > 0 and isinstance(tail[0], list) and tail[0][0] == element_initializer[0]:
        prev_incomplete = tail.pop(0)
        last_values = last_values + prev_incomplete[1]
    base_value = [min_indent, [[last_indent, last_values]] + tail]

    p[0] = base_value


def p_simple_value(p):
    """
    simple_value : VALUE ESC
                 | VALUE_LIST ESC
                 | VALUE_LIST
                 | VALUE
    """
    # The value is either an explicit value or the indicator that the initialization is described below and it contains
    # complex fields or array elements initializations
    value = p[1]
    if isinstance(value[1], str):
        # Check that the explicit value is a function reference
        possible_function_name = value[1]
        add_function(possible_function_name)

    # Anyway always returns a list of such values
    p[0] = value


def setup_parser(work_dir):
    """
    Setup the parser.

    :return: None
    """
    global __parser
    global __lexer

    os.makedirs(work_dir, exist_ok=True)
    __lexer = lex.lex(outputdir=work_dir, optimize=1, errorlog=yacc.NullLogger())
    __parser = yacc.yacc(outputdir=work_dir, optimize=1, errorlog=yacc.NullLogger())


def add_function(value):
    m = function_name_re.fullmatch(value)
    if m:
        function_name = m.group(1)
        tmp_value_cache.add(function_name)


def commit_functions(path):
    global functions
    global tmp_value_cache
    global callgraph_update_method
    callgraph_update_method({f for f in tmp_value_cache if f in functions}, path)
    tmp_value_cache = set()


def parse_declaration(string, work_dir):
    """
    Parse the given C declaration string with the possible interface extensions.

    :param string: C declaration string.
    :return: Obtained abstract syntax tree.
    """
    global __parser
    global __lexer

    if not __parser:
        setup_parser(work_dir)

    return __parser.parse(string, lexer=__lexer)


def parse_variables_initializations(iter_init_global, callgraph_functions, commit_method, work_dir):
    global functions
    global callgraph_update_method
    functions = callgraph_functions
    callgraph_update_method = commit_method

    data = ''.join(list(iter_init_global())) + '\n'

    return parse_declaration(data, work_dir)
