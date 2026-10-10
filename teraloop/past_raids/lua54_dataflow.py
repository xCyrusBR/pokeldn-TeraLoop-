"""Recognize only straight-line field-to-method copies, never execute Lua."""


def direct_field_copies(prototype, source_register):
    """Return SELF/GETFIELD/GETFIELD/CALL copies from one argument register.

    This deliberately excludes branches, casts, extra-action constructors and
    aliases. It does not identify the receiver's native class or wire format.
    """
    if type(source_register) is not int or not 0 <= source_register < 256:
        raise ValueError('Source register outside byte range')
    constants = {item['index']: item['value'] for item in prototype['constants']}
    code = prototype['instruction_windows']
    if len(code) > 1000000 or len({i['pc'] for i in code}) != len(code):
        raise ValueError('Instruction query exceeds bounds or repeats PCs')
    result = []
    for index in range(len(code) - 3):
        method, first, second, call = code[index:index + 4]
        if [i['pc'] for i in (first, second, call)] != [method['pc'] + n for n in (1, 2, 3)]:
            continue
        if (method['op'] != 'SELF' or method['k'] != 1 or
                first['op'] != 'GETFIELD' or first['B'] != source_register or
                first['A'] != method['A'] + 2 or second['op'] != 'GETFIELD' or
                second['A'] != first['A'] or second['B'] != first['A'] or
                call['op'] != 'CALL' or call['A'] != method['A'] or
                call['B'] != 3 or call['C'] != 1):
            continue
        names = [constants.get(i['C']) for i in (method, first, second)]
        if not all(isinstance(name, str) and 1 <= len(name) <= 128 for name in names):
            raise ValueError('Field-copy constant is not a bounded name')
        result.append({'pc': method['pc'], 'setter': names[0],
                       'source_path': names[1:], 'receiver_register': method['B']})
    return result
