"""Print the packer's own catalog bookkeeping for a freshly built disk.

The on-disk catalog is decoded by tools/a2_dsk_verify.py; this asks dos33.py
itself which track/sector it recorded for each file, so the two views can be
compared.  A T/S-list pointer that lands on the catalog track means the file
cannot be found by real DOS.
"""

import importlib.util
import os
import sys

DOS33 = r"C:\dev\pom2games\dev\tools\dos33.py"
MASTER = os.path.join(os.path.dirname(DOS33), "dos33_system.bin")


def load():
    spec = importlib.util.spec_from_file_location("dos33", DOS33)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    mod = load()
    out = sys.argv[1]
    bins = sys.argv[2:]
    img = mod.Dos33Image(MASTER, 254, read_fast=True)
    for a in bins:
        name, rest = a.split("=", 1)
        path, addr = rest.split("@")
        data = open(path, "rb").read()
        payload = bytes([int(addr, 16) & 0xFF, int(addr, 16) >> 8])
        payload += bytes([len(data) & 0xFF, len(data) >> 8])
        payload += data
        img.add_file(name, mod.TYPE_B, payload)
    img.save(out)

    bad = 0
    for tl, sl, ft, name, n in img.catalog:
        flag = ""
        if tl == mod.VTOC_T:
            flag = "  <-- T/S LIST ON THE CATALOG TRACK"
            bad += 1
        print("  %-9s tl=%d sl=%d  nsect=%d%s" % (name, tl, sl, n, flag))
    print("free sectors %d" % img.free_sectors())
    print("RESULT: %s" % ("OK" if bad == 0 else "%d file(s) point at the catalog" % bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
