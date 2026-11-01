import sys
def decode(path):
    data = open(path,'rb').read()
    tag=data[0]; out=bytearray(); i=1; last=0
    while i<len(data):
        b=data[i]; i+=1
        if b!=tag: out.append(b); last=b
        else:
            n=data[i]; i+=1
            if n==0: break
            out.extend([last]*n)
    return out
for name in ('titleh','creditsh'):
    out = decode(r'build\art\%s.bin' % name)
    b7clear = sum(1 for b in out if not (b&0x80))
    print("%s: %d bytes, %d bit7-clear (%.1f%%)" % (name, len(out), b7clear, 100*b7clear/len(out)))
