import sys

if __name__ == '__main__':
	print('Please run main.py to start the program!')
	sys.exit()

import os
import re
import platform
import traceback
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font
import tkinter.filedialog
import tkinter.messagebox

# for PyInstaller binaries
try:
	temp_path = sys._MEIPASS
except AttributeError:
	temp_path = os.getcwd()

import json
import math
import disas
import urllib.request
import threading
import webbrowser
import configparser
import pkg_resources

pg_name = 'PyU8disasX'  # program name here

username = 'gamingwithevets'  # GitHub username here
repo_name = 'pyu8disasx'  # GitHub repository name here

version = '0.0.1'  # displayed version (e.g. 1.0.0 Prerelease - must match GH release title)
internal_version = 'v0.0.1'  # internal version (must match GitHub release tag)
prerelease = True  # prerelease flag (must match GitHub release's prerelease flag)


def report_error(self=None, exc=None, val=None, tb=None, term=True):
	"""
	Logs in the console and displays a dialog box showing the error.
	Replaces the report_callback_exception() function in
	the tkinter.Tk class.
	NOTE: DO NOT REMOVE THE UNUSED ARGUMENTS! Due to the function replacement
	these arguments must be added.
	"""

	e = traceback.format_exc()
	err_text = f'''\
Whoops! An error has occurred.
{e}
If this error persists, please report it here:
https://github.com/{username}/{repo_name}/issues\
'''

	print(err_text)
	tk.messagebox.showerror('Whoops!', err_text)
	if term:
		sys.exit()

def process_ins_param(dis, param):
	if type(param) == list: return ', '.join(param)
	elif type(param) == disas.Address:
		if param.seg is None:
			if param.addr in dis.data_labels: return dis.data_labels[param.addr]
		else:
			addr = (param.seg.value << 16) | param.addr.value
			if addr in dis.labels: return dis.labels[addr][1]
	elif type(param) == disas.DSRPrefix:
		if type(param.dsr) == disas.Num and type(param.item) == disas.Address:
			addr = (param.dsr.value << 16) | param.item.addr
			if addr in dis.data_labels: return dis.data_labels[addr]

	return str(param)


tk.Tk.report_callback_exception = report_error

class GUI:
	def __init__(self, window, args):
		self.version = version

		self.window = window
		self.args = args

		self.temp_path = temp_path

		# change width and height of window here
		self.display_w = 800
		self.display_h = 600

		# TODO: add more "open" bools for other Toplevel classes
		self.updater_win_open = False

		tk_font = tk.font.nametofont('TkDefaultFont').actual()
		self.font_name = tk_font['family']
		self.font_size = tk_font['size']

		# TODO: add more font styles (italic, condensed, etc.)
		self.bold_font = (self.font_name, self.font_size, 'bold')

		self.init_window()
		self.init_protocols()

		self.bc_cond = False
		self.bc_cond_tk = tk.BooleanVar(); self.bc_cond_tk.set(self.bc_cond)

		# updater settings
		self.auto_check_updates = tk.BooleanVar()
		self.auto_check_updates.set(True)
		self.check_prerelease_version = tk.BooleanVar()
		self.check_prerelease_version.set(False)

		self.debug = False
		self.bc_cond_debug = tk.BooleanVar(); self.bc_cond_debug.set(False)

		# gets appdata folder
		if os.name == 'nt':
			self.appdata_folder = f'{os.getenv("LOCALAPPDATA")}\\{pg_name}'
		else:
			if platform.system() == 'Darwin':
				self.appdata_folder = os.path.expanduser(f'~/Library/Application Support/{pg_name}')
			else:
				self.appdata_folder = os.path.expanduser(f'~/.config/{pg_name}')

		self.save_to_cwd = False
		self.ini = configparser.ConfigParser()
		self.parse_settings()

		self.refreshing = True
		self.scrolling = False

		self.dis = disas.Disassembly()
		self.UpdaterGUI = UpdaterGUI(self)

		self.unsupported_tcl = False
		if sys.version_info < (3, 7, 6):
			if tk.messagebox.askyesno('Warning', f'''
It looks like you are running Python {platform.python_version()}, which has a version of Tcl/Tk that doesn\'t support \
some Unicode characters.

Do you want to continue?\
''', icon='warning'):
				self.unsupported_tcl = True
			else:
				self.quit()

		self.menubar()

		self.make_canvas()

	def make_canvas(self):
		self.canvas = tk.Canvas()
		self.canvas_scrollbar = ttk.Scrollbar(orient = 'vertical', command = self.canvas.yview)
		self.canvas.configure(yscrollcommand = self.canvas_scrollbar.set)
		self.canvas.bind('<MouseWheel>', self.scrollwheel)

	def scrollwheel(self, e):
		if self.scrolling: self.canvas.yview_scroll(int(-1*(e.delta/120)), 'units')

	def start_main(self):
		"""
		Runs necessary commands before calling the main function.
		"""

		# TODO: add more commands here

		self.updates_checked = False

		if self.auto_check_updates.get():
			threading.Thread(target=self.auto_update).start()
		else:
			self.updates_checked = True
		self.main()

	def auto_update(self):
		self.update_thread = ThreadWithResult(target=self.UpdaterGUI.updater.check_updates, args=(True,))
		self.update_thread.start()
		i = 0
		j = 0
		mult = 5000
		while self.update_thread.is_alive():
			if i == mult * 4:
				i += 1
				j = 1
			else:
				i = i - 1 if j else i + 1
			if i == 0:
				j = 0
			print(' ' * (int(i / mult)) + '.' + ' ' * (5 - int(i / mult)), end='\r')
		print('\r     ', end='\r')
		update_info = self.update_thread.result
		if update_info['newupdate']:
			self.UpdaterGUI.init_window(True, (update_info['title'], update_info['tag'], update_info['prerelease'],
										update_info['body']))
		self.updates_checked = True

	def parse_settings(self):
		"""
		Loads the program settings.
		"""

		# load override settings
		if os.path.exists(os.path.join(os.getcwd(), 'settings.ini')):
			self.ini.read('settings.ini')
			self.save_to_cwd = True
		else:
			# load normal settings
			self.ini.read(f'{self.appdata_folder}\\settings.ini')

		sects = self.ini.sections()
		if sects:
			if 'settings' in sects:
				self.config_getbool('settings', 'bc_cond', True, 'bc_cond_tk')

			if 'updater' in sects:
				self.config_getbool('updater', 'auto_check_updates')
				self.config_getbool('updater', 'check_prerelease_version')

			if 'dont_touch_this_area_unless_you_know_what_youre_doing' in sects:
				self.config_getbool('dont_touch_this_area_unless_you_know_what_youre_doing', 'debug', False)
				self.config_getbool('dont_touch_this_area_unless_you_know_what_youre_doing', 'bc_cond_debug')

		self.save_settings()

	def config_getbool(self, sect, name, tkvar = True, tkvarname = None):
		try:
			if tkvar:
				getattr(self, name if tkvarname is None else tkvarname).set(self.ini.getboolean(sect, name))
				if tkvarname is not None: setattr(self, name, getattr(self, tkvarname).get())
			else: setattr(self, name, self.ini.getboolean(sect, name))
		except (configparser.NoSectionError, configparser.NoOptionError): pass

	def config_setbool(self, sect, name, tkvar = True, tkvarname = None):
		if tkvar: self.ini[sect][name] = str(getattr(self, name if tkvarname is None else tkvarname).get())
		else: self.ini[sect][name] = str(getattr(self, name))

	def save_settings(self):
		"""
		Saves the program settings.
		"""

		# settings are set individually and initialized when needed to retain compatibility between versions
		if 'settings' not in self.ini.keys(): self.ini['settings'] = {}
		self.config_setbool('settings', 'bc_cond', True, 'bc_cond_tk')

		if 'updater' not in self.ini.keys(): self.ini['updater'] = {}
		self.config_setbool('updater', 'auto_check_updates')
		self.config_setbool('updater', 'check_prerelease_version')

		if 'dont_touch_this_area_unless_you_know_what_youre_doing' not in self.ini.keys(): self.ini['dont_touch_this_area_unless_you_know_what_youre_doing'] = {}
		self.config_setbool('dont_touch_this_area_unless_you_know_what_youre_doing', 'debug', False)
		self.config_setbool('dont_touch_this_area_unless_you_know_what_youre_doing', 'bc_cond_debug')

		if self.save_to_cwd:
			with open(os.path.join(os.getcwd(), 'settings.ini'), 'w') as f:
				self.ini.write(f)

		if not os.path.exists(self.appdata_folder):
			os.makedirs(self.appdata_folder)
		with open(f'{self.appdata_folder}{os.path.sep}settings.ini', 'w') as f:
			self.ini.write(f)

	@staticmethod
	def n_a():
		"""
		Used to prevent access to unimplemented or unfinished features.
		"""

		tk.messagebox.showinfo('Not implemented',
							   f'This feature is not implemented into this version of {pg_name}. Sorry!')

	@staticmethod
	def notify_restart():
		tk.messagebox.showinfo(pg_name, f'Please restart {pg_name} for the changes to take effect.')

	def refresh(self, load_func=False):
		"""
		Deletes all widgets and call the main function (if load_func is True).
		"""

		self.refreshing = True

		for w in self.window.winfo_children():
			w.destroy()
		self.menubar()

		self.window.protocol('WM_DELETE_WINDOW', self.quit)

		if load_func:
			self.main()

	def set_title(self, custom_str=None):
		"""
		Sets the Tkinter window title.
		"""

		self.window.title(f'{pg_name} {version}{" - " + custom_str if custom_str is not None else ""}')

	def init_window(self):
		"""
		Initializes the Tkinter window.
		"""

		self.window.geometry(f'{self.display_w}x{self.display_h}')
		self.window.bind('<F5>', lambda: self.refresh(True))
		self.window.bind('<F12>', self.version_details)
		self.window.bind('<Control-i>', lambda e: self.load_file())
		self.window.bind('<Control-I>', lambda e: self.load_file())
		self.window.option_add('*tearOff', False)
		self.set_title()
		# TODO: uncomment this when you actually have an icon.ico/xbm file

	#         try:
	#             self.window.iconbitmap(f'{self.temp_path}\\icon.{"ico" if os.name == "nt" else "xbm"}')
	#         except tk.TclError:
	#             err_text = f'''\
	# Whoops! The icon file "icon.ico" is required.
	# Can you make sure the file is in "{self.temp_path}"?
	# {traceback.format_exc()}
	# If this problem persists, please report it here:
	# https://github.com/{username}/{repo_name}/issues\
	# '''
	#             print(err_text)
	#             tk.messagebox.showerror('Hmmm?', err_text)
	#             sys.exit()

	def init_protocols(self):
		"""
		Initializes protocols.
		"""

		self.window.protocol('WM_DELETE_WINDOW', self.quit)

	def quit(self):
		"""
		Quits the program.
		"""

		if not any([
			self.updater_win_open,
			# TODO: add other "open" bools here
		]):
			self.save_settings()
			sys.exit()

	@staticmethod
	def about_menu():
		"""
		Shows basic information about the version, system and architecture, as well as the license of the project.
		NOTE: LICENSE CANNOT BE CHANGED, AS PER THE CONDITIONS OF THE GNU GPL-V3 LICENSE.
		"""

		nl = '\n'
		syst = platform.system()
		syst += ' x64' if platform.machine().endswith('64') else ' x86'
		tk.messagebox.showinfo(f'About {pg_name}', f'''\
{pg_name} - {version} ({'64' if sys.maxsize > 2 ** 31 - 1 else '32'}-bit) - Running on {syst}
Project page: https://github.com/{username}/{repo_name}
{nl + 'WARNING: This is a pre-release version, therefore it may have bugs and/or glitches.' + nl if prerelease else ''}
Licensed under the GNU GPL-v3 license
(LICENSE file available on the GitHub repository or included with source code)\
''')

	def version_details(self, event=None):
		"""
		Shows technical information about the Python installation and operating system.
		By default, it can be triggered via the F12 key.
		Note: DO NOT REMOVE THE event ARGUMENT!
		"""

		if self.debug:
			dnl = '\n\n'
			tk.messagebox.showinfo(f'{pg_name} version details', f'''\
{pg_name} {version}{" (prerelease)" if prerelease else ""}
Internal version: {internal_version}

Python version information:
Python {platform.python_version()} ({'64' if sys.maxsize > 2 ** 31 - 1 else '32'}-bit)
Tkinter (Tcl/Tk) version {self.window.tk.call('info', 'patchlevel')}\
{" (most Unicode chars not supported)" if self.unsupported_tcl else ""}

Operating system information:
{platform.system()} {platform.release()}
{'NT version: ' if os.name == 'nt' else ''}{platform.version()}
Architecture: {platform.machine()}{dnl + "Settings file is saved to working directory" if self.save_to_cwd else ""}\
''')

	def disable_debug(self):
		if tk.messagebox.askyesno('Warning',
								  'To re-enable debug mode you must set the debug flag to True in settings.ini.\nContinue?',
								  icon='warning'):
			self.debug = False
			self.save_settings()
			self.menubar()  # update the menubar

	def menubar(self):
		"""
		Sets up the menubar.
		"""

		menubar = tk.Menu()

		file_menu = tk.Menu(menubar)
		file_menu.add_command(label = 'New project', accelerator = 'Ctrl+N', state = 'disabled')
		file_menu.add_command(label = 'Open project...', accelerator = 'Ctrl+O', state = 'disabled')
		file_menu.add_command(label = 'Save project', accelerator = 'Ctrl+S', state = 'disabled')
		file_menu.add_command(label = 'Save project as...', accelerator = 'Ctrl+Shift+S', state = 'disabled')
		file_menu.add_separator()
		file_menu.add_command(label = 'Import...', accelerator = 'Ctrl+I', command = self.load_file)
		export_menu = tk.Menu(file_menu)
		export_menu.add_command(label = 'As OMFU8 assembly...', command = self.export_omf)
		export_menu.add_command(label = 'As ELF assembly...', state = 'disabled')
		file_menu.add_cascade(label='Export', menu=export_menu, state = 'normal' if len(self.dis.filename) > 0 else 'disabled')
		file_menu.add_separator()
		file_menu.add_command(label='Exit', command=self.quit)
		menubar.add_cascade(label='File', menu=file_menu)

		settings_menu = tk.Menu(menubar)

		bc_cond_menu = tk.Menu(settings_menu)
		bc_cond_menu.add_radiobutton(label = 'Bcond Radr', variable = self.bc_cond_tk, value = False, command = self.replace_bcond if self.bc_cond_debug.get() else self.notify_restart)
		bc_cond_menu.add_radiobutton(label = 'BC cond, Radr', variable = self.bc_cond_tk, value = True, command = self.replace_bcond if self.bc_cond_debug.get() else self.notify_restart)
		settings_menu.add_cascade(label='Conditional branch syntax', menu=bc_cond_menu)

		updater_settings_menu = tk.Menu(settings_menu)
		updater_settings_menu.add_checkbutton(label='Check for updates on startup', variable=self.auto_check_updates,
											  command=self.save_settings)
		updater_settings_menu.add_checkbutton(label='Check for pre-release versions',
											  variable=self.check_prerelease_version,
											  command=self.save_settings)
		settings_menu.add_cascade(label='Updates', menu=updater_settings_menu)

		if self.debug:
			settings_menu.add_separator()
			debug_menu = tk.Menu(settings_menu)
			
			experimental_menu = tk.Menu(debug_menu)
			experimental_menu.add_command(label = 'These settings may or may not work properly.', state = 'disabled')
			experimental_menu.add_command(label = 'Use these settings with caution.', state = 'disabled')
			experimental_menu.add_separator()
			experimental_menu.add_checkbutton(label = 'Auto update Bcond <-> BC cond', variable = self.bc_cond_debug, command = self.notify_restart)
			debug_menu.add_cascade(label = 'Debug/Experimental settings', menu = experimental_menu)

			debug_menu.add_separator()
			debug_menu.add_command(label='Version details', command=self.version_details, accelerator='F12')
			debug_menu.add_command(label='Updater test', command=lambda: self.UpdaterGUI.init_window(debug=True))
			debug_menu.add_separator()
			debug_menu.add_command(label='Disable debug mode', command=self.disable_debug)
			settings_menu.add_cascade(label='Debug', menu=debug_menu)

		menubar.add_cascade(label='Settings', menu=settings_menu)

		help_menu = tk.Menu(menubar)
		help_menu.add_command(label='Check for updates', command=self.UpdaterGUI.init_window)
		help_menu.add_command(label=f'About {pg_name}', command=self.about_menu)
		help_menu.add_command(label = 'Join Casio Calculator Hacking', command = lambda: webbrowser.open_new_tab('http://discord.gg/QjGpH6rSQQ'))
		menubar.add_cascade(label='Help', menu=help_menu)

		self.window.config(menu=menubar)

	def main(self):
		"""
		Where the mainloop is called.
		"""

		self.window.update()
		self.set_title()

		if self.args.f_import is None:
			ttk.Label(text = 'Welcome to PyU8disasX!', font = self.bold_font).pack()
			ttk.Label(text = '''\
This is a very early version of PyU8disasX that includes basic functions such as importing binary files and exporting assembly files.
More features will be added in the future.

To start, load a binary file with File > Import... (Ctrl+I).''', justify = 'center').pack()
		else: self.load_file(self.args.f_import)

		self.window.mainloop()

	def load_file(self, file = ''):
		if len(file) == 0: file = tk.filedialog.askopenfilename(title = 'Import', initialdir = os.getcwd(), filetypes = (('Binary Files', '*.bin'), ('All Files', '*.*')), defaultextension = '.bin')

		if len(file) > 0:
			self.set_title(os.path.basename(file))
			self.dis.load(file)
			self.dis.disassemble()
			self.draw_disas()

	def draw_disas(self):
		mono = tk.font.Font(font = 'TkFixedFont').actual()

		self.refresh()
		self.make_canvas()
		head = ttk.Label(text = 'Please wait', font = self.bold_font); head.pack()
		body = ttk.Label(text = 'Disassembling... This may take a while.'); body.pack()
		self.window.update()

		y = 0
		for addr, ins in self.dis.code.items():
			self.window.update()
			if addr in self.dis.labels:
				l = self.dis.labels[addr]
				if l[0] == disas.labeltype.FUN: y += 20
				self.canvas.create_text(0, y, anchor = 'nw', text = f'{l[1]}:', font = 'TkFixedFont')
				y += 20

			instrl = ins[0]
			instr = ins[1]
			bc = addr in self.dis.conds
			tab = ' '*4
			opx = self.canvas.bbox(self.canvas.create_text(0, y, anchor = 'nw', text = f'{addr >> 16:X}:{addr & 0xfffe:04X}H{tab*2}{"".join([format(a, "04X") for a in instrl])}{tab*(3-len(instrl))}\t', font = 'TkFixedFont'))[2]
			opx = self.canvas.bbox(self.canvas.create_text(opx, y, anchor = 'nw', text = f'{instr[0] if bc and self.bc_cond or not bc else "B"+instr[1]} ', font = (mono['family'], mono['size'], 'bold'), fill = 'blue', tag = f'i_{addr:05X}_0'))[2]
			for i, op in enumerate(instr[1:]):
				if i == 0 and bc and not self.bc_cond:
					self.canvas.create_text(opx, y, anchor = 'nw', tag = f'i_{addr:05X}_1', font = 'TkFixedFont')
					continue
				if i > 0: opx = self.canvas.bbox(self.canvas.create_text(opx, y, anchor = 'nw', text = ',  ' if bc and self.bc_cond or not bc else '', tag = f'i_{addr:05X}_{i}{i+1}'))[2]
				if type(op) == disas.Address:
					adr = op.get_combined()
					if adr in self.dis.labels:
						s_op = self.canvas.create_text(opx, y, anchor = 'nw', text = self.dis.labels[adr][1], tag = f'i_{addr:05X}_{i+1}', font = 'TkFixedFont')
						self.canvas.tag_bind(s_op, '<Button-1>', lambda e, adr = adr: self._canvas_moveto_address(adr))
					else:
						s_op = self.canvas.create_text(opx, y, anchor = 'nw', text = op, tag = f'i_{addr:05X}_{i+1}', font = 'TkFixedFont')
						self.canvas.tag_bind(s_op, '<Button-1>', lambda e, adr = adr: self._canvas_moveto_address(adr, False))
					self.canvas.tag_bind(s_op, '<Enter>', lambda e, tag = s_op: self._canvas_enter(tag))
					self.canvas.tag_bind(s_op, '<Leave>', lambda e, tag = s_op: self._canvas_leave(tag))
					self.canvas.tag_bind(s_op, '<Button-3>', self.do_context_menu)
				elif type(op) == disas.Register:
					s_op = self.canvas.create_text(opx, y, anchor = 'nw', text = op, tag = f'i_{addr:05X}_{i+1}', font = 'TkFixedFont')
				else: 
					s_op = self.canvas.create_text(opx, y, anchor = 'nw', text = op, tag = f'i_{addr:05X}_{i+1}', font = 'TkFixedFont')
					self.canvas.tag_bind(s_op, '<Enter>', lambda e, tag = s_op: self._canvas_enter(tag))
					self.canvas.tag_bind(s_op, '<Leave>', lambda e, tag = s_op: self._canvas_leave(tag))
					self.canvas.tag_bind(s_op, '<Button-3>', self.do_context_menu)
				opx = self.canvas.bbox(s_op)[2]
			y += 20
		self.canvas.config(scrollregion = self.canvas.bbox('all'))

		body.destroy()
		head['text'] = 'Disassembly'
		self.canvas_scrollbar.pack(side = 'right', fill = 'y')
		self.canvas.pack(side = 'left', fill = 'both', expand = True)
		self.window.update()

	def replace_bcond(self):
		bccond = self.bc_cond_tk.get()
		if bccond and not self.bc_cond:
			for addr in Progressbar(self, self.dis.conds, 'Bcond Radr -> BC cond, Radr'):
				instr = self.dis.code[addr][1]
				self.canvas.itemconfigure(f'i_{addr:05X}_0', text = 'BC ')
				self.canvas.itemconfigure(f'i_{addr:05X}_1', text = instr[1])
				self._canvas_update_bbox(f'i_{addr:05X}_1', f'i_{addr:05X}_0')
				self.canvas.itemconfigure(f'i_{addr:05X}_12', text = ', ')
				self._canvas_update_bbox(f'i_{addr:05X}_12', f'i_{addr:05X}_1')
				self.canvas.itemconfigure(f'i_{addr:05X}_2', text = instr[2])
				self._canvas_update_bbox(f'i_{addr:05X}_2', f'i_{addr:05X}_12')
				pb.inc()
		elif not bccond and self.bc_cond:
			for addr in Progressbar(self, self.dis.conds, 'BC cond, Radr -> Bcond Radr'):
				instr = self.dis.code[addr][1]
				self.canvas.itemconfigure(f'i_{addr:05X}_0', text = f'B{instr[1]} ')
				self.canvas.itemconfigure(f'i_{addr:05X}_1', text = '')
				self.canvas.itemconfigure(f'i_{addr:05X}_12', text = '')
				self._canvas_update_bbox(f'i_{addr:05X}_2', f'i_{addr:05X}_0')

		self.bc_cond = bccond

	def _canvas_get_tag(self):
		item = self.canvas.find_withtag('current')
		tags = self.canvas.gettags(item)
		return tags[0]

	def _canvas_update_bbox(self, tag1, tag2):
		box = self.canvas.bbox(tag2)
		self.canvas.coords(tag1, box[2], box[1])

	def _canvas_enter(self, tag): self.canvas.itemconfigure(tag, fill = 'blue')

	def _canvas_leave(self, tag): self.canvas.itemconfigure(tag, fill = 'black')

	def _canvas_moveto_address(self, addr, has_label = True):
		bbox = self.canvas.bbox(f'i_{addr:05X}_0')
		if bbox:
			_, _, _, scroll_hi = map(int, self.canvas.cget('scrollregion').split())
			self.canvas.yview_moveto((bbox[1] - (40 if has_label else 20)) / scroll_hi)

	def export_omf(self):
		f = tk.filedialog.asksaveasfile(title = 'Export as OMFU8', initialdir = os.getcwd(), initialfile = f'{os.path.splitext(self.dis.filename)[0]}.asm', filetypes = (('Assembly Files', '*.asm'), ('All Files', '*.*')), defaultextension = '.asm')
		if f is None: return
		f.write('TYPE(foo)  ; Replace with DCL name (see Section 5.1.1 of MACU8 User\'s Manual)\nMODEL LARGE\n\n')
		l = math.ceil(max(len(v) for v in self.dis.data_labels.values()) / 4) * 4
		equs = ''
		extrns = ''
		self.dis.data_labels = dict(sorted(self.dis.data_labels.items()))
		for k, v in self.dis.data_labels.items():
			tabs = '\t'*(1+math.ceil((l - len(v)) / 4))
			if k >= 0x8000: equs += f'{v}{tabs}EQU {"" if hex(k)[2].isnumeric() else "0"}{k:04X}H\n'
			else: extrns += f'EXTRN DATA\t: {v}{tabs}; {k:05X}\n'

		f.write(f'{equs}\n{extrns}\n')

		for addr, ins in self.dis.code.items():
			if addr in self.dis.labels:
				if self.dis.labels[addr][0] == disas.labeltype.FUN: f.write(f'\n; {addr:05X}\n')
				f.write(f'{self.dis.labels[addr][1]}:\n')
			instrl = ins[0]
			instr = ins[1]
			tab = '\t'
			#string = f'{addr >> 16:X}:{addr & 0xfffe:04X}H\t\t{"".join([format(a, "04X") for a in instrl])}{tab*(3-len(instrl))}\t{instr[0]}'
			string = f'\t{instr[0]}'
			if len(instr) >= 2: string += ' ' + process_ins_param(self.dis, instr[1])
			if len(instr) == 3: string += ', ' + process_ins_param(self.dis, instr[2])
			f.write(string + '\n')

		f.write('\n')
		for k, v in dict(sorted(self.dis.labels.items())).items():
			if v[0] == disas.labeltype.FUN: f.write(f'PUBLIC {v[1]}\n')

		f.write('\nEND\n')

		f.close()
		tk.messagebox.showinfo('Export as OMFU8', 'The export was successful.')

	def do_context_menu(self, event):
		tag = self._canvas_get_tag()

		m = re.match(r'^i_([0-9A-F]{5})_(\d)$', tag)
		if m is None: return

		addr = int(m.group(1), 16)
		idx = int(m.group(2))

		param = self.dis.code[addr][1][idx]
		if type(param) == disas.Num:
			numdisp = tk.IntVar(value = param.disp)

			menu = tk.Menu()
			if disas.conv_sign(param.value, param.bits) < 0: menu.add_command(label = 'Invert sign', command = lambda: self.invert_bool(addr, idx, 'sign'))
			numdisp_menu = tk.Menu(menu)
			numdisp_menu.add_radiobutton(label = 'Hexadecimal', variable = numdisp, value = 0, command = lambda: self.set_param_attr(addr, idx, 'disp', 0))
			numdisp_menu.add_radiobutton(label = 'Decimal', variable = numdisp, value = 1, command = lambda: self.set_param_attr(addr, idx, 'disp', 1))
			numdisp_menu.add_radiobutton(label = 'Octal', variable = numdisp, value = 2, command = lambda: self.set_param_attr(addr, idx, 'disp', 2))
			numdisp_menu.add_radiobutton(label = 'Binary', variable = numdisp, value = 3, command = lambda: self.set_param_attr(addr, idx, 'disp', 3))
			numdisp_menu.add_radiobutton(label = 'Character constant', variable = numdisp, value = 4, command = lambda: self.set_param_attr(addr, idx, 'disp', 4))
			menu.add_cascade(label = 'Display as', menu = numdisp_menu)
			try: menu.tk_popup(event.x_root, event.y_root)
			finally: menu.grab_release()

	def invert_bool(self, addr, idx, name): self.set_param_attr(addr, idx, name, not getattr(self.dis.code[addr][1][idx], name))

	def set_param_attr(self, addr, idx, name, value):
		setattr(self.dis.code[addr][1][idx], name, value)
		self.canvas.itemconfigure(f'i_{addr:05X}_{idx}', text = self.dis.code[addr][1][idx])

class Progressbar(tk.Toplevel):
	def __init__(self, gui, iterable, text = None, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.resizable(False, False)
		self.protocol('WM_DELETE_WINDOW', lambda: 'break')
		self.title('Working...')
		ttk.Label(self, text = text).pack()
		self.__iterator = iter(iterable)
		self.__length = len(iterable)
		self.__bar = ttk.Progressbar(self, orient='horizontal', length = 100, maximum=self.__length, mode='determinate')
		self.__bar.pack(side = 'left')
		self.__lab = ttk.Label(self, text = '0%')
		self.__lab.pack(side = 'right')
		self.focus()
		self.grab_set()
		self.gui = gui
		gui.scrolling = False
		self.update()

	def __iter__(self): return self

	def __next__(self):
		if not self.winfo_exists(): raise StopIteration
		try:
			value = next(self.__iterator)
			self.after(0, self.update())
			return value
		except StopIteration:
			self.gui.scrolling = True
			self.grab_release()
			self.destroy()
			raise

	def update(self):
		self.__bar['value'] += 1
		self.__lab['text'] = f'{int(self.__bar["value"]/self.__length*100)}%'
		super().update()

class UpdaterGUI:
	def __init__(self, gui):
		self.gui = gui

		self.after_ms = 100

		self.updater = Updater()

	def init_window(self, auto=False, auto_download_options=None, debug=False):
		if not self.gui.updater_win_open:
			self.gui.updater_win_open = True

			self.auto = auto
			self.debug = debug

			self.win = tk.Toplevel(self.gui.window)
			self.win.geometry('400x400')
			self.win.resizable(False, False)
			self.win.protocol('WM_DELETE_WINDOW', self.quit)
			self.win.title('Updater')
			# TODO: uncomment this when you actually have an icon.ico/xbm file
#             try:
#                 self.updater_win.iconbitmap(f'{self.gui.temp_path}\\icon.{"ico" if os.name == "nt" else "xbm"}')
#             except tk.TclError:
#                 err_text = f'''\
# Whoops! The icon file "icon.ico" is required.
# Can you make sure the file is in "{self.gui.temp_path}"?
# {traceback.format_exc()}
# If this problem persists, please report it here:
# https://github.com/{username}/{repo_name}/issues\
# '''
#                 print(err_text)
#                 tk.messagebox.showerror('Hmmm?', err_text)
#                 sys.exit()

			self.win.focus()
			self.win.grab_set()
			if self.debug:
				self.debug_menu()
			elif self.auto:
				self.win.after(0, lambda: self.draw_download_msg(*auto_download_options))
			else: self.main()

	def quit(self):
		self.win.grab_release()
		self.win.destroy()
		self.gui.updater_win_open = False
		if self.auto:
			self.auto = False
			self.gui.main()

	def main(self):
		self.update_thread = ThreadWithResult(target=self.updater.check_updates,
											  args=(self.gui.check_prerelease_version.get(),))

		self.draw_check()
		self.win.after(1, self.start_thread)
		self.win.mainloop()

	def debug_menu(self):
		ttk.Button(self.win, text='Check updates', command=self.main).pack()
		ttk.Button(self.win, text='Message test',
				   command=lambda: self.draw_msg('Updater message test.\nLine 2\nLine 3\nLine 4')).pack()
		ttk.Button(self.win, text='New update screen test',
				   command=lambda: self.draw_download_msg(version, internal_version, False, '''\
Hello! **This is a *test* of the updater\'s Markdown viewer**, made possible with the [Markdown](https://pypi.org/project/Markdown/), [`mdformat`](https://pypi.org/project/mdformat/), and [TkinterWeb](https://pypi.org/project/tkinterweb/) modules.

By the way, here\'s [TkTemplate](https://github.com/gamingwithevets/tktemplate), which is what this program was based on.

Also, you should check out the [Steveyboi/GWE Discord server](https://gamingwithevets.github.io/redirector/discord).\
''')).pack()
		ttk.Button(self.win, text='Quit', command=self.quit).pack(side='bottom')

	def start_thread(self):
		self.update_thread.start()
		while self.update_thread.is_alive():
			self.win.update_idletasks()
			self.progressbar['value'] = self.updater.progress
		self.progressbar['value'] = 100
		self.update_thread.join()
		update_info = self.update_thread.result

		if update_info['error']:
			if 'exceeded' in update_info and update_info['exceeded']:
				self.draw_msg('GitHub API rate limit exceeded! Please try again later.')
			elif 'nowifi' in update_info and update_info['nowifi']:
				self.draw_msg(
					'Unable to connect to the internet. Please try again\nwhen you have a stable internet connection.')
			elif 'prerelease' in update_info and update_info['prerelease']:
				self.draw_msg('Cannot get the latest release. Try enabling "Check for\npre-release versions" in Settings.')
			else:
				self.draw_msg('Unable to check for updates! Please try again later.')
		elif update_info['newupdate']:
			self.draw_download_msg(update_info['title'], update_info['tag'], update_info['prerelease'])
		else:
			self.draw_msg('You are already using the latest version.')

	def draw_check(self):
		for w in self.win.winfo_children():
			w.destroy()

		ttk.Label(self.win, text='Checking for updates...').pack()
		self.progressbar = ttk.Progressbar(self.win, orient='horizontal', length=100, mode='determinate')
		self.progressbar.pack()
		ttk.Label(self.win, text='DO NOT close the program\nwhile checking for updates',
				  justify='center', font=self.gui.bold_font).pack(side='bottom')

	def draw_msg(self, msg):
		if self.auto:
			self.gui.set_title()
			self.quit()
		else:
			for w in self.win.winfo_children():
				w.destroy()
			ttk.Label(self.win, text=msg, justify='center').pack()
			ttk.Button(self.win, text='Back', command=self.quit).pack(side='bottom')

	@staticmethod
	def package_installed(package):
		try:
			pkg_resources.get_distribution(package)
		except pkg_resources.DistributionNotFound:
			return False

		return True

	def draw_download_msg(self, title, tag, prever, body):
		if self.auto:
			self.win.deiconify()
			self.gui.set_title()
		for w in self.win.winfo_children():
			w.destroy()
		ttk.Label(self.win, justify='center', text=f'''\
An update is available!
Current version: {self.gui.version}{" (pre-release)" if prerelease else ""}
New version: {title}{" (pre-release)" if prever else ""}\
''').pack()
		ttk.Button(self.win, text='Cancel', command=self.quit).pack(side='bottom')
		ttk.Button(self.win, text='Visit download page',
				   command=lambda: self.open_download(tag)).pack(side='bottom')

		ttk.Label(self.win).pack()

		packages_missing = []
		for package in ('markdown', 'mdformat-gfm', 'tkinterweb'):
			if not self.package_installed(package):
				packages_missing.append(package)

		if packages_missing:
			ttk.Label(self.win,
				text=f'Missing package(s): {", ".join(packages_missing[:2])}{" and " + str(len(packages_missing) - 2) + " others" if len(packages_missing) > 2 else ""}',
				font=self.gui.bold_font).pack()
		else:
			import markdown
			import mdformat
			import tkinterweb

			html = tkinterweb.HtmlFrame(self.win, messages_enabled=False)
			html.load_html(
				markdown.markdown(mdformat.text(body)).replace('../..', f'https://github.com/{username}/{repo_name}'))
			html.on_link_click(webbrowser.open_new_tab)
			html.pack()

		if self.auto:
			self.win.deiconify()

	def open_download(self, tag):
		webbrowser.open_new_tab(f'https://github.com/{username}/{repo_name}/releases/tag/{tag}')
		self.quit()


class Updater:
	def __init__(self):
		self.username, self.reponame = username, repo_name
		self.request_limit = 5

		self.progress = 0
		self.progress_inc = 25

	def check_internet(self):
		try:
			self.request('https://google.com', True)
			return True
		except Exception:
			return False

	def request(self, url, testing=False):
		success = False
		for i in range(self.request_limit):
			try:
				r = urllib.request.urlopen(url)
				success = True
				break
			except urllib.error.HTTPError as e:
				r = e.fp
				success = True
			except urllib.error.URLError as e:
				if not testing:
					if not self.check_internet():
						return
		if success:
			if not testing:
				d = r.read().decode()
				return json.loads(d)

	def check_updates(self, pr):
		self.progress = 0

		if not self.check_internet():
			return {
				'newupdate': False,
				'error': True,
				'exceeded': False,
				'nowifi': True
			}
		try:
			versions = []
			if not self.check_internet():
				return {'newupdate': False, 'error': True, 'exceeded': False, 'nowifi': True}

			response = self.request(f'https://api.github.com/repos/{self.username}/{self.reponame}/releases')
			if response is None:
				return {'newupdate': False, 'error': True, 'exceeded': False, 'nowifi': True}

			for info in response:
				versions.append(info['tag_name'])

			# UPDATE POINT 1
			self.progress += self.progress_inc

			if internal_version not in versions:
				try:
					testvar = response['message']
					if 'API rate limit exceeded for' in testvar:
						return {
							'newupdate': False,
							'error': True,
							'exceeded': True
						}
					else:
						return {'newupdate': False, 'error': False}
				except Exception:
					return {'newupdate': False, 'error': False}
			if not self.check_internet():
				return {'newupdate': False, 'error': True, 'exceeded': False, 'nowifi': True}

			# UPDATE POINT 2
			self.progress += self.progress_inc

			response = self.request(
				f'https://api.github.com/repos/{self.username}/{self.reponame}/releases/tags/{internal_version}')
			if response is None:
				return {'newupdate': False, 'error': True, 'exceeded': False, 'nowifi': True}
			try:
				testvar = response['message']
				if 'API rate limit exceeded for' in testvar:
					return {
						'newupdate': False,
						'error': True,
						'exceeded': True
					}
				else:
					return {'newupdate': False, 'error': False}
			except Exception:
				pass

			currvertime = response['published_at']

			# UPDATE POINT 3
			self.progress += self.progress_inc

			if not pr:
				if not self.check_internet():
					return {'newupdate': False, 'error': True, 'exceeded': False, 'nowifi': True}

				response = self.request(f'https://api.github.com/repos/{self.username}/{self.reponame}/releases/latest')
				if response is None:
					return {'newupdate': False, 'error': True, 'exceeded': False, 'nowifi': True}
				try:
					testvar = response['message']
					if 'API rate limit exceeded for' in testvar:
						return {
							'newupdate': False,
							'error': True,
							'exceeded': True
						}
					else:
						return {'newupdate': False, 'error': True, 'prerelease': True}
				except Exception:
					pass
				if response['tag_name'] != internal_version and response['published_at'] > currvertime:
					return {
						'newupdate': True,
						'prerelease': False,
						'error': False,
						'title': response['name'],
						'tag': response['tag_name'],
						'body': response['body']
					}
				else:
					return {
						'newupdate': False,
						'unofficial': False,
						'error': False
					}
			else:
				for ver in versions:
					if not self.check_internet():
						return {'newupdate': False, 'error': True, 'exceeded': False, 'nowifi': True}

					response = self.request(
						f'https://api.github.com/repos/{self.username}/{self.reponame}/releases/tags/{ver}')
					if response is None:
						return {'newupdate': False, 'error': True, 'exceeded': False, 'nowifi': True}
					try:
						testvar = response['message']
						if 'API rate limit exceeded for' in testvar:
							return {
								'newupdate': False,
								'error': True,
								'exceeded': True
							}
						else:
							return {'newupdate': False, 'error': True, 'exceeded': False, 'nowifi': False}
					except Exception:
						pass
					if currvertime < response['published_at']:
						return {
							'newupdate': True,
							'prerelease': response['prerelease'],
							'error': False,
							'title': response['name'],
							'tag': response['tag_name'],
							'body': response['body']
						}
					else:
						return {
							'newupdate': False,
							'unofficial': False,
							'error': False
						}
		except Exception:
			return {
				'newupdate': False,
				'error': True,
				'exceeded': False,
				'nowifi': False
			}

# https://stackoverflow.com/a/65447493
class ThreadWithResult(threading.Thread):
	def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None):
		if kwargs is None:
			kwargs = {}

		def function(): self.result = target(*args, **kwargs)

		super().__init__(group=group, target=function, name=name, daemon=daemon)
