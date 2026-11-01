import io
import subprocess

CA65 = r'C:\dev\cc65\bin\ca65.exe'
tmp = r'C:\dev\alter-ego\build\a2\tmp'

cases = {
    'at_col0':   "@lab:\n\tnop\n\tjmp @lab\n",
    'at_indent': "\tlda #$01\n@lab2:\n\tnop\n\tjmp @lab2\n",
    'at_indent_space': " @lab3:\n\tnop\n\tjmp @lab3\n",
    'dot_indent': "foo:\n.lab:\n\tnop\n\tjmp .lab\n",
}

for name, body in cases.items():
    src = tmp + '\\' + name + '.s'
    io.open(src, 'w', encoding='utf-8').write(body)
    row = []
    for target in ('apple2', 'apple2enh'):
        r = subprocess.run([CA65, '-t', target, '-o', tmp + '\\p.o', src],
                           capture_output=True)
        err = r.stderr.decode('utf-8', 'replace')
        first = next((l for l in err.split('\n') if 'Error' in l), '')
        row.append('%s:%d %s' % (target, r.returncode, first.strip()[:70]))
    print('%-18s %s' % (name, '  |  '.join(row)))
