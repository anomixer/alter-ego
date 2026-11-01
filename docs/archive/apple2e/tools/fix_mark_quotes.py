"""Close the character-constant quotes on the MARK invocations.

ca65 needs both quotes for a character constant ('1'); the MARK calls were
written with an opening quote only, which ca65 reports as "Illegal character
constant" / "Newline in string constant".  Two of them sit on a labelled line
(`main: MARK '1`), so the pattern must not anchor at the start of the line.
"""
import io
import re

path = 'src/a2/hgrdemo2.s'
src = io.open(path, encoding='utf-8').read()

def fix(m):
    head, val = m.group(1), m.group(2)
    if val.startswith("'") and not val.endswith("'"):
        val += "'"
    return head + val

out = re.sub(r"(?<!\w)(MARK\s+)(?!\bch\b)(\S+)", fix, src)
io.open(path, 'w', encoding='utf-8').write(out)
print([l.strip() for l in out.splitlines() if 'MARK' in l])
