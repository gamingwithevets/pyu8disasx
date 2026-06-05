import sys
import re
from labeltool import labeltool

class DCLReader:
	def __init__(self, file_path):
		self.file_path = file_path
		self.data_labels = {}
		self.data_bit_labels = {}
		self.romwin = 0

	def parse(self):
		current_section = None
		
		with open(self.file_path, 'r') as f:
			for line in f:
				line = line.split(';')[0].strip()
				
				if not line: continue
				
				if line.startswith('#RAM'):
					current_section = 'RAM'
					continue
				if line.startswith('#DEFDATA'):
					current_section = 'DATA'
					continue
				elif line.startswith('#DEFBIT'):
					current_section = 'BIT'
					continue
				elif line.startswith('#'):
					current_section = None
					continue

				parts = re.split(r'\t+(?:,\t+)?', line)
				if len(parts) < 2: continue

				if current_section == 'RAM':
					if parts[0] == 'ROMWINDOW':
						end_adr = parts[2]
						if end_adr.endswith('H'):
							try:
								clean_addr = int(end_adr.rstrip('H'), 16)
								self.romwin = clean_addr + 1
							except ValueError: continue
				elif current_section == 'DATA':
					name = parts[0]
					addr_str = parts[1]
					if addr_str.endswith('H'):
						try:
							clean_addr = int(addr_str.rstrip('H'), 16)
							self.data_labels[clean_addr] = name
						except ValueError: continue

				elif current_section == 'BIT':
					bit_sym = parts[0]
					mapping = parts[1]
					if '.' in mapping: self.data_bit_labels[mapping] = bit_sym

	def save(self, out_path):
		with open(out_path, 'w') as f: labeltool.save_labels(f, 0, {}, self.data_labels, self.data_bit_labels)
		print(f'Done. {len(self.data_labels)} SFRs, {len(self.data_bit_labels)} bits')

if __name__ == '__main__':
	if len(sys.argv) < 3:
		print('Incorrect number of arguments')
		sys.exit()
	reader = DCLReader(sys.argv[1])
	reader.parse()
	reader.save(sys.argv[2])
