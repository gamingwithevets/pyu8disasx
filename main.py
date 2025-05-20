import os
import sys
import argparse
import platform
import traceback
import tkinter.messagebox

if __name__ != '__main__': raise ImportError('Not a module')

python_requirement = (3, 6, 0)
if sys.version_info < python_requirement:
	print('Oops! Your Python version is too old.\n')
	print(f'Requirement: Python {".".join(map(str, python_requirement))}\nYou have   : Python {platform.python_version()}')
	print('\nGet a newer version!')
	sys.exit()

try:
	import tkinter as tk
except ImportError:
	print('''Oooh no you don't have Tkinter.
Don't worry! It's super easy. Just search "install tkinter" on Google and you\'ll find it!

Now scram!''')
	sys.exit()

username = 'gamingwithevets'  # GitHub username here
reponame = 'pyu8disasx'  # GitHub repository name here

try:
	import gui
except ImportError:
	err_text = f'''\
Whoops! The script "gui.py" is required.\nCan you make sure the script is in "{gui.temp_path}"?

{traceback.format_exc()}
If this problem persists, please report it here:\nhttps://github.com/{username}/{reponame}/issues\
'''
	print(err_text)
	tk.messagebox.showerror('Hmmm?', err_text)
	sys.exit()

try:
	parser = argparse.ArgumentParser(description = 'Tool to assist in disassembling nX-U8/100 and nX-U16/100 binary applications.', epilog = f'© GamingWithEvets Inc. More info in Help > About {gui.pg_name}')
	parser.add_argument('-i', '--import', metavar = 'filename', dest = 'f_import', help = 'import a binary file (File > Import...)')
	parser.add_argument('-v', '--version', action = 'store_true', help = 'show the program version and exit')
	args = parser.parse_args()
	if args.version:
		print(gui.pg_name, gui.internal_version)
		sys.exit()
	g = gui.GUI(tk.Tk(), args)
	g.start_main()
except SystemExit:
	os._exit(0)
except Exception:
	gui.report_error()
