import io

p = r'C:\dev\alter-ego\docs\PORT-APPLE2-EVAL.md'
s = io.open(p, encoding='utf-8').read()

anchor = "### 13.3 DHGR 硬體偵測(可直接沿用)"
add = """**重要推論(已落地):DHGR 位址表與 HGR 位址表是同一張。**
`addr = HGR_ROW_ADDR(base,y) + (byte>>1)`,byte 0..79 → 位移 0..39,
所以每條線在**同一組 40 個位址**上跨兩個 bank,區分只靠 byte 同偶性。
`tools/dhgr_layout.py` 已改寫為輸出這張表(span `$2000..$3FF8`,15,360 B =
main 7,680 + aux 7,680),並附 16 色樣板自檢:

```
colour  5 GRAY1  bits=1010  pattern[aux-even,main-even,aux-odd,main-odd]=$2A $55 $2A $55
colour 10 GRAY2  bits=0101  pattern[aux-even,main-even,aux-odd,main-odd]=$55 $2A $55 $2A
colour 15 WHITE  bits=1111  pattern[aux-even,main-even,aux-odd,main-odd]=$7F $7F $7F $7F
colour  0 BLACK  bits=0000  pattern[aux-even,main-even,aux-odd,main-odd]=$00 $00 $00 $00
```

`$2A/$55` 交錯正是經典 DHGR 灰色樣板,`$7F` 全白 —— 與外部知識吻合,
可作為公式正確性的旁證。

**資產影響:DHGR 每頁從我原估的 30,720 B 降到 15,360 B。**
重跑後 26 張地圖的 RLE 總量 = **73,354 B**(min 1,349 / max 4,715 / avg 2,821)。

"""
if anchor not in s:
    raise SystemExit('anchor not found')
s = s.replace(anchor, add + anchor, 1)

tail = """

### 13.9 管線現況(本輪)

`build\\a2\\build.bat` 已重寫並**全綠通過**,順序:

1. `tools/a2_assets.py` — NES CHR → HGR/DHGR 圖磚、地圖 → 畫面(RLE)
2. `tools/hgr_layout.py` — 掃描線表(正確公式)
3. `tools/dhgr_layout.py` — DHGR 表(= HGR 表)+ 佈局自檢 + 16 色樣板自檢
4. `tools/check_hgr_table.py` — **與 kit 表格逐位元組比對:192 條全中**
5. `cl65 -C src/a2/a2_4000.cfg` → `hgrtest40`(**BRUN 載入 $4000**)
6. `tools/apple2bin.py` — AppleSingle → DOS 3.3 BIN 載入檔
7. kit 的 `dev/tools/dos33.py` → **`ae2_boot.dsk`:可開機 DOS 3.3,`HELLO` 自動 `BRUN HGRTEST`**
8. `ca65 src/a2/ftm.s` — Mockingboard + FamiTone 播放器**組譯通過**

兩個新發現值得記:

- **cc65 apple2 輸出的 AppleSingle 內層沒有 BIN header。** area 1 直接是 6502 碼
  (`A2 FF 9A 20`),載入位址在 **area 11(exec args)末兩 bytes、大端**
  (預設 `$0803`)。`tools/apple2bin.py` 就是照這個實際觀察寫的。
- **載入 $0803 會壓掉 DOS 保留的 BASIC HELLO($0800-$0FFF)。**
  改連結到 `$4000` 後可用空間變成 `$4000-$95FF` = **22,016 B**,
  `ae2`(15,163 B)直接放得下 —— §13.5 的 13.8 KB 限制只在 $6000 起算時才成立。

`ftm.s` 體積:**CODE 1,038 B / RODATA 12 B / BSS 143 B / ZEROPAGE 23 B**。

"""
s = s.rstrip() + tail
io.open(p, 'w', encoding='utf-8').write(s)
print('report updated, chars', len(s))
