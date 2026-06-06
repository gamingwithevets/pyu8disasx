**PyU8disasX** is an nX-U8/100 / nX-U16/100 disassembler, and is an upgraded rewritten version of [PyU8disas](https://github.com/gamingwithevets/pyu8disas).

## Usage
### Command-line interface
Even though the command-line interface was added later, it is the **preferred method** of using PyU8disasX. It has many options for customizing the disassembly output.

Run `python main_cli.py -h` for command-line syntax and available options.

### GUI (experimental)
As of now, the GUI interface is in an experimental state, and is **not recommended** to be used at this time.

To use the GUI interface, the ROM has to be imported with File > Import... or Ctrl+I. The result will be a generic disassembly listing.
The speed of the viewer will depend on your computer's speed as well as the size of the disassembly.

### Module (`disas.py`)
The main disassembler module. Custom disassemblers can be made using this module to manually add jump tables or disassemble parts of code that the disassembler was not able to reach.

## License
PyU8disasX is licensed under the [GNU General Public License Version 3](LICENSE).
Additional conditions under Section 7 are present and are as follows:
- **Attribution** (7b): Use of this code, including derivatives, must display a visible notice:
    > This app uses code from PyU8disasX. © GamingWithEvets Inc.  
    > https://github.com/gamingwithevets/pyu8disasx
- **Name Restriction** (7c): The name "**PyU8disasX**" may not be used for derivative works.  
  Derivatives must adopt a distinct identity unrelated to "**PyU8disasX**".

See the [LICENSE](LICENSE) file for the full GPL-v3 terms and the [NOTICE](NOTICE) file for full conditions of GPL-v3 Section 7.
