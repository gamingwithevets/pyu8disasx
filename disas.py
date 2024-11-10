import sys
if __name__ == '__main__':
	print('This script cannot be run normally.')
	sys.exit()

from enum import IntEnum, auto
import math

def conv_sign(value, bits): return value - (value >> (bits - 1)) * (2**bits)

class numdisp(IntEnum):
	HEX = 0
	DEC = auto()
	OCT = auto()
	BIN = auto()

class labeltype(IntEnum):
	FUN = 0
	LAB = auto()
	DAT = auto()

class Register:
	__reg_prefixes = {1: 'R', 2: 'ER', 4: 'XR', 8: 'QR'}
	__slots__ = ('size', 'n')
	def __init__(self, size, n):
		if size not in self.__reg_prefixes.keys(): raise ValueError(f'invalid register size {size}')
		super().__setattr__('size', size)
		super().__setattr__('n', n & (-1 << int(math.log2(size))))

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
	__slots__ = ('bits', 'value', 'imm', 'disp', 'sign')
	def __init__(self, bits, value, imm = True):
		bits = int(bits)
		if bits < 1: raise ValueError('invalid bit length')
		elif type(value) == float: raise TypeError("'float' object cannot be interpreted as an integer")
		super().__setattr__('bits', bits)
		super().__setattr__('value', value & (2**bits-1))
		super().__setattr__('imm', bool(imm))
		self.disp = numdisp.HEX
		self.sign = True

	def __repr__(self): return f'{type(self).__name__}(bits={self.bits}, value={self.value}, disp={numdisp(self.disp).name})'
	def __str__(self):
		value = conv_sign(self.value, self.bits) if self.sign else self.value
		if self.disp == numdisp.HEX: string = f'{value:X}H'
		elif self.disp == numdisp.DEC: string = f'{value}'
		elif self.disp == numdisp.OCT: string = f'{value:o}O'
		elif self.disp == numdisp.BIN: string = f'{value:b}B'
		if string[0] == '-':
			if not string[1].isnumeric(): string = f'-0{string[1:]}'
		elif not string[0].isnumeric(): string = f'0{string[1:]}'
		return '#' + string if self.imm else string
	def __setattr__(self, name, value):
		if name in ('bits', 'value'): raise AttributeError(f"attribute '{name}' of '{type(self).__name__}' objects is not writable")
		else: super().__setattr__(name, value)

class Pointer:
	__slots__ = ('disp', 'register')
	def __init__(self, register, disp = None):
		if type(register) not in (Register, str): raise TypeError("'register' argument must be of type Register or str")
		elif disp is not None and type(disp) != Num: raise TypeError("'disp' argument must be of type NoneType or Num")
		super().__setattr__('register', register)
		super().__setattr__('disp', disp)

	def __repr__(self): return f'{type(self).__name__}(register={repr(self.register)}, disp={repr(self.disp)})'
	def __str__(self): return f'{"" if self.disp is None else self.disp}[{self.register}]'

class Address:
	__slots__ = ('addr', 'seg')
	def __init__(self, addr, seg = None):
		if type(addr) != int: raise TypeError("'addr' argument must be of type int")
		elif seg is not None and type(seg) != int: raise TypeError("'seg' argument must be of type NoneType or int")
		super().__setattr__('addr', addr)
		super().__setattr__('seg', seg if seg is None else seg & 0xf)

	def __repr__(self): return f'{type(self).__name__}(addr={self.addr}{"" if self.seg is None else ", seg="+str(self.seg)})'
	def __str__(self):
		addr_fmt = format(self.addr, '04X')
		string = f'{"" if addr_fmt[0].isnumeric() else "0"}{addr_fmt}H'
		if self.seg is not None:
			seg_fmt = format(self.seg, 'X')
			string = f'{"" if seg_fmt[0].isnumeric() else "0"}{seg_fmt}:' + string
		return string

class DSRPrefix:
	__slots__ = ('dsr', 'item')
	def __init__(self, dsr, item):
		if dsr != 'DSR' and type(dsr) not in (Register, Num): raise TypeError("'dsr' argument must be of type Register, Num or str (= 'DSR')")
		elif type(item) not in (Pointer, Address): raise TypeError("'seg' argument must be of type Pointer or Address")
		super().__setattr__('dsr', dsr)
		super().__setattr__('item', item)

	def __repr__(self): return f'{type(self).__name__}(dsr={self.dsr}, item={self.item})'
	def __str__(self): return f'{self.dsr}:{self.item}'

def RegHandler(self, flags, value): return Register(flags & 0xf, value)

def NumHandler(self, flags, value): return Num(flags, value)

def RegCtrlHandler(self, flags, value):
	flags &= 0xf
	if flags == 0: return 'ECSR'
	elif flags == 1: return 'ELR'
	elif flags == 2: return 'PSW'
	elif flags == 3: return 'EPSW'
	elif flags == 4: return 'SP'
	elif flags == 6: return 'DSR'

def MemHandler(self, flags, value):
	s = (flags >> 12) & 0xf
	d = (flags >> 8) & 0xf
	e = (flags >> 4) & 0xf
	r = flags & 0xf

	if s & 8 and r == 1: return Pointer('EA+')
	if d == 0: disp = None
	elif d == 1: disp = Num(16, self.fetch())
	elif d == 2: disp = Num(e+1, value)
	if r == 0 and disp is not None: return Address(disp.value)
	elif r > 0:
		if r == 1: reg = 'EA'
		elif r == 2: reg = Register(2, value)
		elif r == 3: reg = Register(2, 12)
		elif r == 4: reg = Register(2, 14)
		return Pointer(reg, disp)

	raise RuntimeError

def CondHandler(self, flags, value):
	if value == 0: return 'GE'
	elif value == 1: return 'LT'
	elif value == 2: return 'GT'
	elif value == 3: return 'LE'
	elif value == 4: return 'GES'
	elif value == 5: return 'LTS'
	elif value == 6: return 'GTS'
	elif value == 7: return 'LES'
	elif value == 8: return 'NE'
	elif value == 9: return 'EQ'
	elif value == 0xa: return 'NV'
	elif value == 0xb: return 'OV'
	elif value == 0xc: return 'PS'
	elif value == 0xd: return 'NS'
	elif value == 0xe: return 'AL'

	raise RuntimeError

def CadrHandler(self, flags, value): return Address(self.fetch(), value)
def RadrHandler(self, flags, value): return Address((self.pc+conv_sign(value, 8)*2) & 0xfffe, self.pc >> 16)

def PushHandler(self, flags, value):
	regs = []
	if value & 2: regs.append('ELR')
	if value & 4: regs.append('EPSW')
	if value & 8: regs.append('LR')
	if value & 1: regs.append('EA')

	if len(regs) == 0: raise RuntimeError
	return regs

def PopHandler(self, flags, value):
	regs = []
	if value & 1: regs.append('EA')
	if value & 8: regs.append('LR')
	if value & 4: regs.append('PSW')
	if value & 2: regs.append('PC')

	if len(regs) == 0: raise RuntimeError
	return regs

class Disassembly:
	__instrs_dsr = [
		# DSR Prefix Instructions
		[None, 0xe300, [0x00ff, 0,  0x0008, NumHandler]],
		[None, 0x900f, [0x00f0, 4,  0x0001, RegHandler]],
		[None, 0xfe9f, [0x0000, 0,  0x0006, RegCtrlHandler]],
	]

	__instrs = [
		# original from https://github.com/gamingwithevets/u8_emu/blob/main/src/core/instr.c
		
		#                               op0                                      op1
		# [mnemonic, mask,  [mask, shift, flags, handler],          [mask, shift, flags, handler]]

		# Arithmetic Instructions
		['ADD',		0x8001,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['ADD',		0x1000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]],
		['ADD',		0xf006, [0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x0002, RegHandler]],
		['ADD',		0xe080, [0x0e00, 8,  0x0002, RegHandler],		[0x007f, 0,  0x0006, NumHandler]],
		['ADDC',	0x8006,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['ADDC',	0x6000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]],
		['AND',		0x8002,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['AND',		0x2000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]],
		['CMP',		0x8007,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['CMP',		0x7000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]],
		['CMPC',	0x8005,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['CMPC',	0x5000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]],
		['MOV',		0xf005,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x0002, RegHandler]],
		['MOV',		0xe000,	[0x0e00, 8,  0x0002, RegHandler],		[0x007f, 0,  0x0006, NumHandler]],
		['MOV',		0x8000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['MOV',		0x0000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]],
		['OR',		0x8003,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['OR',		0x3000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]],
		['XOR',		0x8004,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['XOR',		0x4000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00ff, 0,  0x0008, NumHandler]],
		['CMP',		0xf007,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x0002, RegHandler]],
		['SUB',		0x8008,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['SUBC',	0x8009,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],

		# Shift Instructions
		['SLL',		0x800a,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['SLL',		0x900a,	[0x0f00, 8,  0x0001, RegHandler],		[0x0070, 4,  0x0003, NumHandler]],
		['SLLC',	0x800b,	[0x0f00, 8,  0x0012, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['SLLC',	0x900b,	[0x0f00, 8,  0x0012, RegHandler],		[0x0070, 4,  0x0003, NumHandler]],
		['SRA',		0x800e,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['SRA',		0x900e,	[0x0f00, 8,  0x0001, RegHandler],		[0x0070, 4,  0x0003, NumHandler]],
		['SRL',		0x800c,	[0x0f00, 8,  0x0001, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['SRL',		0x900c,	[0x0f00, 8,  0x0001, RegHandler],		[0x0070, 4,  0x0003, NumHandler]],
		['SRLC',	0x800d,	[0x0f00, 8,  0x0002, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['SRLC',	0x900d,	[0x0f00, 8,  0x0002, RegHandler],		[0x0070, 4,  0x0003, NumHandler]],

		# Load/Store Instructions
		['L',		0x9032,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x1001, MemHandler]],
		['L',		0x9052,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x9001, MemHandler]],
		['L',		0x9002,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x1002, MemHandler]],
		['L',		0xa008,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x1102, MemHandler]],
		['L',		0xb000,	[0x0e00, 8,  0x0002, RegHandler],		[0x003f, 0,  0x1253, MemHandler]],
		['L',		0xb040,	[0x0e00, 8,  0x0002, RegHandler],		[0x003f, 0,  0x1254, MemHandler]],
		['L',		0x9012,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x1100, MemHandler]],
		['L',		0x9030,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0001, MemHandler]],
		['L',		0x9050,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x8001, MemHandler]],
		['L',		0x9000,	[0x0f00, 8,  0x0001, RegHandler],		[0x00e0, 4,  0x0002, MemHandler]],
		['L',		0x9008,	[0x0f00, 8,  0x0001, RegHandler],		[0x00e0, 4,  0x0102, MemHandler]],
		['L',		0xd000,	[0x0f00, 8,  0x0001, RegHandler],		[0x003f, 0,  0x0253, MemHandler]],
		['L',		0xd040,	[0x0f00, 8,  0x0001, RegHandler],		[0x003f, 0,  0x0254, MemHandler]],
		['L',		0x9010,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0100, MemHandler]],
		['L',		0x9034,	[0x0c00, 8,  0x0004, RegHandler],		[0x0000, 0,  0x3001, MemHandler]],
		['L',		0x9054,	[0x0c00, 8,  0x0004, RegHandler],		[0x0000, 0,  0xB001, MemHandler]],
		['L',		0x9036,	[0x0800, 8,  0x0008, RegHandler],		[0x0000, 0,  0x7001, MemHandler]],
		['L',		0x9056,	[0x0800, 8,  0x0008, RegHandler],		[0x0000, 0,  0xF001, MemHandler]],

		['ST',		0x9033,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x1001, MemHandler]],
		['ST',		0x9053,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x9001, MemHandler]],
		['ST',		0x9003,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x1002, MemHandler]],
		['ST',		0xa009,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x1102, MemHandler]],
		['ST',		0xb080,	[0x0e00, 8,  0x0002, RegHandler],		[0x003f, 0,  0x1253, MemHandler]],
		['ST',		0xb0c0,	[0x0e00, 8,  0x0002, RegHandler],		[0x003f, 0,  0x1254, MemHandler]],
		['ST',		0x9013,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x1100, MemHandler]],
		['ST',		0x9031,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0001, MemHandler]],
		['ST',		0x9051,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x8001, MemHandler]],
		['ST',		0x9001,	[0x0f00, 8,  0x0001, RegHandler],		[0x00e0, 4,  0x0002, MemHandler]],
		['ST',		0x9009,	[0x0f00, 8,  0x0001, RegHandler],		[0x00e0, 4,  0x0102, MemHandler]],
		['ST',		0xd080,	[0x0f00, 8,  0x0001, RegHandler],		[0x003f, 0,  0x0253, MemHandler]],
		['ST',		0xd0c0,	[0x0f00, 8,  0x0001, RegHandler],		[0x003f, 0,  0x0254, MemHandler]],
		['ST',		0x9011,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0100, MemHandler]],
		['ST',		0x9035,	[0x0c00, 8,  0x0004, RegHandler],		[0x0000, 0,  0x3001, MemHandler]],
		['ST',		0x9055,	[0x0c00, 8,  0x0004, RegHandler],		[0x0000, 0,  0xB001, MemHandler]],
		['ST',		0x9037,	[0x0800, 8,  0x0008, RegHandler],		[0x0000, 0,  0x7001, MemHandler]],
		['ST',		0x9057,	[0x0800, 8,  0x0008, RegHandler],		[0x0000, 0,  0xF001, MemHandler]],

		# Control RegHandler Access Instructions
		['ADD',		0xe100,	[0x0000, 0,  0x0024, RegCtrlHandler],	[0x00ff, 0,  0x0007, NumHandler]],
		['MOV',		0xa00f,	[0x0000, 0,  0x0010, RegCtrlHandler],	[0x00f0, 4,  0x0001, RegHandler]],
		['MOV',		0xa00d,	[0x0000, 0,  0x0021, RegCtrlHandler],	[0x0f00, 8,  0x0002, RegHandler]],
		['MOV',		0xa00c,	[0x0000, 0,  0x0013, RegCtrlHandler],	[0x00f0, 4,  0x0001, RegHandler]],
		['MOV',		0xa005,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x0021, RegCtrlHandler]],
		['MOV',		0xa01a,	[0x0e00, 8,  0x0002, RegHandler],		[0x0000, 0,  0x0024, RegCtrlHandler]],
		['MOV',		0xa00b,	[0x0000, 0,  0x0012, RegCtrlHandler],	[0x00f0, 4,  0x0001, RegHandler]],
		['MOV',		0xe900,	[0x0000, 0,  0x0012, RegCtrlHandler],	[0x00ff, 0,  0x0008, NumHandler]],
		['MOV',		0xa007,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0010, RegCtrlHandler]],
		['MOV',		0xa004,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0013, RegCtrlHandler]],
		['MOV',		0xa003,	[0x0f00, 8,  0x0001, RegHandler],		[0x0000, 0,  0x0012, RegCtrlHandler]],
		['MOV',		0xa10a,	[0x0000, 0,  0x0024, RegCtrlHandler],	[0x00e0, 4,  0x0002, RegHandler]],

		# Push/Pop Instructions
		['PUSH',	0xf05e,	[0x0e00, 8,  0x0002, RegHandler],		None],
		['PUSH',	0xf07e,	[0x0800, 8,  0x0008, RegHandler],		None],
		['PUSH',	0xf04e,	[0x0f00, 8,  0x0001, RegHandler],		None],
		['PUSH',	0xf06e,	[0x0c00, 8,  0x0004, RegHandler],		None],
		['PUSH',	0xf0ce,	[0x0f00, 8,  0x0008, PushHandler],		None],
		['POP',		0xf01e,	[0x0e00, 8,  0x0002, RegHandler],		None],
		['POP',		0xf03e,	[0x0800, 8,  0x0008, RegHandler],		None],
		['POP',		0xf00e,	[0x0f00, 8,  0x0001, RegHandler],		None],
		['POP',		0xf02e,	[0x0c00, 8,  0x0004, RegHandler],		None],
		['POP',		0xf08e,	[0x0f00, 8,  0x0008, PopHandler],		None],

		# TODO: Coprocessor Instructions

		# EA RegHandler Data Transfer Instructions
		['LEA',		0xf00a,	[0x00e0, 4,  0x0002, MemHandler],		None],
		['LEA',		0xf00b,	[0x00e0, 4,  0x0102, MemHandler],		None],
		['LEA',		0xf00c,	[0x0000, 0,  0x0100, MemHandler],		None],

		# ALU Instructions
		['DAA',		0x801f,	[0x0f00, 8,  0x0001, RegHandler],		None],
		['DAS',		0x803f,	[0x0f00, 8,  0x0001, RegHandler],		None],
		['NEG',		0x805f,	[0x0f00, 8,  0x0001, RegHandler],		None],

		# Bit Access Instructions
		['SB',		0xa000,	[0x0f00, 8,  0x0001, RegHandler],		[0x0070, 4,  0x0003, NumHandler]],
		['SB',		0xa080,	[0x0000, 0,  0x0100, MemHandler],		[0x0070, 4,  0x0003, NumHandler]],
		['RB',		0xa002,	[0x0f00, 8,  0x0001, RegHandler],		[0x0070, 4,  0x0003, NumHandler]],
		['RB',		0xa082,	[0x0000, 0,  0x0100, MemHandler],		[0x0070, 4,  0x0003, NumHandler]],
		['TB',		0xa001,	[0x0f00, 8,  0x0001, RegHandler],		[0x0070, 4,  0x0003, NumHandler]],
		['TB',		0xa081,	[0x0000, 0,  0x0100, MemHandler],		[0x0070, 4,  0x0003, NumHandler]],

		# PSW Access Instructions
		['EI',		0xed08,	None,									None],
		['DI',		0xebf7,	None,									None],
		['SC',		0xed80,	None,									None],
		['RC',		0xeb7f,	None,									None],
		['CPLC',	0xfecf,	None,									None],

		# Conditional Relative Branch Instructions
		['BC',		0xc000,	[0x0f00, 8,	 0x0000, CondHandler],		[0x00ff, 0,  0x0007, RadrHandler]],

		# Sign Extension Instruction
		['EXTBW',	0x810f,	[0x0e00, 8,  0x0002, RegHandler],		[0x00e0, 4,  0x0002, RegHandler]],

		# Software Interrupt Instructions
		['SWI',		0xe500,	[0x003f, 0,  0x0008, NumHandler],		None],
		['BRK',		0xffff,	None,									None],

		# Branch Instructions
		['B',		0xf000,	[0x0f00, 8,  0x0004, CadrHandler],		None],
		['B',		0xf002,	[0x00e0, 4,  0x0002, RegHandler],		None],
		['BL',		0xf001,	[0x0f00, 8,  0x0004, CadrHandler],		None],
		['BL',		0xf003,	[0x00e0, 4,  0x0002, MemHandler],		None],

		# Multiplication and Division Instructions
		['MUL',		0xf004,	[0x0e00, 8,  0x0002, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],
		['DIV',		0xf009,	[0x0e00, 8,  0x0002, RegHandler],		[0x00f0, 4,  0x0001, RegHandler]],

		# Miscellaneous Instructions
		['INC',		0xfe2f,	[0x0000, 0,  0x0001, MemHandler],		None],
		['DEC',		0xfe3f,	[0x0000, 0,  0x0001, MemHandler],		None],
		['RT',		0xfe1f,	None,									None],
		['RTI',		0xfe0f,	None,									None],
		['NOP',		0xfe8f,	None,									None],

		# Internal Instructions (undocumented)
		['RTICE',	0xfe6f,	None,									None],  # RTI for emulator software interrupt handler
		['RTICEPSW',0xfe7f,	None,									None],  # Equivalent to POP PSW; RTICE?
		['ICESWI',	0xfeff,	None,									None],  # Triggers emulator software interrupt
	]

	def __init__(self, code_bytes):
		if type(code_bytes) not in (bytes, bytearray): raise TypeError("'code_bytes' argument must be a bytes-like object")
		if len(code_bytes) % 2 != 0: raise ValueError("'code_bytes' argument must have even length")

		self.code = {}
		self.labels = {}
		
		self.__code_bytes = code_bytes
		self.pc = 0
		self.__queue = []
		self.__instrl = []

	def disassemble(self):
		self.labels[self.read_word(2)] = [labeltype.FUN, 'start']
		self.__queue.append(self.read_word(2))
		instr = None
		prev_instr = None
		dsr_src = None

		while len(self.__queue) > 0:
			prev_instr = instr

			self.pc = self.__queue.pop()
			if self.pc in self.__queue: self.__queue.remove(self.pc)
			instr_bytes = self.fetch()
			try:
				_instr, dsr = self.decode(instr_bytes)
				if dsr:
					if _instr[2][3] == RegCtrlHandler: instr = ['EDSR']
					else: instr = ['DW', Num(16, instr_bytes, False)]
					dsr_src = _instr[2][3](self, _instr[2][2], (instr_bytes & _instr[2][0]) >> _instr[2][1])
					self.__queue.append(self.pc)
					continue
				else:
					instr = [_instr[0]]
					if _instr[2] is not None: instr.append(_instr[2][3](self, _instr[2][2], (instr_bytes & _instr[2][0]) >> _instr[2][1]))
					if _instr[3] is not None: instr.append(_instr[3][3](self, _instr[3][2], (instr_bytes & _instr[3][0]) >> _instr[3][1]))
					if len(instr) > 1 and type(instr[-1]) in (Address, Pointer) and _instr[len(instr)][3] == MemHandler and dsr_src is not None:
						instr[-1] = DSRPrefix(dsr_src, instr[-1])
						dsr_src = None
			except RuntimeError: instr = ['DW', Num(16, instr_bytes, False)]

			ins_len = len(self.__instrl)*2
			if dsr_src is None: self.code[self.pc-ins_len] = [self.__instrl, instr]
			else:
				self.code[self.pc-ins_len] = [[self.__instrl[0]], prev_instr]
				self.code[self.pc-ins_len+2] = [self.__instrl[1:], prev_instr]
				dsr_src = None

			self.__instrl = []
			
			if (instr[0] == 'B' and type(instr[1]) == Address) or instr[0] == 'BC':
				radr = (instr[-1].seg << 16) | instr[-1].addr
				if radr not in self.labels: self.labels[radr] = [labeltype.LAB, f'LAB_{radr:05X}']
				self.queue_add(radr)
				if instr[0] == 'BC' and instr[1] != 'AL': self.queue_add(self.pc)
			elif instr[0] == 'BL' and type(instr[1]) == Address:
				cadr = (instr[-1].seg << 16) | instr[-1].addr
				if cadr not in self.labels or (cadr in self.labels and self.labels[cadr][0] == labeltype.LAB): self.labels[cadr] = [labeltype.FUN, f'FUN_{cadr:05X}']
				self.queue_add(self.pc)
				self.queue_add(cadr)
			elif instr[0] == 'RT' or instr[0] == 'RTI': pass
			else: self.queue_add(self.pc)

		self.code = dict(sorted(self.code.items()))

	def queue_add(self, addr):
		addr %= len(self.__code_bytes)
		addr &= 0xffffe
		if addr not in self.code:
			self.__queue.append(addr)
			if self.__queue.count(addr) > 1: self.__queue.remove(addr)

	def read_word(self, addr): return (self.__code_bytes[addr+1] << 8) | self.__code_bytes[addr]

	def fetch(self):
		a = self.read_word(self.pc)
		self.__instrl.append(a)
		self.pc += 2
		return a

	def decode(self, instr):
		for _instr in self.__instrs_dsr:
			mask = 0
			if _instr[2] is not None: mask |= _instr[2][0]
			mask ^= 0xffff

			if instr & mask == _instr[1]: return _instr, True

		for _instr in self.__instrs:
			mask = 0
			if _instr[2] is not None: mask |= _instr[2][0]
			if _instr[3] is not None: mask |= _instr[3][0]
			mask ^= 0xffff

			if instr & mask == _instr[1]: return _instr, False

		raise RuntimeError

	def __repr__(self): return f'{type(self).__name__}(code_bytes=<{type(code_bytes).__name__}({len(code_bytes)})>)'
