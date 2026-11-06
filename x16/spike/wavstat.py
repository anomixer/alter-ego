import sys
import wave
import array
import math
import struct


def patched_wav_bytes(path):
    """x16emu only fixes up the RIFF/data sizes when it exits normally; a test
    run is killed, so repair the two size fields in memory before parsing."""
    data = bytearray(open(path, 'rb').read())
    if len(data) < 44 or data[0:4] != b'RIFF' or data[8:12] != b'WAVE':
        return bytes(data)
    pos = 12
    while pos + 8 <= len(data):
        cid = bytes(data[pos:pos + 4])
        size = struct.unpack('<I', bytes(data[pos + 4:pos + 8]))[0]
        if cid == b'data':
            struct.pack_into('<I', data, pos + 4, len(data) - (pos + 8))
            break
        pos += 8 + size + (size & 1)
    struct.pack_into('<I', data, 4, len(data) - 8)
    return bytes(data)


path = sys.argv[1]
raw_bytes = patched_wav_bytes(path)
w = wave.open(__import__('io').BytesIO(raw_bytes), 'rb')
ch = w.getnchannels()
sw = w.getsampwidth()
rate = w.getframerate()
n = w.getnframes()
print(f'channels={ch} width={sw} rate={rate} frames={n} seconds={n/rate:.2f}')
raw = w.readframes(n)
w.close()

if sw != 2:
    print('unexpected sample width')
    sys.exit()

a = array.array('h')
a.frombytes(raw[: len(raw) // 2 * 2])
if ch == 2:
    mono = array.array('h', [(a[i] + a[i + 1]) // 2 for i in range(0, len(a) - 1, 2)])
else:
    mono = a

step = int(rate * (float(sys.argv[2]) if len(sys.argv) > 2 else 1.0))  # window seconds
out = []
for start in range(0, len(mono) - step, step):
    seg = mono[start:start + step]
    rms = math.sqrt(sum(s * s for s in seg) / len(seg)) / 32768.0
    peak = max(abs(s) for s in seg) / 32768.0
    out.append((start // rate, rms, peak))
for sec, rms, peak in out:
    bar = '#' * min(60, int(rms * 600))
    print(f'{sec:3d}s rms={rms:.4f} peak={peak:.3f} {bar}')
