import re

game = open(r'build\a2\game.bin', 'rb').read()
mp = open(r'build\a2\game.map', encoding='utf-8', errors='replace').read()

# The map's export list is two columns per line: "name ADDR RLA   name ADDR RLA"
syms = {}
for m in re.finditer(r'(\S+)\s+([0-9A-F]{6})\s+(RLA|REZ|RLZ|REA)', mp):
    syms.setdefault(m.group(1), int(m.group(2), 16))

names = ['pushax', 'pusha', 'pusha0', 'push0', 'popa', 'popax', 'popw', 'pushw',
         'stasptr', 'ldasptr', 'incsp', 'incsp1', 'incsp2', 'decsp', 'decsp1',
         'clrsptr', 'popptr1', 'pushptr1', 'callmain', 'zerobss', 'copydata']

for n in names:
    if n not in syms:
        continue
    a = syms[n]
    if a < 0x6000 or a - 0x6000 >= len(game):
        continue
    blob = game[a - 0x6000:a - 0x6000 + 26]
    print('%-10s $%04X  %s' % (n, a, blob.hex(' ')))
