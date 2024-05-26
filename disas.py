from enum import IntEnum

class numdisp(IntEnum):
	HEX = 0
	DEC = 1
	OCT = 2
	BIN = 3

class Register:
	__reg_prefixes = {1: 'R', 2: 'ER', 4: 'XR', 8: 'QR'}
	__slots__ = ('size', 'n')
	def __init__(self, size, n):
		if size not in self.__reg_prefixes.keys(): raise ValueError('invalid register size')
		if n not in range(0, 16, size): raise ValueError('invalid value for n')
		super().__setattr__('size', size)
		super().__setattr__('n', n)

	def __repr__(self): return f'Register(size={self.size}, n={self.n})'
	def __str__(self): return f'{self.__reg_prefixes[self.size]}{self.n}'
	def __setattr__(self, name, value): raise AttributeError(f"attribute '{name}' of '{type(self).__name__}' objects is not writable")

class RegisterBit:
	__slots__ = ('register', 'bit')
	def __init__(self, register, bit):
		if type(register) != Register: raise TypeError(f'expected Register, got {type(register).__name__}')
		elif register.size != 1: raise TypeError(f'expected Register of size 1, got Register of size {register.size}')
		if bit not in range(8): raise ValueError('bit offset must be between 0-7')
		super().__setattr__('register', register)
		super().__setattr__('bit', bit)

	def __repr__(self): return f'RegisterBit(register={self.register}, bit={self.bit})'
	def __str__(self): return f'{self.register}.{self.bit}'
	def __setattr__(self, name, value): raise AttributeError(f"attribute '{name}' of '{type(self).__name__}' objects is not writable")

class Num:
	__slots__ = ('bits', 'value', 'disp', 'sign')
	def __init__(self, bits, value):
		if bits < 1: raise ValueError('invalid bit length')
		elif type(value) == float: raise TypeError('immediate type cannot be float')
		super().__setattr__('bits', bits)
		super().__setattr__('value', value & (2**bits))
		self.disp = numdisp.HEX
		self.sign = True

	def __repr__(self): return f'Num(bits={self.bits}, value={self.value}, disp={numdisp(self.disp).name})'
	def __str__(self):
		value = self.value - (self.value >> (bits - 1)) * (2**bits) if self.sign else self.value
		if self.disp == numdisp.HEX: return f'#{value:X}H'
		elif self.disp == numdisp.DEC: return f'#{value}'
		elif self.disp == numdisp.OCT: return f'#{value:o}O'
		elif self.disp == numdisp.BIN: return f'#{value:b}B'
	def __setattr__(self, name, value):
		if name in ('bits', 'value'): raise AttributeError(f"attribute '{name}' of '{type(self).__name__}' objects is not writable")
		else: super().__setattr__(name, value)

class Num8(Num):
	def __init__(self, value): super().__init__(8, value)

class Num7(Num):
	def __init__(self, value): super().__init__(7, value)
