import io

DOC = 'docs/PORT-APPLE2-EVAL.md'

SECTION = """
## 14. II+ 無頭驗證鏈落地(a2run)— 七個根因一次收干净

本節是 Phase 0/3 在 `tools\\a2run`(Apple II+ NMOS 6502 核心)上跑出來的結果。
重點不在「跑起來了」,而在七個會咬人的坑,每個都已用證據定位並修掉。

### 14.1 驗證鏈的最後一哩:`-t none` 是唯一可行目標

| 目標 | 結果 |
|---|---|
| `-t apple2enh` | //e 65C02,可用 `BRA`;定義 `__APPLE2ENH__` |
| `-t apple2` | 嚴格 NMOS 6502(不能用 `BRA`),但 C 執行庫會把 `bltu2` **硬塞在 `$D39A`** |
| `-t none` | 無 C 執行庫(只有 `zerobss/copydata/initlib/donelib`),**唯一能在 II+ 核心上跑的目標** |

`bltu2` 的位置寫死在 cc65 的 `lc-copy-applesoft.o` 裡;把 `__LCADDR__` 改成 `$1000`
也不會動它。結論:**`-t apple2` / `-t apple2enh` 的 C 程式永遠無法在 II+ 核心(a2run)
上執行**,C 層的驗證(musictest、hgrtest)只能上真 //e(AppleWin)。
因此 II+ 驗證程式必須是純組合語言(`src/a2/hgrdemo2.s`)。

移植可攜性:`bra` 是 65C02 指令。`sys.s / hgr.s / dhgr.s` 裡的 `bra` 全數換成 `jmp`
(`tools/fix_nmos_portable.py`),三個檔案在 `-t apple2` 與 `-t apple2enh` 下都組得過。

### 14.2 根因一:BIN 標頭被疊了兩次(所有「main 進不去」的總根因)

`dos33.py --bin NAME=file@addr` 自己會寫 `load(LE) + len(LE) + data`。
我的打包器又前置了一次同樣的標頭 → DOS 剝掉它自己那層,記憶體裡留下我那層 →
**整個映像向後位移 4 bytes**,所有絕對位址全部錯 4。

對照實驗(`minimal.s`,無 crt0、無函式庫)抓到的鐵證:

```
4000: 00 40 36 00 AD 51 C0      ; 標頭 + 程式碼  -> 錯
4000: AD 51 C0                  ; 修好後:純程式碼 -> 對
```

修法治則:**打包器只輸出 `ld65 -t none` 的裸映像,絕不自帶標頭**
(`tools/rawbin.py`、`tools/apple2bin.py` 皆已改),且 cfg 的 `STARTADDRESS` 必須等於
`@addr`。kit 的 `dist/HGR.dsk` 在 `$6000` peek 到的是 `D8 BA 8E C3 ...`(crt0 的
`CLD;TSX;STX`),沒有標頭 —— 與此結論一致。

### 14.3 根因二:`$4000` 不是可用的 BRUN 載入位址

同一支程式(7.6 KB):

| 載入位址 | `until:_main` |
|---|---|
| `$4000` | **永遠到不了**,PC 停在 DOS 的 `$FD1D/$FD21` |
| `$6000` | **抵達 `_main`**,開始繪圖 |

kit 的慣例也是 `$6000`(`apple2_hgr_c.cfg` 的 RAM = `$6000`,`--bin HGR=hgr.bin@0x6000`)。
**採用 `$6000`。** 注意 kit 文件給 II+ 48K 的 BRUN 上限是 13.8 KB(`$6000-$95FF`),
之後接 BSS 與 C stack;`$4000-$5FFF` 那兩頁留給 HGR page2。

### 14.4 根因三:`LORES`($C056)與 `HIRES`($C057)搞反

a2run 會警告 `lores not rendered (shot shows HGR memory)` —— 螢幕停在 lo-res,
截圖看到的是記憶體而不是圖。`hgr.s:82` 與 `hgrprobe.s:20` 打了 `LORES`,`minimal.s`
用了 `$C051/$C053`。cc65 `asminc/apple2.inc` 的正確值(注意 **不在 `include/`**):

```
TXTCLR $C050  TXTSET $C051  MIXCLR $C052  MIXSET $C053
LOWSCR $C054  (page1)       HISCR $C055   (page2)
LORES  $C056  (lo-res)      HIRES $C057   (hi-res)
DHIRESON $C05E              DHIRESOFF $C05F
```

三處皆已修正,警告消失。

### 14.5 根因四:迴圈計數器被 `tax` 踩掉

彩階迴圈把「欄位計數器」放在 X,而 `hgr_put8` 的圖塊索引也在 X → `tax` 直接蓋掉計數器,
`inx / cpx #40` 永遠到不了 40。改放在 BSS(`col`、`rampy`)後正常。

順帶記錄:`rampy/col` 放進 `.segment "ZEROPAGE"` 會讓彩階卡住(ZEROPAGE 長到 50 B),
放 BSS 才跑得完 —— 此現象尚未完全解釋,列為追蹤項。

### 14.6 根因五(最關鍵):`hgr_put8` 原地推進 `dst_ptr`

`hgr_put8` 每畫一行就把 `dst_ptr` 加 `$28`,8 行後 `dst_ptr` 已前移 `$140`。
`hgr_set_row` 只在「列」開頭設一次起點,於是**同一列裡第 2、3、… 個圖塊的起點逐次往下
滑 8 行**,寫入位址一路走出 HGR 頁(`$2000-$3FFF`)、繞回並**覆寫程式自己的記憶體**
→ 程式被自己改寫 → 無限迴圈。

這解釋了之前所有詭異症狀:計數器明明在走(`loops=FF, rampy=04, col=26`)、
`hgr_line_off` 全 192 筆逐筆驗證正確、分支位移正確,卻永遠到不了下一個標記。

修法:ZEROPAGE 增加 `cur_ptr`,`hgr_put8` 每次進入時把 `dst_ptr` 複製到 `cur_ptr`,
迴圈只推進 `cur_ptr`,`dst_ptr` 保持不變。修完立刻抵達精靈迴圈(`$0400` 標記 = `$38`='8')。

### 14.7 量測到的階段成本(a2run 為 1:1 計時,已校準)

校準基準:`hgr_clear` 寫 8,192 個位元組耗 82,201 cycles = **10.0 cycles/store** ✓。

| 階段 | cycles |
|---|---|
| `_main` → `hgr_clear` | 46 |
| `hgr_clear`(整頁清空 7,680 B) | 82,201 |
| `hgr_set_tiles` → 標記 '5'(RLE 解碼整張畫面 7,680 B) | 405,825(≈53 cycles/byte) |

對 17,030 cycles/框 而言:**整頁清空 ≈ 4.8 框、整頁 RLE 重繪 ≈ 23.8 框**。
這坐實 §10 的路線決定 —— 逐框全圖重繪不可行,只能走精靈局部重繪。

### 14.8 已固化進管線

`build\\a2\\build.bat` 新增 **4b) II+ 驗證段**:`-t none` + kit `crt0_apple2.s`(排第一)
+ kit `apple2_hgr_c.cfg` + `rawbin.py ... 0x6000`,產物 `HGRDEMO6` 一併打包進
`ae2_boot.dsk`。管線全綠,實測:

```
a2run --disk build\a2\ae2_boot.dsk key:"HELLO\r" wait:1500 pc peek:400:2
  PC=6212  0400: 38      ; '8' = 已進入精靈迴圈
```

截圖 `build\\a2\\demo7.png`(560×384、6 色、約 108,200 個非黑點、24 個 16 列帶皆有墨)
= 關卡畫面 + 24 列彩階 + 精靈。下方那片「雜訊」是 HGR 1-bit 對細圖的正常抖動,不是錯誤。

### 14.9 a2run 使用須知(踩過的坑)

- `until:ADDR:N` 的 **N 是「框」**(×17,030 cycles),且**只觀察未來**;要放在程式結束之前。
- 逾時會印 `until ADDR cycles=<N*17030> PC=<實際>` 並以 exit 3 收場。
  **務必確認 `PC == target`**,否則那個 cycles 值是時間上限,不是成本。
  我早期把兩次逾時解讀成「彩階成本 136,240,000 cycles」與「`$62F8` 花 501,871 cycles」,
  兩者都是逾時,不是成本。
- 按鈕極性有反:`btn:n,v` 在「未按下」時回 `$00`;繞法 `btn:0,1 btn:1,1 btn:2,1`。
- 開機 RAM 圖樣:`ram[k] = (k&2) ? 0xFF : 0x00`。
- 無 //e 韌體 / aux RAM / language card / 80 欄 / DHGR / 6522 VIA →
  **DHGR 與 Mockingboard 在 a2run 上無法驗證**,只能上 AppleWin。
- `tick_frame()` 在 II+ 上會打死迴圈:它輪詢 `RDVBLBAR $C019`,而 II+ 上該位址是鍵盤閂鎖
  (bit7 永遠不會置 1)。已用 `.ifdef __APPLE2ENH__` 分流(//e 輪詢;II+ 用 BSS 計數延時)。

### 14.10 尚待處理

1. **全遊戲體積**:`game.c` + 素材 > 22 KB → `RODATA` 溢出 `MAIN`、`BSS` 變負。
   Phase 6(neslib 抽象層,188 處呼叫 / 28 支 API)是必經之路。
2. `src/a2/dhgr.s` / `src/a2/spr.s` 尚未對齊已驗證的 80 B/line + bank 奇偶幾何。
3. Mockingboard 輸出驗證需要 AppleWin `-wav-mockingboard`(a2run 無 VIA)。
4. 真 //e(AppleWin)上的 Phase 0/7 執行檢查尚未執行(目前無聲卡,AppleWin 會彈出
   波形對話框遮住主視窗;由 shell 截屏取不到畫面)。
5. 舊磁碟 `ae2_demo.dsk` / `ae2_min.dsk` 是雙標頭時期產物,需以新打包器重包。
"""

text = io.open(DOC, encoding='utf-8', errors='replace').read()
if not text.endswith('\n'):
    text += '\n'
io.open(DOC, 'w', encoding='utf-8').write(text + SECTION)
print('appended; total lines =', len((text + SECTION).splitlines()))
