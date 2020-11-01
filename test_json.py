from __future__ import annotations

import json
import re
from itertools import repeat

from lark import Lark, v_args
from lark.visitors import Transformer

from main import NimParseTable

_json_unesc_re = re.compile(r'\\(["/\\bfnrt]|u[0-9A-Fa-f])')
_json_unesc_map = {
    '"': '"',
    '/': '/',
    '\\': '\\',
    'b': '\b',
    'f': '\f',
    'n': '\n',
    'r': '\r',
    't': '\t',
}


def _json_unescape(m):
    c = m.group(1)
    if c[0] == 'u':
        return chr(int(c[1:], 16))
    c2 = _json_unesc_map.get(c)
    if not c2:
        raise ValueError(f'invalid escape sequence: {m.group(0)}')
    return c2


def json_unescape(s):
    return _json_unesc_re.sub(_json_unescape, s[1:-1])


json_grammar = r"""
    ?start: _WS? value _WS?

    ?value: object
          | array
          | string
          | NUMBER             -> number
          | "true"             -> true
          | "false"            -> false
          | "null"             -> null

    array  : _BRACK1 [value (_COMMA value)*] _BRACK2
    object : _CURLY1 [pair (_COMMA pair)*] _CURLY2
    pair   : string _COLON value

    _COLON: /\s*:\s*/
    _COMMA: /\s*,\s*/
    _CURLY1: /\s*{\s*/
    _CURLY2: /\s*}\s*/
    _BRACK1: /\s*\[\s*/
    _BRACK2: /\s*\]\s*/

    string : STRING
    STRING: "\"" INNER* "\""
    INNER: /[ !#-\[\]-\U0010ffff]*/
         | /\\(?:["\/\\bfnrt]|u[0-9A-Fa-f]{4})/

    NUMBER : INTEGER FRACTION? EXPONENT?
    INTEGER: ["-"] ("0" | "1".."9" INT?)
    FRACTION: "." INT
    EXPONENT: ("e"|"E") ["+"|"-"] INT

    _WS: /\s+/

    %import common.INT
"""


class TreeToJson(Transformer):
    @v_args(inline=True)
    def string(self, s):
        return json_unescape(s)

    array = list
    pair = tuple
    object = dict
    number = v_args(inline=True)(float)

    null = lambda self, _: None
    true = lambda self, _: True
    false = lambda self, _: False


json_parser = Lark(json_grammar,
                   parser='lalr',
                   lexer='standard',
                   propagate_positions=False,
                   maybe_placeholders=False,
                   transformer=TreeToJson())
nim_json_parser = NimParseTable(json_parser)

data = """{
 "int": 123456789,
 "float": 1234.56789,
 "exponent": 12345678e9,
 "dot_exp": 1.234567e89,
 "string": "123456789",
 "list": [1,2,3,4,5,6,7,8,9]
}"""

big_data = "[" + ",".join(repeat(data, 100)) + "]"
bigger_data = "[" + ",".join(repeat(big_data, 100)) + "]"
# json.loads(bigger_data)
nim_json_parser.parse(bigger_data)
