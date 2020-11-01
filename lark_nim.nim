import nimpy
import tables

type
    
  LarkNim* = object
    name*: string
    parse_table: Table[int, string]
    
  Rule* = object
    id*: int
    length*: int
    callback*: proc (children: seq[PyObject]): PyObject
    
  ParseTable* = object
    start_states*: Table[string, int]
    end_states*: Table[string, int]
    rules*: Table[int, Rule]
    states*: Table[int, Table[int, (bool, int)]]
    eof_id: int

  TokenStream* = proc (): tuple[id: int, obj: PyObject]

iterator items(it: TokenStream): tuple[id: int, obj: PyObject] =
    while true:
        let next = it()
        if next[0] < 0:
            break
        yield next

proc compile(parse_table: ParseTable): ref ParseTable {.exportpy.} =
    result.new
    result[] = parse_table

proc parse*(parse_table: ref ParseTable, start: string, stream: proc (): tuple[id: int, obj: PyObject]): PyObject {.exportpy.} =
    template reduce(rule_id: int) {.dirty.} =
        let r = parse_table.rules[rule_id]
        let children = value_stack[(value_stack.len - r.length)..^1]
        value_stack.setLen(value_stack.len - r.length)
        state_stack.setLen(state_stack.len - r.length)
        value_stack.add(r.callback(children))
        state_stack.add(parse_table.states[state_stack[^1]][r.id][1])
    let
        start_state = parse_table.start_states[start]
        end_state = parse_table.end_states[start]
    
    var
        value_stack: seq[PyObject] = @[]
        state_stack: seq[int] = @[start_state]
    for (id, obj) in stream:
        while true:
            let (action, arg) = parse_table.states[state_stack[^1]][id]
            if action:
                reduce(arg)
            else:
                state_stack.add(arg)
                value_stack.add(obj)
                break
    while true:
        if state_stack[^1] == end_state:
            return value_stack[^1]
        let (action, arg) = parse_table.states[state_stack[^1]][parse_table.eof_id]
        reduce(arg)
        doAssert action == true

