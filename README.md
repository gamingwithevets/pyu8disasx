# Coming soon!
**PyU8disasX** is an upcoming nX-U8/100 / nX-U16/100 disassembler, and will be an upgraded rewritten version of [PyU8disas](https://github.com/gamingwithevets/pyu8disas).
Currently, the actual GUI application is not being worked on, however you can use the WIP module `disas.py`! See below for documentation.

## Usage
### GUI interface
Nope! Not yet.

### Module (`disas.py`)
The documentation below is currently very basic.

First, you will need to place the repostory directory in the same one as your Python script, then add this to your script:
```
from pyu8disasx import disas
```
Now you can start using the module.

### `class disas.Register(size, n)`
`size` must be one of 1 (Rn), 2 (ERn), 4 (XRn), and 8 (QRn).

`n` must be an integer in `range(0, 16, size)`.

#### `Register.__str__()`
Returns a string representing the register object.

### `class disas.RegisterBit(register, bit)`
`register` must be a `Register` object with `size=1`.

`bit` must be an integer between 0 and 7.

#### `RegisterBit.__str__()`
Returns a string representing the register bit offset object.

### `class disas.Num8(value)`
`value` must be an integer. It will be ANDed with 255.

#### `Num8.__str__()`
Returns a string representing the 8-bit number object. The format of the string depends on `Num8.disp` and `Num8.sign`.
