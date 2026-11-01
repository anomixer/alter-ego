import re

p = r'C:\dev\alter-ego\src\a2\ftm.s'
lines = open(p, encoding='utf-8').read().split('\n')

start = end = None
for i, l in enumerate(lines):
    if l.strip().startswith('note_to_period:'):
        start = i
    if start is not None and 'noteTable copied from' in l:
        end = i
        break
if start is None or end is None:
    raise SystemExit('routine bounds not found: %r %r' % (start, end))

print('replacing lines %d..%d' % (start + 1, end))

body = """note_to_period:
\tasl a
\ttay\t\t\t\t\t; note*2 -> index into noteTable
\tlda noteTable,y
\tsta tmpv
\tlda noteTable+1,y
\tsta tmpv+1
\t; mul = P << 3
\tlda tmpv
\tasl a
\tsta mul
\tlda tmpv+1
\trol a
\tsta mul+1
\t; mul = (P<<3) - P = P*7
\tlda mul
\tsec
\tsbc tmpv
\tsta mul
\tlda mul+1
\tsbc tmpv+1
\tsta mul+1
\t; mul = P*14
\tasl mul
\trol mul+1
\t; mul >>= 10   (P*14 <= 23926, so the result is <= 23)
\tldx #$0A
@shr:
\tlsr mul+1
\tror mul
\tdex
\tbne @shr
\t; N = 2P - mul
\tlda tmpv
\tasl a
\tsta tmpv
\tlda tmpv+1
\trol a
\tsta tmpv+1
\tlda tmpv
\tsec
\tsbc mul
\tsta tmpv
\tlda tmpv+1
\tsbc mul+1
\tsta tmpv+1
\tlda tmpv
\ttax
\tldy tmpv+1
\trts

"""

lines[start:end] = body.split('\n')

# make sure the 'mul' zero-page pair exists
src = '\n'.join(lines)
if not re.search(r'^mul:', src, re.M):
    src = src.replace('tmpv:       .res 1', 'tmpv:       .res 1\nmul:        .res 2')
    print('added mul to ZEROPAGE')

open(p, 'w', encoding='utf-8').write(src)
print('total lines', len(src.split('\n')))
