import sys
if sys.version_info < (3, 8, 0):
	print('This program requires at least Python 3.8.0. (You are running Python ' + platform.python_version() + ')')
	sys.exit()

import os
import io
import math
import disas
import logging
import functools

try:
	import labeltool.labeltool as labeltool
	import dcl
	has_labeltool = True
except ImportError: has_labeltool = False

try:
	from colorama import init, Fore, Style
	has_colorama = True
except ImportError: has_colorama = False

if has_colorama: init(autoreset = True)
GREEN = Fore.GREEN if has_colorama else ''
RED = Fore.RED if has_colorama else ''
DARK_GRAY = Fore.LIGHTBLACK_EX if has_colorama else ''
CYAN = Fore.CYAN if has_colorama else ''
YELLOW = Fore.YELLOW if has_colorama else ''
LIGHT_BLUE = Fore.BLUE if has_colorama else ''
END = Style.RESET_ALL if has_colorama else ''

logging.basicConfig(format = f'{DARK_GRAY}[%(asctime)s] [%(filename)s:%(funcName)s:%(lineno)d] %(levelname)s: {END}%(message)s', datefmt = '%d/%m/%Y %H:%M:%S', level = logging.INFO)
logging.addLevelName(logging.INFO, f'{LIGHT_BLUE}INFO')
logging.addLevelName(logging.WARNING, f'{YELLOW}WARNING')
logging.addLevelName(logging.ERROR, f'{RED}ERROR')
logging.addLevelName(logging.DEBUG, f'{CYAN}DEBUG')

def process_ins_param(dis, param, is_lea = False, data_bit_labels = None):
	if data_bit_labels is None: data_bit_labels = {}
	if type(param) == list: return ', '.join(param)
	elif type(param) == disas.Address:
		if param.seg is None:
			addr = param.addr.value
			if addr in dis.data_labels: return dis.data_labels[addr]
		else:
			addr = (param.seg.value << 16) | param.addr.value
			if addr in dis.labels: return dis.labels[addr][1]
	elif type(param) == disas.DSRPrefix:
		if type(param.dsr) == disas.Num and type(param.item) == disas.Num:
			addr = (param.dsr.value << 16) | param.item.value
			if addr in dis.data_labels: return dis.data_labels[addr]
	elif type(param) == disas.BitOffset and type(param.item) == disas.Address:
		addr = param.item.addr.value
		if addr in dis.data_labels:
			s = f'{dis.data_labels[addr]}.{param.bit}'
			if s in data_bit_labels: return data_bit_labels[s]
			else: return s
	elif type(param) == disas.Pointer and not is_lea and type(param.disp) == disas.Num and type(param.register) == disas.Register and param.register.n in (12, 14) and param.register.size == 2:
		val = param.disp.get()
		if param.disp.bits == 16 and ((val >= 0 and val <= 0x1f) or (val >= -0x20 and val < 0)):
			param.register.ptr = False
			return str(param) + '  ;  Disp16 used instead of Disp6'

	return str(param)

@functools.lru_cache
def get_byte(b):
	fmt = f'{b:3X}H'
	if b >= 0xa and b <= 0xf: fmt = ' 0' + fmt[2:]
	elif b >= 0xa0: fmt = '0' + fmt[1:]
	return fmt

def log_exc(func, exc):
	if issubclass(type(exc), OSError):
		if os.name == 'nt':
			if exc.winerror: errno = f'WE{exc.winerror}'
			else: errno = exc.errno
		else: errno = exc.errno
		func(f'[{type(exc).__name__}] {exc.filename}{", "+exc.filename2 if exc.filename2 else ""}: {exc.strerror} ({errno})')
	else: func(f'[{type(exc).__name__}] {exc}')

def disassemble(filename, out, labelfile = '', dclfile = '', romwin = None, addresses = False, disas_all = False):
	logging.info('Loading binary')
	size = 0
	rom = b''
	try:
		with open(filename, 'rb') as f:
			rom = f.read()
			size = len(rom)
			dis = disas.Disassembly(rom)
	except Exception as e:
		log_exc(logging.error, e)
		return
	num_segs = math.ceil(size / 0x10000)

	sfr_labels = {}
	dcl_name = 'foo'
	data_bit_labels = {}

	interrupts = {}
	if dclfile:
		logging.info('Loading DCL file')
		try:
			reader = dcl.DCLReader(dclfile)
			reader.parse()
			for k, v in reader.data_labels.items():
				dis.data_labels[k] = v
				sfr_labels[k] = v
			for k, v in reader.data_bit_labels.items(): data_bit_labels[k] = v
			dcl_name = os.path.splitext(os.path.basename(dclfile))[0]
			if romwin is None: romwin = reader.romwin
			interrupts = dict(sorted(reader.interrupts.items()))
		except Exception as e: log_exc(logging.warning, e)
	else:
		if romwin is None: romwin = 0

	if labelfile:
		logging.info('Loading label files')
		for file in labelfile:
			try:
				with open(file) as f: labels, data_labels, _data_bit_labels = labeltool.load_labels(f, 0)
				for k, v in labels.items():
					if v[1]: dis.labels[k] = [disas.labeltype.FUN, ('' if v[0].endswith('u8') or (v[0].endswith('_n') and not v[0].endswith('base_n')) or v[0].endswith('_nn') else '_')+v[0].replace('.', '_')]
					else: dis.labels[k] = [disas.labeltype.LAB, f'_${labels[v[2]][0]}_{v[0][1:]}']
				for k, v in data_labels.items():
					name = '_' + v.replace('.', '_')
					if v == f'd_{k:05X}':
						if k >= romwin: dis.data_labels[k] = name
						else: dis.data_labels[k] = f'_unk_{k:05x}'
					else: dis.data_labels[k] = name
				for k, v in _data_bit_labels.items(): data_bit_labels[k] = '_' + v
			except Exception as e: log_exc(logging.warning, e)
	logging.info('Disassembling')
	dis.disassemble()
	logging.info('Disassembling vector table')
	for addr in interrupts:
		dis.queue_add(addr)
		func_addr = dis.read_word(addr)
		if func_addr not in dis.labels: dis.labels[func_addr] = [disas.labeltype.FUN, f'int_{interrupts[addr]}']
	dis.disassemble()
	if disas_all:
		logging.info('Adding undetected functions to queue')
		for addr in dis.labels:
			if addr not in dis.code: dis.queue_add(addr)
		logging.info('Disassembling undetected functions')
		dis.disassemble()

	f = io.StringIO()
	logging.info('Writing initialization directives')
	f.write(f'TYPE({dcl_name})\nMODEL {"SMALL" if size <= 0x10000 else "LARGE"}\nROMWINDOW 0, {romwin-1:05X}H\n\n')

	logging.info('Writing symbol definitions')
	l = math.ceil(max(len(v) for v in dis.data_labels.values()) / 4) * 4
	equs = ''
	table_dt = {}
	dis.data_labels = dict(sorted(dis.data_labels.items()))
	for k, v in dis.data_labels.items():
		if k in sfr_labels: continue
		tabs = '\t'*math.ceil((l - len(v)) / 4)
		if not tabs: tabs = '\t'
		if k >= romwin: equs += f'{v}{tabs}EQU {"" if hex(k)[2].isnumeric() else "0"}{k:04X}H\n'
		else: table_dt[k] = v

	f.write(equs)

	logging.info('Writing disassembly')
	tab = '\t'
	for seg in range(num_segs):
		table_mode = seg == 0
		tbytes_line = 0
		tbytes_mode = False
		skip_byte = 0
		f.write(f'\n{"T" if table_mode else "C"}SEG #{seg} AT 0\n\n')
		for addr16 in range(0x10000):
			if not table_mode and addr16 % 2 != 0: continue
			if skip_byte:
				skip_byte -= 1
				continue
			addr = (seg << 16) + addr16
			if addr < 6:
				if not table_mode:
					if addr < romwin: f.write(f'\nTSEG #{seg} AT {addr:05X}H\n')
					table_mode = True
					tbytes_line = 0
				elif tbytes_mode:
					if tbytes_line > 0: f.write('\n\n')
					tbytes_mode = False
					tbytes_line = 0
				if addr == 0: f.write(f'; Initial SP\n{"/*"+tab+"00000"+tab+"*/ " if addresses else tab}DW {disas.Address(dis.read_word(0))}\n')
				elif addr == 2: f.write(f'; Entry point\n{"/*"+tab+"00002"+tab+"*/ " if addresses else tab}DW {process_ins_param(dis, disas.Address(dis.read_word(2), 0))}\n')
				elif addr == 4: f.write(f'; BRK interrupt entry point\n{"/*"+tab+"00004"+tab+"*/ " if addresses else tab}DW {process_ins_param(dis, disas.Address(dis.read_word(4), 0))}\n')
				skip_byte = 1
			elif addr in interrupts:
				if not table_mode:
					if addr < romwin: f.write(f'\nTSEG #{seg} AT {addr:05X}H\n\n')
					table_mode = True
					tbytes_line = 0
				elif tbytes_mode:
					if tbytes_line > 0: f.write('\n\n')
					tbytes_mode = False
					tbytes_line = 0
				f.write(f'; Interrupt: {interrupts[addr]}\n{"/*"+tab+format(addr, "05X")+tab+"*/ " if addresses else tab}DW {process_ins_param(dis, disas.Address(dis.read_word(addr), 0))}\n\n')
				skip_byte = 1
			elif addr in dis.jump_tables:
				if not table_mode:
					if addr < romwin: f.write(f'\nTSEG #{seg} AT {addr:05X}H\n')
					table_mode = True
					tbytes_line = 0
				elif tbytes_mode:
					if tbytes_line > 0: f.write('\n\n')
					else: f.write('\n')
					tbytes_mode = False
					tbytes_line = 0
				entry = dis.jump_tables[addr]
				size = entry[0]
				f.write(f'; {addr:05X}\n{dis.data_labels[addr]}:\n')
				if entry[1]:
					_size = 0
					for a in range(addr, addr+size*4, 4):
						func_name = process_ins_param(dis, disas.Address(dis.read_word(a), dis.read_word(a+2)))
						f.write(f'{"/*"+tab+format(a, "05X")+tab+"*/ " if addresses else tab}DW OFFSET ({func_name})\n')
						f.write(f'{"/*"+tab+format(a+2, "05X")+tab+"*/ " if addresses else tab}DW SEG ({func_name})\n')
						_size += 1
						if a+4 in dis.jump_tables or a+4 in dis.data_labels or a+4 in dis.code:
							size = _size
							break
					skip_byte = size * 4 - 1 if table_mode else size * 2 - 1
				else:
					s = entry[2]
					_size = 0
					for a in range(addr, addr+size*2, 2):
						f.write(f'{"/*"+tab+format(a, "05X")+tab+"*/ " if addresses else tab}DW {process_ins_param(dis, disas.Address(dis.read_word(a), s))}\n')
						_size += 1
						if a+2 in dis.jump_tables or a+2 in dis.data_labels or a+2 in dis.code:
							size = _size
							break
					skip_byte = size * 2 - 1 if table_mode else size - 1
				f.write('\n')
			elif addr in dis.code:
				if table_mode:
					if tbytes_mode:
						if tbytes_line > 0: f.write('\n')
						tbytes_mode = False
						tbytes_line = 0
					if addr < romwin: f.write(f'\nCSEG #{seg} AT {addr:05X}H\n')
					table_mode = False
				if addr in dis.labels:
					if dis.labels[addr][0] == disas.labeltype.FUN: f.write(f'\n; {addr:05X}\n')
					f.write(f'{dis.labels[addr][1]}:\n')
				ins = dis.code[addr]
				instrl = ins[0]
				instr = ins[1]
				#string = f'{addr >> 16:X}:{addr & 0xfffe:04X}H\t\t{"".join([format(a, "04X") for a in instrl])}{tab*(3-len(instrl))}\t{instr[0]}'
				if addresses:
					string = f'/*\t{addr:05X}\t{"".join([format(a, "04X") for a in instrl])}{tab*(3-len(instrl))} */ {instr[0]}'
				else: string = f'\t{instr[0]}'
				is_lea = instr[0] == 'LEA'
				if len(instr) >= 2: string += ' ' + process_ins_param(dis, instr[1], is_lea, data_bit_labels)
				if len(instr) == 3: string += ', ' + process_ins_param(dis, instr[2], is_lea, data_bit_labels)
				f.write(string + '\n')
				skip_byte = len(instrl) - 1
			else:
				if not table_mode:
					if addr < romwin: f.write(f'\nTSEG #{seg} AT {addr:05X}H\n\n')
					table_mode = True
					tbytes_line = 0
				if not tbytes_mode: tbytes_mode = True
				
				if addr in table_dt:
					if tbytes_line > 0: f.write('\n\n')
					tbytes_line = 0
					f.write(f'; {addr:05X}\n{table_dt[addr]}:\n')
				
				f.write(f'{"/*"+tab+format(addr, "05X")+tab+"*/ " if addresses else tab}DB ' if tbytes_line == 0 else ', ')
				f.write(get_byte(rom[addr]))
				tbytes_line += 1
				if tbytes_line == 16:
					f.write('\n')
					tbytes_line = 0

		if tbytes_mode: f.write('\n')

	f.write(f'\nEND\n')
	
	logging.info('Copying disassembly to file')
	with open(out, 'w') as g: g.write(f.getvalue())

	logging.info('Done.')

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(description = 'PyU8disasX command line auto-disassembler.\nDisassembly is compatible with RASU8.', epilog = f'© 2024-2026 GamingWithEvets Inc. Licensed under GPL-v3', formatter_class = argparse.RawDescriptionHelpFormatter)
	parser.add_argument('file', help = 'filename of ROM to disassemble')

	gr_disas = parser.add_argument_group(f'disassembler {"and labels" if has_labeltool else "options"}')
	gr_disas.add_argument('-r', '--romwin', type = lambda x: int(x, 0), help = f'ROM window size. if unspecified{" and no DCL file is loaded," if has_labeltool else ""} or ROM window is 0, no ROM window will be present{". if specified, overrides DCL specification" if has_labeltool else ""}')
	if has_labeltool:
		gr_disas.add_argument('-l', '--label', action = 'append', help = 'add a label file. data labels override DCL specification and are added to the symbol definitions')
		gr_disas.add_argument('-d', '--dcl', help = 'load a DCL file. if unspecified, default DCL name will be "foo"')
		gr_disas.add_argument('--all', action = 'store_true', help = 'disassemble all functions listed in all provided label files')

	gr_output = parser.add_argument_group('output options')
	gr_output.add_argument('-o', '--output', help = 'filename of output assembly file (default: ROM filename with ASM extension)')
	gr_output.add_argument('-a', '--addresses', action = 'store_true', help = 'add addresses and raw bytes/words to disassembly')
	
	gr_misc = parser.add_argument_group('miscellaneous')
	gr_misc.add_argument('--debug', action = 'store_true', help = 'enable debug logs')

	args = parser.parse_args()

	if args.debug: logging.basicConfig(format = f'{DARK_GRAY}[%(asctime)s] [%(filename)s:%(funcName)s:%(lineno)d] %(levelname)s: {END}%(message)s', datefmt = '%d/%m/%Y %H:%M:%S', level = logging.DEBUG, force = True)

	if args.output is None: output = os.path.splitext(args.file)[0] + '.asm'
	else: output = args.output

	if has_labeltool: disassemble(args.file, output, args.label, args.dcl, args.romwin, args.addresses, args.all)
	else: disassemble(args.file, output, romwin = args.romwin, addresses = args.addresses)
