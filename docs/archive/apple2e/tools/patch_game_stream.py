import io, re

p = 'src/game.c'
s = io.open(p, encoding='utf-8').read()

# 1. includes: keep the NES build byte-identical, swap the 26 level arrays for
#    the streamed pointer on the Apple //e build.
inc_old = ''.join('#include "map%d.h"\n' % i for i in range(26))
inc_new = ('#ifdef __APPLE2ENH__\n'
           '#include "a2/level_stream.h"\n'
           '#else\n'
           + inc_old +
           '#define MAP_PTR(n) map##n\n'
           '#endif\n')
assert inc_old in s, 'include block not found'
s = s.replace(inc_old, inc_new, 1)

# 2. level_ptrs table: mapN -> MAP_PTR(N)
s2, n = re.subn(r'\bmap(\d+),palGameBG(\d)', lambda m: 'MAP_PTR(%s),palGameBG%s' % (m.group(1), m.group(2)), s)
print('level_ptrs entries rewritten:', n)
assert n == 26, n
s = s2

# 3. stream the level from disk just before it is decoded
old = '\tunrle_vram(level_ptrs[i],0x2000);'
new = ('\tif(lv_load((unsigned char)level)) lv_fail_halt();\n'
       '\tunrle_vram(level_ptrs[i],0x2000);')
assert s.count(old) == 1, s.count(old)
s = s.replace(old, new, 1)

io.open(p, 'w', encoding='utf-8').write(s)
print('game.c patched')
