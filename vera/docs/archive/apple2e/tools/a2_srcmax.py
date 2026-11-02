import subprocess, re
p = subprocess.run(['tools/a2_emu.py', '--max-steps', '400000', '--report-every', '0',
                    '--fast-tick', '--watch-addr', '0x80'], capture_output=True, text=True)
vals = []
for m in re.finditer(r'\$0080 <= \$([0-9A-Fa-f]{2})', p.stdout):
    vals.append(int(m.group(1), 16))
print('writes:', len(vals))
if vals:
    print('max src_ptr low: 0x%02X' % max(vals))
    print('tail:', ' '.join('%02X' % v for v in vals[-8:]))
else:
    print('none')
