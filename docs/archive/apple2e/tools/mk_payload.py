"""Generate the BLOAD test payload: byte[i] = (i*7+7) & 0xFF for 2048 bytes."""
import io
import sys

n = 2048
data = bytes((i * 7 + 7) & 0xFF for i in range(n))
out = sys.argv[1] if len(sys.argv) > 1 else 'build/a2/lv00.bin'
io.open(out, 'wb').write(data)
print(f'{out}  {len(data)} bytes  first={data[0]}  sum16={sum(data) & 0xFFFF} (0x{sum(data) & 0xFFFF:04X})')
