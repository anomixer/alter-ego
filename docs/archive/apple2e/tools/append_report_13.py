import io, sys

p = r'C:\dev\alter-ego\docs\PORT-APPLE2-EVAL.md'
src = io.open(p, encoding='utf-8').read()

section = """

---

## 13. 外部參考 `C:\\dev\\pom2games`(本輪新增,重大)

使用者指點:`C:\\dev\\pom2games` 內有成熟的 Apple II 開發套件(VERHILLE Arnaud,GPL-3.0)。
它直接推翻了我兩處自行推導的佈局,並補上我缺的驗證工具。**以下每條都有原始碼行號。**

### 13.1 HGR 掃描線公式 — 我錯了,已修正並逐位元組驗證

套件兩處獨立來源一致:

- `dev/lib/hgr/hgr_scanline.inc`:`addr[y] = $2000 + (y%8)*$0400 + ((y/8)%8)*$80 + (y/64)*$28`
- `dev/lib/hgrc/hgr_layout.h`:`HGR_ROW_ADDR(base,y) = base<<8 + ((y&7)<<10) + (((y>>3)&7)<<7) + (y>>6)*40`

即 **1024 ↔ (y%8)、128 ↔ ((y//8)%8)、40 ↔ (y//64)**。

我先前用的 `2560*(y//64) + 320*((y//8)%8) + 40*(y%8)` 把正確的三個係數**指派到錯誤的項**。
關鍵教訓:它仍然是 192 條互不重疊的 40-byte 帶(自洽排列),所以「重疊檢查」會通過 ——
这正是這個 bug 能躲過自我一致性測試的原因。

| y | 我(錯) | 正確 |
|---|---|---|
| 1 | $2028 | **$2400** |
| 8 | $2140 | **$2080** |
| 64 | $2A00 | **$2028** |
| 128 | $3400 | **$2050** |
| 191 | $3DD8 | **$3FD0** |

只有 y=0 剛好相同。佈局末端在 `$3FF8`(頁尾 8 bytes 自然留空),我的只到 `$3E00`。

`tools/hgr_layout.py` 已改用正確公式;`tools/check_hgr_table.py` 對套件表格做**逐位元組比對:
192 條全數一致**。

### 13.2 DHGR 幾何 — 我先前假設的 640×2bpp/160B 是錯的

來源 `dev/lib/hgrc/dhgr.c:19-25`:

```c
byte = x / 7u;                                  /* x: 0..559  -> 0..79 */
dhgr_addr = HGR_ROW_ADDR(dhgr_base, y) + (byte >> 1);   /* 40 B/line/bank */
dhgr_aux  = (byte & 1u) ^ 1u;                   /* 偶數 byte -> aux,奇數 -> main */
dhgr_mask = 1u << (x % 7u);
```

- 寬 **560 px**(`DHGR_WIDTH 560u`,`DHGR_COLOR_WIDTH 140u`),**7 px/byte**
- 每線 **80 bytes** = 40 main + 40 aux → **每頁 15,360 B**(我原以為 30,720 B,資產直接減半)
- 掃描線公式**與 HGR 完全相同**,base = $2000(page1)/ $4000(page2)
- 顏色:`color_bits(c) = ((c>>1)|(c<<3)) & 15`;`pattern = color_bits*0x1111`;
  四個樣板 byte = `(pattern >> ((i*7)&3)) & 0x7F`,i=0..3 依序為
  **[aux偶, main偶, aux奇, main奇]**(位移依序 0,3,2,1)
- 顏色編號同 LORES:0 BLACK … 9 ORANGE … 15 WHITE

### 13.3 DHGR 硬體偵測(可直接沿用)

`dev/lib/hgrc/dhgr_asm.s`:

- 擴充 80 欄卡偵測:`lda $FBB3; cmp #$06`
- 寫 $55/$AA 到 main/aux 的 $2000,再寫 $66/$33 測 $4000 的上半部獨立性
- **DHGR 必須 80STORE OFF**;`RAMRDON=$C003`、`RAMWRTON=$C005`
- aux 讀取用**拷到 zero page 的 trampoline** 執行,這樣 RAMRD 不會把執行中的程式碼換掉
- IRQ 狀態需保留;進入時為 main RAMRD/RAMWRT + 一般 ROM

### 13.4 實測效能基準(支持我的 Phase 3 判定)

`dev/examples/dhgr/README.md`:3 個 6×6 遮罩精靈,優化後 **10 秒 299 幀 ≈ 30 fps**
(優化前僅 37 幀),在 ~1 MHz 的 IIe 核心上。

換算:10 s × 1.023 MHz ÷ 299 ≈ **34,214 CPU 週期/顯示幀**。
我估的 9 顆 DHGR 精靈 = 25,434 週期 = **74%** →
**DHGR 在 30 fps 可行,60 fps 不可行**,與 §10 的判定一致(出路 B)。

### 13.5 記憶體地圖(套件已驗證的 DOS 3.3 約束)

```
$0000-$004F  Monitor / DOS(勿動)
$0050-$00FF  程式 ZEROPAGE(要還原才能回 DOS)
$0100-$01FF  堆疊
$0200-$02FF  input buffer(執行中自由)
$0300-$03FF  DOS / Monitor 向量(勿動,$03F2 = RESET)
$0400-$07FF  text page 1
$0800-$0FFF  DOS 保留的 BASIC HELLO(勿壓)
$1000-$1FFF  自由(LOWBSS)
$2000-$3FFF  HGR page 1
$4000-$5FFF  HGR page 2
$6000-$95FF  BRUN 的 binary(**上限 13.8 KB**),其後 BSS / C 堆疊
$9600-$BFFF  DOS 3.3
```

**衝擊:我的 `ae2` 是 15,221 B > 13.8 KB** → 必須縮小,或改用 DHGR 那套
「code 放 $6000、畫面用 $2000-$5FFF」的配置(套件 DHGR C 設定即如此)。

### 13.6 可直接採用的工具

| 工具 | 用途 | 狀態 |
|---|---|---|
| `dev/tools/a2run` | **無視窗 Apple II 模擬器**(C99,6502 NMOS 過 Klaus Dormann 測試),腳本 `wait:/key:/shot:PNG/peek:/poke:/text:/spk/dsk:` | 本機無 C 編譯器;`C:\\dev\\llvm-mos-sdk\\install\\bin\\clang.exe` 可用,zlib 僅供 PNG IDAT → 改 stored-deflate 即可,**建置中** |
| `dev/tools/a2shot` | POM2 核心,支援 //e + aux(DHGR)、附 Apple //e / Disk II ROM | **arm64 macOS only**,本機不可用 |
| `dev/tools/dos33.py` + `dos33_system.bin` | 產生**可開機** DOS 3.3 映像(系統軌 0-2 內建) | 可採用;解決我映像內無 DOS 的問題 |
| `dev/cc65/apple2_hgr.cfg`、`apple2_hgr_c.cfg`、`crt0_apple2.s` | 已驗證的 ld65 配置 + 含正確回 DOS 的 crt0 | 可採用(取代我手寫的 `a2.cfg`) |
| `dev/lib/hgr/hgr_sprite16.asm` | 成熟遮罩精靈引擎 | 可參考/採用 |
| `dev/lib/apple2c/apple2frame.h` | 幀節拍(IIe 用 VBLBAR,II/IIc 用計時) | 可採用 |
| `dev/bench/baseline.json` | 週期預算基準 | 可用來校準我的估算 |

### 13.7 授權注意

套件為 **GPL-3.0**。採用其原始碼(`a2run`、`dos33.py`、`crt0_apple2.s`、圖形庫)
会使本專案衍生部分受 GPL 約束;目前作為**內部移植工具與參考**使用,
若要釋出需連同授權一併處理。`dos33_system.bin` 與 ROM 為 Apple Computer 著作。

### 13.8 尚未解決

- `a2run` 是 **Apple II+ 48 KB** 核心(無 aux RAM)→ **DHGR 無法在 a2run 驗證**,
  只能驗 HGR/文字;DHGR 需要 a2shot(arm64)或 AppleWin。
- `a2run` 無 Mockingboard → 音樂仍需 AppleWin 的 `-wav-mockingboard` 或其他實測。
- 本機無音效卡,AppleWin 的音效驗證需走檔案輸出繞過 DirectSound。
"""

io.open(p, 'w', encoding='utf-8').write(src + section)
print('appended, total chars', len(src) + len(section))
