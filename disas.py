from enum import IntEnum, auto
import ctypes

class numdisp(IntEnum):
	HEX = 0
	DEC = auto()
	OCT = auto()
	BIN = auto()

class Register:
	__reg_prefixes = {1: 'R', 2: 'ER', 4: 'XR', 8: 'QR'}
	__slots__ = ('size', 'n')
	def __init__(self, size, n):
		if size not in self.__reg_prefixes.keys(): raise ValueError('invalid register size')
		if n not in range(0, 16, size): raise ValueError('invalid value for n')
		super().__setattr__('size', size)
		super().__setattr__('n', n)

	def __repr__(self): return f'{type(self).__name__}(size={self.size}, n={self.n})'
	def __str__(self): return f'{self.__reg_prefixes[self.size]}{self.n}'
	def __setattr__(self, name, value): raise AttributeError(f"attribute '{name}' of '{type(self).__name__}' objects is not writable")

class ObjectBit:
	__slots__ = ('obj', 'bit')
	def __init__(self, obj, bit):
		if bit not in range(8): raise ValueError('bit offset must be an integer between 0-7')
		super().__setattr__('obj', obj)
		super().__setattr__('bit', bit)

	def __repr__(self): return f'{type(self).__name__}(obj={self.obj}, bit={self.bit})'
	def __str__(self): return f'{self.obj}.{self.bit}'
	def __setattr__(self, name, value): raise AttributeError(f"attribute '{name}' of '{type(self).__name__}' objects is not writable")

class Num:
	__slots__ = ('bits', 'value', 'disp', 'sign')
	def __init__(self, bits, value):
		bits = int(bits)
		if bits < 1: raise ValueError('invalid bit length')
		elif type(value) == float: raise TypeError("'float' object cannot be interpreted as an integer")
		super().__setattr__('bits', bits)
		super().__setattr__('value', value & (2**bits))
		self.disp = numdisp.HEX
		self.sign = True

	def __repr__(self): return f'{type(self).__name__}(bits={self.bits}, value={self.value}, disp={numdisp(self.disp).name})'
	def __str__(self):
		value = self.value - (self.value >> (bits - 1)) * (2**bits) if self.sign else self.value
		if self.disp == numdisp.HEX: return f'#{value:X}H'
		elif self.disp == numdisp.DEC: return f'#{value}'
		elif self.disp == numdisp.OCT: return f'#{value:o}O'
		elif self.disp == numdisp.BIN: return f'#{value:b}B'
	def __setattr__(self, name, value):
		if name in ('bits', 'value'): raise AttributeError(f"attribute '{name}' of '{type(self).__name__}' objects is not writable")
		else: super().__setattr__(name, value)

def RegHandler(flags, value): return Register(flags, value)
def NumHandler(flags, value): return Num(flags, value)
def RegCtrlHandler(flags, value):
	if flags == 0: return 'ECSR'
	elif flags == 1: return 'ELR'
	elif flags == 2: return 'PSW'
	elif flags == 3: return 'EPSW'
	elif flags == 4: return 'SP'
	elif flags == 6: return 'DSR'
def MemHandler(flags, value):
	s = (flags >> 12) & 0xf
	d = (flags >> 8) & 0xf
	e = (flags >> 4) & 0xf
	r = flags & 0xf

class Disassembly:
	__instrs = [
		# original from https://github.com/gamingwithevets/u8_emu/blob/main/src/core/instr.c
		
		#                               op0                                      op1
		# [mnemonic, mask,  [mask, shift, flags, handler],          [mask, shift, flags, handler]]

		# Arithmetic Instructions
		['ADD',		0x8001,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['ADD',		0x1000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]]
		['ADD',		0xf006, [0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x0002, RegHandler]]
		['ADD',		0xe080, [0x0e00, 8,  0x0002, RegHandler],		[0x007f, 0,  0x0006, NumHandler]]
		['ADDC',	0x8006,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['ADDC',	0x6000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]]
		['AND',		0x8002,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['AND',		0x2000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]]
		['CMP',		0x8007,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['CMP',		0x7000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]]
		['CMPC',	0x8005,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['CMPC',	0x5000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]]
		['MOV',		0xf005,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x0002, RegHandler]]
		['MOV',		0xe000,	[0x0e00, 8,  0x0002, RegHandler],		[0x007f, 0,  0x0006, NumHandler]]
		['MOV',		0x8000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['MOV',		0x0000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]]
		['OR',		0x8003,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['OR',		0x3000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]]
		['XOR',		0x8004,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['XOR',		0x4000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]]
		['CMP',		0xf007,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x0002, RegHandler]]
		['SUB',		0x8008,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['SUBC',	0x8009,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]

		# Shift Instructions
		['SLL',		0x800a,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['SLL',		0x900a,	[0x0f00, 8,  0x0001, RegHandler],		None]
		['SLLC',	0x800b,	[0x0f00, 8,  0x0012, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['SLLC',	0x900b,	[0x0f00, 8,  0x0012, RegHandler],		None]
		['SRA',		0x800e,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['SRA',		0x900e,	[0x0f00, 8,  0x0001, RegHandler],		None]
		['SRL',		0x800c,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['SRL',		0x900c,	[0x0f00, 8,  0x0001, RegHandler],		None]
		['SRLC',	0x800d,	[0x0f00, 8,  0x0002, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['SRLC',	0x900d,	[0x0f00, 8,  0x0002, RegHandler],		None]

		# DSR Prefix Instructions
		[None,		0xe300,	[0x00ff, 0,  0x0008, NumHandler],		None]
		[None,		0x900f,	[0x00f0, 4,  0x0001, RegHandler],		None]
		[None,		0xfe9f,	[0x0000, 0,  0x0006, RegCtrlHandler],	None]

		# Load/Store Instructions
		['L',		0x9032,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x1001, MemHandler]]
		['L',		0x9052,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x9001, MemHandler]]
		['L',		0x9002,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x1002, MemHandler]]
		['L',		0xa008,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x1102, MemHandler]]
		['L',		0xb000,	[0x0e00, 8,  0x0002, RegHandler],		[0x003f, 0,  0x1253, MemHandler]]
		['L',		0xb040,	[0x0e00, 8,  0x0002, RegHandler],		[0x003f, 0,  0x1254, MemHandler]]
		['L',		0x9012,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x1100, MemHandler]]
		['L',		0x9030,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0001, MemHandler]]
		['L',		0x9050,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x8001, MemHandler]]
		['L',		0x9000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00e0, 4,  0x0002, MemHandler]]
		['L',		0x9008,	[0x0f00, 8,  0x0001, RegHandler],		[0x00e0, 4,  0x0102, MemHandler]]
		['L',		0xd000,	[0x0f00, 8,  0x0001, RegHandler],		[0x003f, 0,  0x0253, MemHandler]]
		['L',		0xd040,	[0x0f00, 8,  0x0001, RegHandler],		[0x003f, 0,  0x0254, MemHandler]]
		['L',		0x9010,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0100, MemHandler]]
		['L',		0x9034,	[0x0c00, 8,  0x0004, RegHandler],		[0x0000, 0,  0x3001, MemHandler]]
		['L',		0x9054,	[0x0c00, 8,  0x0004, RegHandler],		[0x0000, 0,  0xB001, MemHandler]]
		['L',		0x9036,	[0x0800, 8,  0x0008, RegHandler],		[0x0000, 0,  0x7001, MemHandler]]
		['L',		0x9056,	[0x0800, 8,  0x0008, RegHandler],		[0x0000, 0,  0xF001, MemHandler]]

		['ST',		0x9033,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x1001, MemHandler]]
		['ST',		0x9053,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x9001, MemHandler]]
		['ST',		0x9003,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x1002, MemHandler]]
		['ST',		0xa009,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x1102, MemHandler]]
		['ST',		0xb080,	[0x0e00, 8,  0x0002, RegHandler],		[0x003f, 0,  0x1253, MemHandler]]
		['ST',		0xb0c0,	[0x0e00, 8,  0x0002, RegHandler],		[0x003f, 0,  0x1254, MemHandler]]
		['ST',		0x9013,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x1100, MemHandler]]
		['ST',		0x9031,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0001, MemHandler]]
		['ST',		0x9051,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x8001, MemHandler]]
		['ST',		0x9001,	[0x0f00, 8,  0x0001, RegHandler],		[0x00e0, 4,  0x0002, MemHandler]]
		['ST',		0x9009,	[0x0f00, 8,  0x0001, RegHandler],		[0x00e0, 4,  0x0102, MemHandler]]
		['ST',		0xd080,	[0x0f00, 8,  0x0001, RegHandler],		[0x003f, 0,  0x0253, MemHandler]]
		['ST',		0xd0c0,	[0x0f00, 8,  0x0001, RegHandler],		[0x003f, 0,  0x0254, MemHandler]]
		['ST',		0x9011,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0100, MemHandler]]
		['ST',		0x9035,	[0x0c00, 8,  0x0004, RegHandler],		[0x0000, 0,  0x3001, MemHandler]]
		['ST',		0x9055,	[0x0c00, 8,  0x0004, RegHandler],		[0x0000, 0,  0xB001, MemHandler]]
		['ST',		0x9037,	[0x0800, 8,  0x0008, RegHandler],		[0x0000, 0,  0x7001, MemHandler]]
		['ST',		0x9057,	[0x0800, 8,  0x0008, RegHandler],		[0x0000, 0,  0xF001, MemHandler]]

		# Control RegHandler Access Instructions
		['ADD',		0xe100,	[0x0000, 0,  0x0024, RegCtrlHandler],	[0x00ff, 0,  0x0007, NumHandler]]
		['MOV',		0xa00f,	[0x0000, 0,  0x0010, RegCtrlHandler],	[0x00f0, 4,  0x0001, RegHandler]]
		['MOV',		0xa00d,	[0x0000, 0,  0x0021, RegCtrlHandler],	[0x0f00, 8,  0x0002, RegHandler]]
		['MOV',		0xa00c,	[0x0000, 0,  0x0013, RegCtrlHandler],	[0x00f0, 4,  0x0001, RegHandler]]
		['MOV',		0xa005,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x0021, RegCtrlHandler]]
		['MOV',		0xa01a,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x0024, RegCtrlHandler]]
		['MOV',		0xa00b,	[0x0000, 0,  0x0012, RegCtrlHandler],	[0x00f0, 4,  0x0001, RegHandler]]
		['MOV',		0xe900,	[0x0000, 0,  0x0012, RegCtrlHandler],	[0x00ff, 0,  0x0008, NumHandler]]
		['MOV',		0xa007,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0010, RegCtrlHandler]]
		['MOV',		0xa004,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0013, RegCtrlHandler]]
		['MOV',		0xa003,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0012, RegCtrlHandler]]
		['MOV',		0xa10a,	[0x0000, 0,  0x0024, RegCtrlHandler],	[0x00e0, 4,  0x0002, RegHandler]]

		# Push/Pop Instructions
		['PUSH',	0xf05e,	[0x0e00, 8,  0x0002, RegHandler],		None]
		['PUSH',	0xf07e,	[0x0800, 8,  0x0008, RegHandler],		None]
		['PUSH',	0xf04e,	[0x0f00, 8,  0x0001, RegHandler],		None]
		['PUSH',	0xf06e,	[0x0c00, 8,  0x0004, RegHandler],		None]
		['PUSH',	0xf0ce,	[0x0f00, 8,  0x0008, NumHandler],		None]
		['POP',		0xf01e,	[0x0e00, 8,  0x0002, RegHandler],		None]
		['POP',		0xf03e,	[0x0800, 8,  0x0008, RegHandler],		None]
		['POP',		0xf00e,	[0x0f00, 8,  0x0001, RegHandler],		None]
		['POP',		0xf02e,	[0x0c00, 8,  0x0004, RegHandler],		None]
		['POP',		0xf08e,	[0x0f00, 8,  0x0008, NumHandler],		None]

		# TODO: Coprocessor Instructions

		# EA RegHandler Data Transfer Instructions
		['LEA',		0xf00a,	[0x00e0, 4,  0x0002, MemHandler],		None]
		['LEA',		0xf00b,	[0x00e0, 4,  0x0102, MemHandler],		None]
		['LEA',		0xf00c,	[0x0000, 0,  0x0100, MemHandler],		None]

		# ALU Instructions
		['DAA',		0x801f,	[0x0f00, 8,  0x0001, RegHandler],		None]
		['DAS',		0x803f,	[0x0f00, 8,  0x0001, RegHandler],		None]
		['NEG',		0x805f,	[0x0f00, 8,  0x0001, RegHandler],		None]

		# Bit Access Instructions
		['SB',		0xa000,	[0x0f00, 8,  0x0001, RegHandler],		None]
		['SB',		0xa080,	[0x0000, 0,  0x0100, MemHandler],		None]
		['RB',		0xa002,	[0x0f00, 8,  0x0001, RegHandler],		None]
		['RB',		0xa082,	[0x0000, 0,  0x0100, MemHandler],		None]
		['TB',		0xa001,	[0x0f00, 8,  0x0001, RegHandler],		None]
		['TB',		0xa081,	[0x0000, 0,  0x0100, MemHandler],		None]

		# PSW Access Instructions
		['EI',		0xed08,	None,						None]
		['DI',		0xebf7,	None,						None]
		['SC',		0xed80,	None,						None]
		['RC',		0xeb7f,	None,						None]
		['CPLC',	0xfecf,	None,						None]

		# Conditional Relative Branch Instructions
		['BC',		0xc000,	[0x0f00, 8,	 0x0000, CondHandler],		[0x00ff, 0,  0x0007, NumHandler]]

		# Sign Extension Instruction
		['EXTBW',	0x810f,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x0002, RegHandler]]

		# Software Interrupt Instructions
		['SWI',		0xe500,	[0x003f, 0,  0x0008, NumHandler],		None]
		['BRK',		0xffff,	None,						None]

		# Branch Instructions
		['B',		0xf000,	[0x0f00, 8,  0x0004, NumHandler],		[0x0000, 0,  0x0100, MemHandler]]
		['B',		0xf002,	[0x00e0, 4,  0x0002, MemHandler]]
		['BL',		0xf001,	[0x0f00, 8,  0x0004, NumHandler],		[0x0000, 0,  0x0100, MemHandler]]
		['BL',		0xf003,	[0x00e0, 4,  0x0002, MemHandler]]

		# Multiplication and Division Instructions
		['MUL',		0xf004,	[0x0e00, 8,  0x0002, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]
		['DIV',		0xf009,	[0x0e00, 8,  0x0002, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]]

		# Miscellaneous Instructions
		['INC',		0xfe2f,	[0x0000, 0,  0x0001, MemHandler],		None]
		['DEC',		0xfe3f,	[0x0000, 0,  0x0001, MemHandler],		None]
		['RT',		0xfe1f,	None,						None]
		['RTI',		0xfe0f,	None,						None]
		['NOP',		0xfe8f,	None,						None]
	]

	def __setattr__(self, name, value): raise AttributeError(f"attribute '{name}' of '{type(self).__name__}' objects is not writable")

	def __init__(self, labels = [], data_labels = [], data_bit_labels = []):
		pass
