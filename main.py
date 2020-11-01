from __future__ import annotations

from pprint import pprint
from typing import Dict, Callable

from lark import Lark, Token
from lark.grammar import Rule
from lark.parsers.lalr_analysis import ParseTable, Shift
import nimporter
import lark_nim

def log(f):
    def wrap(*args, **kwargs):
        print(f"Calling {f.__name__} with ({args}, {kwargs})")
        r = f(*args, **kwargs)
        print(f"Return Value: {r}")
        return r
    return wrap

class NimParseTable:
    def __init__(self, lark: Lark):
        parse_table = lark.parser.parser.parser.parse_table
        callbacks = lark.parser.parser.parser.callbacks
        self.lark = lark
        self.start_states = {n:i+ 200 for n, i in parse_table.start_states.items()}
        self.end_states = {n:i+ 200 for n, i in parse_table.end_states.items()}
        self.states = {}
        self.rules = {}
        self.names_to_ids = {}
        rule_to_int = {}
        for state, transitions in parse_table.states.items():
            self.states[state + 200] = {}
            for t, action in transitions.items():
                if t not in self.names_to_ids:
                    self.names_to_ids[t] = len(self.names_to_ids) + 100
                if action[0] is Shift:
                    assert isinstance(action[1], int)
                    self.states[state + 200][self.names_to_ids[t]] = 0, action[1] + 200
                else:
                    r = action[1]
                    if r not in rule_to_int:
                        i = rule_to_int[r] = len(rule_to_int) + 300
                        if r.origin.name not in self.names_to_ids:
                            self.names_to_ids[r.origin.name] = len(self.names_to_ids)+ 100
                        self.rules[i] = {"id": self.names_to_ids[r.origin.name],
                                         "length": len(r.expansion),
                                         "callback": callbacks[r]}
                    self.states[state + 200][self.names_to_ids[t]] = 1, rule_to_int[r]
        self.eof_id = self.names_to_ids['$END']
        self._nim_parse_table = lark_nim.compile(self.__dict__)
    def _lex(self, text: str):
        base_lex = self.lark.parser.lexer.lex(text)
        at_end = False
        last_token = None
        def get_token():
            nonlocal at_end, last_token
            if at_end:
                return -1, None
            try:
                last_token = next(base_lex)
                return self.names_to_ids[last_token.type], last_token
            except StopIteration:
                at_end = True
                return -1, None
        return get_token

    def parse(self, text: str):
        lex = self._lex(text)
        return lark_nim.parse(self._nim_parse_table, "start", lex)
