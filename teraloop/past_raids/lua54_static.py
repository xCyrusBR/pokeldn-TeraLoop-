"""Bounded Lua5.4 chunk inspection; never load or execute a script.

Format references: lua.org/source/5.4/{lundump.c,lopcodes.h,lobject.h}.html.
Only prototypes containing the requested string constant are reported.
"""
import struct

OP_NAMES = ('MOVE LOADI LOADF LOADK LOADKX LOADFALSE LFALSESKIP LOADTRUE LOADNIL '
    'GETUPVAL SETUPVAL GETTABUP GETTABLE GETI GETFIELD SETTABUP SETTABLE SETI '
    'SETFIELD NEWTABLE SELF ADDI ADDK SUBK MULK MODK POWK DIVK IDIVK BANDK BORK '
    'BXORK SHRI SHLI ADD SUB MUL MOD POW DIV IDIV BAND BOR BXOR SHL SHR '
    'MMBIN MMBINI MMBINK UNM BNOT NOT LEN CONCAT CLOSE TBC JMP EQ LT LE EQK '
    'EQI LTI LEI GTI GEI TEST TESTSET CALL TAILCALL RETURN RETURN0 RETURN1 '
    'FORLOOP FORPREP TFORPREP TFORCALL TFORLOOP SETLIST CLOSURE VARARG VARARGPREP EXTRAARG').split()


def instruction(word):
    op = word & 127
    if op >= len(OP_NAMES):
        raise ValueError('Unknown Lua5.4 opcode')
    return {'op': OP_NAMES[op], 'A': (word >> 7) & 255,
            'k': (word >> 15) & 1, 'B': (word >> 16) & 255,
            'C': word >> 24, 'Bx': word >> 15,
            'sBx': (word >> 15) - 65535, 'Ax': word >> 7}


class ChunkReader:
    def __init__(self, data, target, field_index=None, selected_prototypes=()):
        if not isinstance(data, (bytes, bytearray)) or not 32 <= len(data) <= 32 * 1024 * 1024:
            raise ValueError('Lua chunk outside input bounds')
        if not isinstance(target, bytes) or not 1 <= len(target) <= 128:
            raise ValueError('A bounded target string is required')
        self.data, self.target, self.offset = data, target, 0
        self.prototypes, self.matches = 0, []
        if (len(selected_prototypes) > 32 or any(type(i) is not int or not 0 <= i < 100000
                                               for i in selected_prototypes)):
            raise ValueError('Selected prototype IDs outside bounded query')
        self.selected_prototypes = frozenset(selected_prototypes)
        self.selected_closure_sites = []
        if field_index is not None and (type(field_index) is not int or not 0 <= field_index <= 255):
            raise ValueError('Numeric table field must fit a byte')
        self.field_index = field_index

    def take(self, size):
        end = self.offset + size
        if size < 0 or end > len(self.data):
            raise ValueError('Truncated Lua chunk')
        result = memoryview(self.data)[self.offset:end]
        self.offset = end
        return result

    def byte(self):
        return self.take(1)[0]

    def unsigned(self, limit=0x7fffffff):
        result = 0
        for _ in range(10):
            value = self.byte()
            result = (result << 7) | (value & 127)
            if result > limit:
                raise ValueError('Lua length exceeds analysis bound')
            if value & 128:
                return result
        raise ValueError('Unterminated Lua integer')

    def string(self):
        size = self.unsigned(32 * 1024 * 1024)
        return None if not size else bytes(self.take(size - 1))

    def proto(self, parent=None, depth=0):
        if depth > 100 or self.prototypes >= 100000:
            raise ValueError('Lua prototype tree exceeds bound')
        ident = self.prototypes
        self.prototypes += 1
        start = self.offset
        self.string()  # Source is deliberately not exported.
        line, endline = self.unsigned(), self.unsigned()
        params, vararg, stack = self.byte(), self.byte(), self.byte()
        count = self.unsigned(4 * 1024 * 1024)
        code_offset = self.offset
        code = self.take(count * 4)
        constants = []
        for _ in range(self.unsigned(1000000)):
            tag = self.byte()
            if tag == 0:
                value = None
            elif tag in (1, 17):
                value = tag == 17
            elif tag in (3, 19):
                value = struct.unpack('<q' if tag == 3 else '<d', self.take(8))[0]
            elif tag in (4, 20):
                value = self.string()
                if value is None:
                    raise ValueError('Null Lua string constant')
            else:
                raise ValueError('Unsupported Lua constant tag')
            constants.append(value)
        upvalue_count = self.unsigned(255)
        self.take(upvalue_count * 3)
        writes = []
        if self.field_index is not None:
            for pc in range(count):
                word = struct.unpack_from('<I', code, pc * 4)[0]
                if word & 127 == 17 and (word >> 16) & 255 == self.field_index:
                    writes.append(pc)
        match = None
        if self.target in constants or writes or ident in self.selected_prototypes:
            targets = [i for i, value in enumerate(constants) if value == self.target]
            hits = []
            for pc in range(count):
                ins = instruction(struct.unpack_from('<I', code, pc * 4)[0])
                constant_index = (ins['Bx'] if ins['op'] == 'LOADK' else
                    ins['C'] if ins['op'] in ('GETTABUP', 'GETFIELD') or (ins['op'] == 'SELF' and ins['k']) else None)
                if constant_index in targets:
                    hits.append(pc)
            positions = sorted({pc for hit in hits + writes for pc in range(max(0, hit - 16), min(count, hit + 24))})
            if count <= 512 or (ident in self.selected_prototypes and count <= 4096):
                positions = list(range(count))
            match = {'prototype_id': ident, 'parent_id': parent,
                'chunk_offset': start, 'code_offset': code_offset,
                'line_defined': line, 'last_line_defined': endline,
                'numparams': params, 'vararg': vararg, 'stack': stack,
                'instruction_count': count, 'target_constant_indices': targets,
                'target_lookup_pcs': hits,
                'numeric_field_write_pcs': writes,
                'constants': [{'index': i, 'value': value.decode('utf-8', 'replace')
                    if isinstance(value, bytes) and len(value) <= 128 else
                    {'opaque_string_bytes': len(value)} if isinstance(value, bytes) else value}
                    for i, value in enumerate(constants)],
                'instruction_windows': [{'pc': pc, **instruction(struct.unpack_from('<I', code, pc * 4)[0])}
                                        for pc in positions]}
            self.matches.append(match)
        child_ids = [self.proto(ident, depth + 1) for _ in range(self.unsigned(100000))]
        if self.selected_prototypes:
            for pc in range(count):
                word = struct.unpack_from('<I', code, pc * 4)[0]
                if word & 127 != 79:
                    continue
                child = word >> 15
                if child >= len(child_ids):
                    raise ValueError('Lua closure child index outside prototype')
                if child_ids[child] not in self.selected_prototypes:
                    continue
                positions = range(max(0, pc - 8), min(count, pc + 3))
                window = [{'pc': at, **instruction(struct.unpack_from('<I', code, at * 4)[0])}
                          for at in positions]
                indices = {i['Bx'] for i in window if i['op'] == 'LOADK'}
                self.selected_closure_sites.append({'parent_id': ident, 'pc': pc,
                    'prototype_id': child_ids[child], 'instruction_window': window,
                    'constant_names': [{'index': i, 'value': constants[i].decode('utf-8', 'replace')}
                                       for i in sorted(indices) if i < len(constants) and
                                       isinstance(constants[i], bytes) and len(constants[i]) <= 128]})
        if match is not None:
            match['closure_links'] = []
            for ins in match['instruction_windows']:
                if ins['op'] == 'CLOSURE':
                    if ins['Bx'] >= len(child_ids):
                        raise ValueError('Lua closure child index outside prototype')
                    match['closure_links'].append({'pc': ins['pc'], 'child_index': ins['Bx'],
                                                   'prototype_id': child_ids[ins['Bx']]})
        self.take(self.unsigned(4 * 1024 * 1024))  # lineinfo
        for _ in range(self.unsigned(4 * 1024 * 1024)):
            self.unsigned(); self.unsigned()
        for _ in range(self.unsigned(1000000)):
            self.string(); self.unsigned(); self.unsigned()
        names = self.unsigned(255)
        if names not in (0, upvalue_count):
            raise ValueError('Lua upvalue-name count differs')
        for _ in range(names):
            self.string()
        return ident

    def read(self):
        expected = bytes.fromhex('1b4c7561540019930d0a1a0a040808')
        if bytes(self.take(len(expected))) != expected:
            raise ValueError('Unsupported Lua5.4 header or machine widths')
        if struct.unpack('<q', self.take(8))[0] != 0x5678 or struct.unpack('<d', self.take(8))[0] != 370.5:
            raise ValueError('Lua byte order or numeric format differs')
        self.byte()  # main closure upvalue count, not a script execution
        self.proto()
        if self.offset != len(self.data):
            raise ValueError('Unconsumed Lua chunk suffix')
        return {'version': '5.4', 'fully_consumed': True,
                'prototypes': self.prototypes, 'matches': self.matches,
                'selected_closure_sites': self.selected_closure_sites,
                'script_executed': False, 'argument_provenance_verified': False}


def inspect_chunk(data, target=b'f17608AE1', field_index=None, selected_prototypes=()):
    return ChunkReader(data, target, field_index, selected_prototypes).read()
