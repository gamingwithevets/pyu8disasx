# Coming soon!
**PyU8disasX** is an upcoming nX-U8/100 / nX-U16/100 disassembler, and will be an upgraded rewritten version of [PyU8disas](https://github.com/gamingwithevets/pyu8disas).
Currently, the actual GUI application is not being worked on, however you can use the WIP module `disas.py`! See below for documentation.

# Usage
## GUI interface
Nope! Not yet.

## Module (`disas.py`)
### Getting started
First, you will need to place the repostory directory in the same one as your Python script, then add this to your script:
```python
from pyu8disasx import disas
```
Now you can start using the module.

### Available types
```python
class disas.numdisp
```
+ An enum class with 4 possible values:
	- 0: `disas.numdisp.HEX`
	- 1: `disas.numdisp.DEC`
	- 2: `disas.numdisp.OCT`
	- 3: `disas.numdisp.BIN`

```python
class disas.Register
```
+ Represents one of the 16 byte-sized general registers (R0 - R15) of the U8/U16 core. Can also represent one of the 8 combined word-sized general registers (ER0 - ER14), one of the 4 combined double word-sized general registers (XR0 - XR12), or one of the 2 combined quad word-sized general registers (QR0 or QR8). Attributes: `size` and `n`.

```python
class disas.RegisterBit
```
+ Represents a bit offset in one of the 16 byte-sized general registers. Attributes: `register` and `bit`.

```python
class disas.Num
```
+ Represents a signed or unsigned number of any bit length with a customizable string output. Attributes: `bits`, `value`, `disp`, `sign`.

```python
class disas.Num8
```
+ An alias of `disas.Num(8, value)`.

```python
class disas.Num7
```
+ An alias of `disas.Num(7, value)`.

### `Register` objects
A `Register` object represents a U8/U16 general register of byte size, word size, double word size or quad word size.

```python
class disas.Register(size, n)
```
+ All arguments are required.

+ `size` must be one of 1 (Rn), 2 (ERn), 4 (XRn), and 8 (QRn).

+ `n` must be an integer in `range(0, 16, size)`.

Instance attributes (read-only):
```python
Register.size
```
+ One of 1, 2, 4, 8.
```python
Register.n
```
+ In `range(0, 16, size)`.

### Register bit objects
A `RegisterBit` object represents a bit offset of a byte-sized general register.

```python
class disas.RegisterBit(register, bit)
```
+ All arguments are required.

+ `register` must be a `Register` object with `size=1`.

+ `bit` must be an integer between 0 and 7.

Instance attributes (read-only):
```python
RegisterBit.register
```
+ A `Register` object of size 1.
```python
RegisterBit.bit
```
+ In `range(8)`.

### Number objects
A `Num` object represents a signed or unsigned number of any bit length, with a customizable string output.

```python
class disas.Num(bits, value)
```
+ All arguments are required.

+ `bits` must be an integer higher than 0.

+ `value` must be an integer. It will be ANDed with 255.

Instance attributes:
```python
Num.bits
```
+ Can be any integer larger than 0.

```python
Num.value
```
+ Between 0 and the `bits`-bit integer limit.

```python
Num.disp
```
+ A `disas.numdisp` enum controlling the base of the string output. By default it is `disas.numdisp.HEX`.

```python
Num.sign
```
+ A boolean for controlling if the string output should be signed (`True`) or unsigned (`False`). By default it is `True`.

#### Subclasses
These classes inherit the `Num` object.

```python
class disas.Num8(value)
```
+ Shorthand for `disas.Num(8, value)`.

```python
class disas.Num7(value)
```
+ Shorthand for `disas.Num(7, value)`.
