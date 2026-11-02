import io
import subprocess

CA65 = r'C:\dev\cc65\bin\ca65.exe'
tmp = r'C:\dev\alter-ego\build\a2\tmp'

def run(name, body):
    src = tmp + '\\' + name
    io.open(src, 'w', encoding='utf-8').write(body)
    out = []
    for t in ('apple2', 'apple2enh'):
        r = subprocess.run([CA65, '-t', t, '-o', tmp + '\\q.o', src], capture_output=True)
        err = r.stderr.decode('utf-8', 'replace').strip()
        out.append('%s:%d %s' % (t, r.returncode, err.split('\n')[0][:58] if err else 'clean'))
    print('%-16s %s' % (name, '  |  '.join(out)))

# Is __APPLE2ENH__ defined by the target (tick_frame relies on it)?
run('enh.s', '.ifndef __APPLE2ENH__\n.error "plain apple2"\n.endif\n')

# Does an explicit .setcpu make BRA legal on the plain target?
run('setcpu.s', '.setcpu "65C02"\nfoo:\n\tbra @fwd\n@fwd:\n\tnop\n')
