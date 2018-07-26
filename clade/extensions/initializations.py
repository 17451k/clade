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


def t_DECLARATION(t):
    r'declaration:[ ]((?:.|\n)+?);[ ]path:[ ](.+);[ ]type:[ ]global'
    declaration = t.lexer.lexmatch.group(2).replace('\n', ' ')
    path = t.lexer.lexmatch.group(3)
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
    t.value = [tab, value]
    return t


def t_VALUE_LIST(t):
    r'([ ]*)value:\n'
    tab = int(len(t.lexer.lexmatch.group(8)) / 2)
    t.value = [tab, []]
    return t


def t_STRUCTURE(t):
    r'([ ]+)field[ ]declaration:[ ](.+);\n'
    tab = int(len(t.lexer.lexmatch.group(10)) / 2)
    declaration = t.lexer.lexmatch.group(11).replace('\n', ' ')
    t.value = [tab, {
        "field": declaration,
        "value": None
    }]
    return t


def t_ARRAY(t):
    r'([ ]+)array[ ]element[ ]index:[ ](\d+)\n'
    tab = int(len(t.lexer.lexmatch.group(13)) / 2)
    index = int(t.lexer.lexmatch.group(14))
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
    if len(p) == 3 and isinstance(p[1], list):
        p[1].append(p[2])
        p[0] = p[1]
    else:
        p[0] = [p[1]]


def p_variable(p):
    """
    variable : DECLARATION ESC value
    """
    if len(p[3]) == 1 and (
            (p[3][0][0] == 0 and (isinstance(p[3][0][1], str) or p[3][0][1] == [])) or
            (p[3][0][0] == 1 and isinstance(p[3][0][1], list))):
        p[1]['value'] = p[3][0][1] if not isinstance(p[3][0][1], list) else list(reversed(p[3][0][1]))
        p[0] = p[1]
    else:
        raise NotImplementedError


def p_value(p):
    """
    value : VALUE_LIST value_list
          | simple_value
    """
    if len(p) == 3:
        p[0] = p[2]
    else:
        p[0] = p[1]


def p_value_list(p):
    """
    value_list : base_value value_list
               | base_value
    """
    if len(p) == 2:
        if isinstance(p[1], list) and isinstance(p[1][0], int):
            p[0] = [p[1]]
        else:
            p[0] = p[1]
    else:
        if p[2][0][0] == p[1][0]:
            p[2][0][1] += p[1][1]
            p[0] = p[2]
        else:
            p[0] = [p[1]] + p[2]


def p_base_value(p):
    """
    base_value : STRUCTURE value
               | ARRAY value
    """
    # The same indent
    p[1][1]["value"] = p[2][0][1]
    if len(p[2]) > 1:
        p[2] = p[2][1:]
        p[2][0][1].append(p[1][1])
        p[0] = p[2]
    else:
        p[0] = [p[1][0], [p[1][1]]]


def p_simple_value(p):
    """
    simple_value : VALUE ESC
                 | VALUE_LIST ESC
                 | VALUE_LIST
                 | VALUE
    """
    p[0] = [p[1]]


def setup_parser():
    """
    Setup the parser.

    :return: None
    """
    global __parser
    global __lexer

    __lexer = lex.lex()
    __parser = yacc.yacc(debug=True, write_tables=True)


def parse_declaration(string):
    """
    Parse the given C declaration string with the possible interface extensions.

    :param string: C declaration string.
    :return: Obtained abstract syntax tree.
    """
    global __parser
    global __lexer

    if not __parser:
        setup_parser()

    return __parser.parse(string, lexer=__lexer)


def parse_initialization_functions(filename):
    with open(filename, 'r') as fp:
        data = fp.read() + '\n'

    return parse_declaration(data)
