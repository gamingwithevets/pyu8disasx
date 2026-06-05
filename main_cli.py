import sys, os
import math
import disas
import labeltool.labeltool as labeltool
import dcl
import logging
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

def process_ins_param(dis, param, is_lea, data_bit_labels):
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

def log_exc(func, exc):
	if issubclass(type(exc), OSError):
		if os.name == 'nt':
			if exc.winerror: errno = f'WE{exc.winerror}'
			else: errno = exc.errno
		else: errno = exc.errno
		func(f'[{type(exc).__name__}] {exc.filename}{", "+exc.filename2 if exc.filename2 else ""}: {exc.strerror} ({errno})')
	else: func(f'[{type(exc).__name__}] {exc}')

def disassemble(filename, out, labelfile, dclfile, romwin = None, addresses = False):
	logging.info('Loading binary')
	size = 0
	try:
		with open(filename, 'rb') as f:
			b = f.read()
			size = len(b)
			dis = disas.Disassembly(b)
	except Exception as e:
		log_exc(logging.error, e)
		return

	sfr_labels = {}
	dcl_name = 'foo'
	data_bit_labels = {}
	if labelfile:
		logging.info('Loading label files')
		for file in labelfile:
			try:
				with open(file) as f: labels, data_labels, _data_bit_labels = labeltool.load_labels(f, 0)
				for k, v in labels.items():
					if v[1]: dis.labels[k] = [disas.labeltype.FUN, ('' if v[0].endswith('u8') or (v[0].endswith('_n') and not v[0].endswith('base_n')) or v[0].endswith('_nn') else '_')+v[0].replace('.', '_')]
					else: dis.labels[k] = [disas.labeltype.LAB, f'_${labels[v[2]][0]}_{v[0][1:]}']
				for k, v in data_labels.items(): dis.data_labels[k] = '_' + v.replace('.', '_')
				for k, v in _data_bit_labels.items(): data_bit_labels[k] = '_' + v
			except Exception as e: log_exc(logging.warning, e)
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
		except Exception as e: log_exc(logging.warning, e)
	logging.info('Disassembling...')
	dis.disassemble()
	#dis.jmptable_add(0x19a8, 27, jmpseg = 1, bl = True)
	#dis.jmptable_add(0x1ae6, 101, jmpseg = 1, bl = True)
	#dis.jmptable_add(0x1df4, 12, True)
	#dis.jmptable_add(0x1e8a, 11, True)
	'''i = 2
	while not dis.is_queue_empty():
		print(f'Disassemble stage {i}...')
		dis.disassemble()
		i += 2'''

	with open(out, 'w') as f:
		logging.info('Writing to file...')
		f.write(f'TYPE({dcl_name})\nMODEL {"SMALL" if size <= 0x10000 else "LARGE"}\n\n')

		l = math.ceil(max(len(v) for v in dis.data_labels.values()) / 4) * 4
		equs = ''
		extrns = ''
		dis.data_labels = dict(sorted(dis.data_labels.items()))
		for k, v in dis.data_labels.items():
			if k in sfr_labels: continue
			tabs = '\t'*math.ceil((l - len(v)) / 4)
			if not tabs: tabs = '\t'
			if k >= romwin: equs += f'{v}{tabs}EQU {"" if hex(k)[2].isnumeric() else "0"}{k:04X}H\n'
			else: extrns += f'EXTRN TABLE\t: {v}\n'

		f.write(equs)

		for addr, ins in dis.code.items():
			if addr in dis.labels:
				if dis.labels[addr][0] == disas.labeltype.FUN: f.write(f'\n; {addr:05X}\n')
				f.write(f'{dis.labels[addr][1]}:\n')
			instrl = ins[0]
			instr = ins[1]
			tab = '\t'
			#string = f'{addr >> 16:X}:{addr & 0xfffe:04X}H\t\t{"".join([format(a, "04X") for a in instrl])}{tab*(3-len(instrl))}\t{instr[0]}'
			if addresses:
				string = f'/*\t{addr:05X}\t{"".join([format(a, "04X") for a in instrl])}{tab*(3-len(instrl))} */ {instr[0]}'
			else: string = f'\t{instr[0]}'
			is_lea = instr[0] == 'LEA'
			if len(instr) >= 2: string += ' ' + process_ins_param(dis, instr[1], is_lea, data_bit_labels)
			if len(instr) == 3: string += ', ' + process_ins_param(dis, instr[2], is_lea, data_bit_labels)
			f.write(string + '\n')

		f.write('\n')
		for k, v in dict(sorted(dis.labels.items())).items():
			if v[0] == disas.labeltype.FUN: f.write(f'PUBLIC {v[1]}\n')

		f.write(f'\n{extrns}\nEND\n')
		f.close()
	logging.info('Done.')

if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser(description = 'PyU8disasX command line auto-disassembler.\nDisassembly is compatible with RASU8.', epilog = f'© 2024-2026 GamingWithEvets Inc. Licensed under GPL-v3', formatter_class = argparse.RawDescriptionHelpFormatter)
	parser.add_argument('file', help = 'filename of ROM to disassemble')

	gr_disas = parser.add_argument_group('disassembler and labels')
	gr_disas.add_argument('-r', '--romwin', type = lambda x: int(x, 0), help = 'ROM window size. if unspecified and no DCL file is loaded, or ROM window is 0, no ROM window will be present. if specified, overrides DCL specification')
	gr_disas.add_argument('-l', '--label', action = 'append', help = 'add a label file')
	gr_disas.add_argument('-d', '--dcl', help = 'load a DCL file. if unspecified, default DCL name will be "foo"')

	gr_output = parser.add_argument_group('output options')
	gr_output.add_argument('-o', '--output', help = 'filename of output assembly file (default: ROM filename with ASM extension)')
	gr_output.add_argument('-a', '--addresses', action = 'store_true', help = 'add addresses and raw bytes/words to disassembly')
	
	gr_misc = parser.add_argument_group('miscellaneous')
	gr_misc.add_argument('--debug', action = 'store_true', help = 'enable debug logs')

	args = parser.parse_args()

	if args.debug: logging.basicConfig(format = f'{DARK_GRAY}[%(asctime)s] [%(filename)s:%(funcName)s:%(lineno)d] %(levelname)s: {END}%(message)s', datefmt = '%d/%m/%Y %H:%M:%S', level = logging.DEBUG, force = True)

	if args.output is None: output = os.path.splitext(args.file)[0] + '.asm'

	os.chdir(os.path.dirname(os.path.abspath(__file__)))
	disassemble(args.file, args.output, args.label, args.dcl, args.romwin, args.addresses)
