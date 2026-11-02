# Alter Ego → Apple II 移植可行性評估

> **路徑說明（2026-11-01）**：本文件寫於上游工作樹 `C:\dev\alter-ego` 內，文中 `build/…`、`src/a2/…`、`tools/…` 都以那棵樹為基準。該樹已於 2026-11-01 移除；保留的 //e 工具在 [docs/archive/apple2e](archive/apple2e/)，PRG 來源樹在 [iigs/prg-src](../iigs/prg-src)。


> **2026-10-26 狀態更新（使用者決定）**：本文件是 2026-02 的 //e DHGR 評估。DHGR 的固定色盤／色塊限制會讓 NES 原色明顯「demake」，因此 **//e DHGR 不再作為主要移植目標**；本文件降為歷史與 game-logic 參考，不再投入實作。現行主線請看 [PORT-IIGS-SILKY-EVAL.md](PORT-IIGS-SILKY-EVAL.md)（IIgs SHR 可從 4096 色 CLUT 選 16 色，對 NES palette 準確得多）。

分析日期:2026-02。分析對象:`C:\dev\alter-ego`(NES/cc65 版)。
評估目標:先評估 **Apple IIe + DHGR + Mockingboard**;若不可行,再評估 **Apple II + VERA(a2vera)**。
所有規格皆查證(本地原始碼引用或網路來源),未查證項目明確標記。

---

## 0. 結論摘要

| | 路線 A:IIe DHGR + Mockingboard | 路線 B:Apple II + VERA(a2vera) |
|---|---|---|
| 可行性 | **可行**(需自寫 3 個 assembly 引擎) | **可行且功能 1:1**(管線現成) |
| 硬體需求 | 標準 IIe(128K)+ 80列卡(內建)+ Mockingboard/clone | 標準 II + a2vera VERA 卡 |
| 模擬器可測 | ✅ AppleWin(圖+聲都模擬) | ❌ 無模擬器支援 VERA 卡 |
| 工具鏈 | cc65 `apple2enh`(本地 `C:\dev\cc65` 已裝) | llvm-mos `mos-apple2e`(本地 SDK 已含,TimePilot 寫的) |
| 現成先例 | deater/dos33fsprogs(同生態 DHGR+PT3 音樂) | `C:\dev\Time-Pilot\TimePilot-IIvera`(完整成品) |
| 圖形 | 640×192、**6 個固定色**、**無硬體精靈** | 640×480、256 色可調色板、**244 硬體精靈** |
| 音樂 | 6 音道 + 2 noise(AY-8910) | 14 PSG 通道 + PCM 取樣 |
| palette fade(16 階) | ❌ 需 dither 模擬 | ✅ 直接支援 |
| DPCM 鼓聲/取樣 | ❌ AY 無 DAC(丟棄或走 1-bit 喇叭) | ✅ PCM 直接播 |
| 磁碟 | DOS 3.3 140KB(單片可容納全部資產) | DOS 3.3 或 ProDOS(TimePilot 用 ProDOS) |
| 主要風險 | 60fps 軟體精靈的週期預算 | 需要實體卡,受眾小 |

**2026-02 建議（已於 2026-10-26 封存，見上方）：** 兩條路線共用「遊戲核心」,平台層做兩個 backend。先做路線 A(可在 AppleWin 驗證、受眾大),VERA backend 作為高畫質備援。

---

## 1. 原始程式分析

### 1.1 專案結構(`C:\dev\alter-ego`)

| 檔案 | 角色 |
|---|---|
| [src/game.c](../src/game.c) | 全部遊戲邏輯,1,606 行純 C |
| [src/neslib.h](../src/neslib.h) / [src/neslib.s](../src/neslib.s) | NES 平台層(PPU/OAM/pad/PPU 時序) |
| [src/famitone.s](../src/famitone.s) | Famitone2 音樂引擎(APU) |
| [src/music_*.s](../src/) | 8 首 FTM 音樂資料 |
| [src/sounds.s](../src/sounds.s) | 16 個 SFX 資料 |
| [src/tileset.chr](../src/tileset.chr) | 8,192 bytes CHR = 256 張 8×8 圖元(2bpp/4 色) |
| [src/map0.h](..)-[map25.h](../src/map25.h) | 26 關,RLE 壓縮的 nametable |
| [src/title.h](../src/title.h) [credits.h](../src/credits.h) [gameover.h](../src/gameover.h) [welldone.h](../src/welldone.h) | 選單/結算畫面(同 RLE nametable) |
| [src/palettes.h](../src/palettes.h) | 5 組背景 + 1 組精靈 + 1 組結算调色板 |
| [src/crt0.s](../src/crt0.s) [src/nes.cfg](../src/nes.cfg) | NES 啟動碼 + 連結器配置 |
| [Makefile](../Makefile) | `cc65 -Oi` → `ca65` → `ld65 -C src/nes.cfg` |

遊戲本體是「Ninja The Action」風格的 2D 動作遊戲(26 關、雙自我交換機制)。

### 1.2 遊戲規格(自 [src/game.c](../src/game.c) 逐項抽出)

| 項目 | NES 規格 | 證據 |
|---|---|---|
| 螢幕 | 256×192(PPU nametable) | `unrle_vram(...,0x2000)`、`scroll()` |
| 遊戲區 | 32×20 格 × 8px = **256×160**,起點 y=48 | `#define MAP_WDT 32`/`MAP_HGT 20`/`TILE_SIZE 8`/`SCREEN_START_Y 48`([game.c:166-170](../src/game.c#L166-L170)) |
| 精靈 | 8×8 硬體精靈,角色用 2 張堆疊成 **8×16** | `oam_spr(x,y,spr,atr,...)` + `spr+0x10`([game.c:1010-1018](../src/game.c#L1010-L1018)) |
| 同屏精靈數 | 8 敵×2 + 4 玩家 + 4 粒子 + 6 狀態 + 暫停 ≈ **22–30 個 8×8** | `OAM_ENEMY/OAM_PARTS/OAM_STATS/OAM_PLAYER`([game.c:88-92](../src/game.c#L88-L92)) |
| 背景動畫 | CHR bank 切換做水流/動畫(每 16 影格) | `bank_bg((frame_cnt>>4)&1)`([game.c:964](../src/game.c#L964)) |
| 逐影格更新 | 物品消失走 vram update buffer | `set_vram_update(items_cnt+1,update_list)`([game.c:891](../src/game.c#L891)) |
| 调色 | 每關 1 組背景调色 + 精靈调色,**16 階 fade** | `pal_fade()`/`pal_fade_to_all()`([game.c:391-404](../src/game.c#L391-L404)、[957](../src/game.c#L957)) |
| 音樂 | Famitone2 **5 通道**(pulse1/pulse2/triangle/noise/DPCM) | `@chn0..@chn4`([music_title.s:3](../src/music_title.s#L3)) |
| 音效 | 16 個 SFX,分 3 個通道播放 | `sfx_play(SFX_ITEM1,2)`([game.c:1216](../src/game.c#L1216)) |
| 影格同步 | 每迴圈一次 `ppu_waitnmi()`(NTSC 60Hz,含 50Hz 跳格) | 60 處呼叫 |
| 輸入 | NES pad:方向 + A/B/Select/Start | `pad_poll()`/`pad_trigger()` |

### 1.3 平台依賴清單(game.c 內 188 處呼叫,28 個 neslib 函式)

| NES 功能 | 呼叫數 | Apple II 對應 |
|---|---|---|
| `ppu_waitnmi` | 60 | 60Hz IRQ tick(需自建,IIe 無 NMI) |
| `oam_spr` / `oam_meta_spr` / `oam_clear` | 40 | **軟體精靈引擎(自寫 asm)** |
| `vram_adr/put/fill/read` + `unrle_vram` | 30 | DHGR 畫面解壓/繪圖(自寫 asm) |
| `pal_*`(all/bg/spr/col/fade/fade_to_*) | 15 | **DHGR 無调色板 → 需 dither 方案** |
| `ppu_off/on_*` | 8 | 關閉/開啟顯示(soft switch) |
| `set_vram_update` | 5 | 影格內小更新(自寫) |
| `bank_bg` | 1 | 以「雙圖元表」取代(記憶體換取) |
| `scroll` | 5 | 選單捲動 → 以 DHGR 雙頁 + 位移實作 |
| `music_play/stop/pause` + `sfx_play` | 30 | **Mockingboard 音樂引擎(自寫/接 deater PT3)** |
| `pad_poll/pad_trigger` | 10 | 搖桿($C061-63 按鈕 + $C064-67 類比)+ 鍵盤 |
| `rand/setrand/memcpy` | 10 | 直接實作(IIe 有 `$C000` 抖動亂數) |

**遊戲邏輯本身(物理、碰撞、AI、關卡流程)完全平台中立,可直接沿用。**

### 1.4 資產體積(實測)

| 資產 | bytes |
|---|---|
| `tileset.chr`(512 張 8×8 圖元,2bpp planar,16 B/張) | 8,192 |
| 26 關地圖(RLE) | 10,414 |
| title/credits/gameover/welldone(RLE) | 1,317 |
| 8 首音樂 + 樂器表 | 6,505 |
| 16 個 SFX | 710 |
| **資產合計** | **27,138** |
| 程式(NES ROM0 上限) | 32,762 |

→ 全部塞進**單片 DOS 3.3 140KB 磁片**綽綽有餘(143,360 bytes)。

**實測更正**:`tileset.chr` = 8,192 B = **512 張**圖元(不是 256;背景用 0-255,精靈由 `PLAYER_SPR_* 0x90-0x97` 落在第二個 4KB bank)。轉換成 DHGR 後仍是 8,192 B(512 × 16 B)。

---

## 2. 目標平台查證

### 2.1 Apple IIe 本體

- CPU 6502 @ 1.023 MHz → **每 60Hz 影格 17,050 cycles**。
- 128KB RAM(Enhanced IIe),含 aux bank(給 80 列 / DHGR 第二頁)。
- cc65 已定義 soft switch(逐字引用 [C:\dev\cc65\asminc\apple2.inc](C:\dev\cc65\asminc\apple2.inc)):
  - `KBD := $C000`、`KBDSTRB := $C010`
  - `CLR80COL := $C000`、`SET80COL := $C001`
  - `TXTCLR $C050`、`TXTSET $C051`、`MIXCLR $C052`、`MIXSET $C053`
  - `LOWSCR $C054`(page1)、`HISCR $C055`(page2)
  - `LORES $C056`、`HIRES $C057`
  - **`DHIRESON := $C05E`、`DHIRESOFF := $C05F`**
  - `RDVBLBAR := $C019`(>127 = 非垂直空白)、`ENVBL $C05B`/`DISVBL $C05A`
  - 搖桿:`BUTN0 $C061`、`BUTN1 $C062`、`BUTN2 $C063`、`PADDL0-3 $C064-$C067`、`PTRIG $C070`
  - 語言卡:`ROMIN $C081`、`LCBANK2 $C083`、`LCBANK1 $C08B`

### 2.2 DHGR(Double Hi-Res)

- 640×192、**2 bpp**、每條 scanline **80 bytes**、每頁 **8KB**;兩頁 = 16KB。
- **6 個固定色**:byte 在 scanline 的偶/奇位置決定使用哪組调色板
  - 組 A:`00`=黑、`01`=綠、`10`=紫、`11`=白
  - 組 B:`00`=黑、`01`=橙、`10`=藍、`11`=白
- 開啟 DHGR 需要:`SET80COL`($C001)+ `EIGHTYCOLON`($C00D)+ `HIRES`($C057)+ `MIXCLR`($C052)+ `PAGE2`($C055)+ `DHIRESON`($C05E)。
  - 本地證據:`DHIRESON := $C05E` 於 cc65 [apple2.inc:76](C:\dev\cc65\asminc\apple2.inc#L76);`PAGE1/PAGE2/LORES/HIRES/EIGHTYCOLON/80STORE/ALTZP` 於 deater `graphics/dgr/animations/hardware.inc`。
  - **未查證**:`MIXED`/`CLIG` 的符號名稱未出現在我抓到的 deater 檔案中(cc65 端有 `MIXCLR/MIXSET`)。
- **無硬體精靈** → 全部精靈要軟體 blit。
- **無可寫调色板** → `pal_fade()` 的 16 階淡入淡出**無法直接實作**,只能以 dither(交錯雜點)預先產生 4 級亮度圖元來近似。
- 地圖適配:32×20 格 × 8px = 256×160 px → DHGR 每列 64 bytes × 160 列 = **10,240 bytes**,剛好放進一個 DHGR 頁(8KB)的 4/5。
- 圖元適配:NES 圖元是 2bpp/4 色(實測 256 張,4 色都有使用:黑 57.3%、色1 12.1%、色2 9.9%、白 20.7%)→ **結構上 1:1 對應 DHGR 的 4 色调色板**,每張 8×8 圖元 DHGR 版 = 16 bytes(256 張 = 4KB,比 NES 的 8KB 還小)。

### 2.3 Mockingboard

AY-3-8910/8913 規格(逐字引用自 `Michaelangel007/apple2_mockingboard/test_mock.s`):

```
MOCK_TONE_LOW   = $0   ; Tone Control Fine   Reg 0/2/4: lo 8-bit
MOCK_TONE_HIGH  = $1   ; Tone Control Coarse Reg 1/3/5: hi 4-bit
MOCK_NOISE      = $6   ; Noise Period        Reg 6    : 5-bit
MOCK_CHANNELS   = $7   ; Disabled Chans Mask Reg 7    : 6-bit
MOCK_AMPLITUDE  = $8   ; Amplitude           Reg 8/9/A: 5-bit
MOCK_ENV_LOW    = $B   ; Envelope Fine       Reg B    : lo 8-bit
MOCK_ENV_HIGH   = $C   ; Envelope Coarse     Reg C    : hi 8-bit
MOCK_ENV_TYPE   = $D   ; Envelope Shape      Reg D    : 4-bit
AMP_STATIC=%01111  AMP_DYNAMIC=%10000
ENV_CONT/ATTACK/ALT/HOLD (C K A H)
demo_note_1: .byte $0F,$0F,$0F   ; [8] Amp A, B, C  → 音量 16 級(0-15)
```

→ 每顆 AY = **3 個音道(12-bit 音調)+ 1 noise(5-bit)+ 1 envelope**;Mockingboard 有 2 顆 = **6 音道 + 2 noise**。NES 的 4 個可樂通道(pulse×2 + triangle + noise)**在通道數上可 1:1 對應**;DPCM 無對應物。

**位址方案(兩種板子不同,需查證)**:
- 原版 Sweet Micro Systems Mockingboard = **2× SY6522 VIA + 2× AY-8913**,透過 VIA 的 port A(資料/暫存器號)+ port B(strobe 位元:`$7`=latch、`$6`=write、`$4`=idle)操作。`test_mock.s` 預設把 VIA 放在 **slot 4 的 ROM 空間 `$C400/$C401` 與 `$C480/$C481`**:
  ```
  ADDR6522    = $C400   ; *** Default Mockingboard to slot 4 ***
  MOCK1_OR_B  = ADDR6522+0 ; ($C400)
  MOCK1_OR_A  = ADDR6522+1 ; ($C401)
  MOCK2_OR_B  = $C480 / MOCK2_OR_A = $C481
  MOCK1_PokeXY: stx MOCK1_OR_A / jsr MOCK1_SetReg / sty MOCK1_OR_A / jmp MOCK1_SetData
  MOCK1_SetReg: lda #_6522_LATCH($7) ; MOCK1_SetData: lda #_6522_WRITE($6) / sta MOCK1_OR_B / lda #_6522_PORT_B($4) / sta MOCK1_OR_B
  ```
- 無 VIA 的 clone(Echo / Mockingboard Clone)用直接 I/O(`$C600/$C601`、`$C610/$C611`)。
- **未查證完成**:`MOCKINGBOARD` 字串偵測位址(常見說法 `$C6F8`)與 ROM 空間 `$C800-$CFFF` 的確切關係 — 由 subagent 查證中,結論以 `docs/` 更新為準。

### 2.4 時序(60Hz)

- NES 用 NMI 做影格同步;Apple II **沒有 NMI**。
- 可用做法(本地證據 + 文件):
  1. `RDVBLBAR := $C019` 輪詢(>127 = 非垂直空白)→ 最簡單,不需要 ROM 權限。cc65 [apple2.inc:62](C:\dev\cc65\asminc\apple2.inc#L62)。
  2. 6522 VIA T1 產生 60Hz IRQ + 把 IRQ handler 寫進 IIe 的 ROM bank2(`LCBANK2 $C083` 寫入模式)。
  3. ProDOS interruptor(cc65 支援,但**僅 ProDOS,不支援 DOS 3.3**)。
- cc65 官方文件逐字:「**DOS 3.3: The DOS 3.3 API doesn't support disk I/O, and it doesn't support the interruptor**」(https://cc65.github.io/doc/apple2.html §8.1)。
- deater 的 DHGR 示範(`irq_wait.s`)是 busy-wait 一個由外部 IRQ handler 遞減的 `IRQ_COUNTDOWN`(註解 50Hz),該批檔案內**沒有** VIA 設定,也沒有 ROM patch 程式碼。

### 2.5 DOS 3.3 磁碟

- 影像大小 143,360 bytes(35 軌 × 16  sectors × 256)——本地證據:`C:\dev\a2vera\a2vera_dos33.dsk` = 143,360 bytes。
- 單檔上限 128KB(512 sectors)。
- BIN 檔頭 = 2 bytes load address + 2 bytes length;`BRUN` 執行。
- 本地工具證據:
  - **ACME** `-f apple` 產生 DOS 3.3 binary header(`C:\dev\a2vera\README.md:127`)。
  - **Cadius**(Brutal Deluxe)產生/寫入 DOS 3.3 與 ProDOS 影像:`cadius-145.exe addfile pt3plr.po /pt3plr pt3plr.system#FF2000`(https://github.com/StewBC/pt3plr README)。
  - **AppleCommander** `-as` 把 cc65 的 AppleSingle 輸出放到 DOS 3.3 / ProDOS 影像(https://cc65.github.io/doc/apple2.html §2)。
  - `C:\dev\Time-Pilot\TimePilot-IIvera` 用自寫 Python(`build_disk.py`/`build_hdv.py`)產生 `.po`/`.hdv`。
  - **找不到** `a2vera_dos33.dsk` 的產生腳本(只有成品影像)。

---

## 3. 工具鏈盤點(本地)

| 工具 | 狀態 | Apple II 支援度 |
|---|---|---|
| `C:\dev\cc65`(ca65/cc65/ld65/cl65) | 已裝 | `apple2.lib` 1,837,960 / `apple2enh.lib` 1,845,619 bytes;`asminc/apple2.inc` 有 DHGR soft switch;**TGI 只有 lores(40×48)與 hires(280×192),無 DHGR;無 Mockingboard/AY 驅動** |
| `C:\dev\llvm-mos-sdk` | 已裝 | `mos-platform/apple2e` + `install/bin/mos-apple2e-clang.bat` + `mos-apple2e.cfg`;`apple2e.h` 是 **VERA 介面**(檔頭註解「Copyright 2026 Time-Pilot-IIvera」),`link.ld` 產 ProDOS BIN @ `$2000`,程式空間 `$2000-$BBFF`(~40KB),`__stack=$BE00` |
| `C:\dev\a2vera` | 已裝 | ACME 組裝 + `-f apple` DOS 3.3 header;VERA 於 slot 2/4 |
| `C:\dev\Time-Pilot\TimePilot-IIvera` | 已裝 | llvm-mos + VERA + ProDOS 打包管線(完整先例) |

**cc65 官方 Apple II 限制(逐字,§8.1)**:「The standard setup of the cc65 runtime system **doesn't support DOS 3.3 disk files**」。
→ 走 DOS 3.3 時,檔案 I/O 要用 ACME/自寫 DOS 3.3 呼叫(`PR#0` + JSR $B7xx)或改走 ProDOS。

---

## 4. 可行性判定

### 4.1 路線 A:IIe DHGR + Mockingboard → **可行**

**週期預算估算(6502 @1.023MHz,17,050 cycles/frame)**

| 工作 | 估算 |
|---|---|
| 8×16 軟體精靈 blit(含背景還原)≈ 16 列 × ~20 cycles | ~320 cycles/隻 |
| 22 隻精靈 | ~7,000 cycles |
| 影格內小更新(物品消失,≤20 格) | ~600 cycles |
| 音樂引擎(4 通道 AY,每影格) | ~800–1,500 cycles |
| 遊戲邏輯(32×20 地圖、8 敵 AI) | ~2,000–3,000 cycles |
| 輸入 + 雜項 | ~500 cycles |
| **合計** | **~11,000–12,500 cycles ≈ 65–73% 影格** |

→ **60fps 可行,但無餘裕**;實作上建議:
- 精靈用「還原背景 + 畫新精靈」的 dirty-rect 方式(不重繪整頁)。
- 地圖每關只繪一次(靜態背景),動畫圖元用雙圖元表每 16 影格重繪局部。
- 若超時,降為 30fps(每影格跑邏輯、影格交替繪圖),遊戲是逐格速度(`player_vx=4`)所以 30fps 只影響流暢度不影響平衡。

**必須接受的 4 項取捨**
1. **6 個固定色**:5 組關卡调色板全部塌縮成同一組 DHGR 色(黑/綠/紫/白 或 黑/橙/藍/白)。視覺風格改變最大的一項。
2. **無 16 階 fade**:以 dither 圖元做 4 級亮度近似,或直接用「黑頁覆蓋」做淡入淡出。
3. **DPCM 通道消失**:鼓聲/取樣要嘛丟掉,要嘛走 Apple II 內建 1-bit 喇叭(會與 AY 混音分離)。
4. **無硬體精靈**:全部自寫(這是工作量最大的一項,約 400–600 行 asm)。

**需要的自寫元件(3 個)**
| 元件 | 規模 | 可參考 |
|---|---|---|
| DHGR 顯示核心(解壓 RLE 畫面 + 圖元 blit + 雙頁切換) | ~300 行 asm | deater `graphics/dgr/animations/`(同 DOS 3.3/cc65 生態) |
| 軟體精靈引擎(8×16 blit + 背景還原 + 遮罩) | ~400 行 asm | 無現成,需自寫 |
| AY-8910 音樂引擎 + FTM→AY 轉換器 | ~400 行 asm + Python | deater `music/tiny_tracker`、`music/pt3_player`;StewBC `pt3plr`(cc65+ProDOS) |

### 4.2 路線 B:Apple II + VERA → **功能 1:1,管線現成**

NES→VERA 幾乎逐項對應:

| NES | VERA |
|---|---|
| nametable 32×32 tiles | Layer0/1 tilemap(現成 `VERA_LAYER0/1`) |
| CHR 8KB(2bpp) | VERA 4bpp/8bpp 圖元表(可直接放 16 色) |
| 64 硬體精靈(8×8) | **244 硬體精靈**(現成 `VERA_SPRITES_BASE`) |
| 32 位调色板 + fade | **256 色 12-bit RGB 调色板**(`VERA_COLOR_PALETTE`)→ fade 直接做 |
| APU 4 通道 + DPCM | **14 PSG 通道 + PCM 取樣** → FTM 5 通道全部保留,鼓聲走 PCM |
| NMI 影格同步 | VERA VSYNC IRQ(`VERA_IRQ_VSYNC`) |
| 捲動 `scroll()` | VERA `layer0.hscroll/vscroll` 硬體捲動 |

現成證據:`C:\dev\llvm-mos-sdk\mos-platform\apple2e\apple2e.h` 已是 cx16 相容的 VERA 介面;`TimePilot-IIvera` 已用同一套做出成品(ProDOS `.po`/`.hdv`)。

**代價**:需要 a2vera 實體卡;AppleWin 無法模擬 → 無法在一般模擬器上測試/分享。

### 4.3 建議

1. **主路線 = 路線 A(IIe DHGR + Mockingboard)**,因為可在 AppleWin 完整驗證、目標硬體普及。
2. **遊戲核心抽出成平台中立層**,讓 VERA backend 之後可以直接接上(路線 B 作為高畫質版,共用 90% 程式)。
3. 磁碟:**DOS 3.3 單片 140KB**(資產 27KB + 程式 ~30KB);若要 ProDOS 則沿用 TimePilot 的 Python 打包管線。

---

## 5. 建議架構

```
alter-ego/
  src/
    game.c            # 遊戲邏輯(平台中立,現有檔案改造)
    core.h            # 平台抽象層(取代 neslib.h 的 28 個函式)
    assets/           # 轉換後的 DHGR 圖元/畫面/音樂(由 tools/ 產生)
    dhgr/             # 路線 A:DHGR asm 核心 + 軟體精靈
    ay8910/           # 路線 A:Mockingboard 音樂引擎 + FTM 解碼
    input/            # 搖桿/鍵盤 → PAD_* 旗標
    tick/             # 60Hz 時序($C019 輪詢 或 VIA T1)
    dos33/            # DOS 3.3 載入/檔頭(ACME -f apple 或自寫)
    vera/             # 路線 B:VERA backend(接 llvm-mos apple2e)
  tools/
    chr2dhgr.py       # tileset.chr → DHGR 圖元(含 dither 亮度級)
    rle2dhgr.py       # nametable RLE → DHGR 畫面 RLE
    ftm2ay.py         # Famitone2 → AY-8910 事件表
    make_disk.py      # Cadius/AppleCommander 打包 DOS 3.3 影像
  build/
```

平台抽象層(直接對應現有呼叫,遊戲程式碼幾乎不用改):

```c
void gfx_init(void);
void gfx_load_screen(const unsigned char *rle);   /* unrle_vram */
void gfx_clear_screen(void);
void spr_clear(void);                              /* oam_clear   */
unsigned char spr_put(unsigned char x,unsigned char y,
                      const unsigned char *bmp8x16,
                      unsigned char flip);         /* oam_spr     */
void gfx_update(const unsigned char *buf,unsigned char len); /* set_vram_update */
void gfx_fade(unsigned char step);                 /* pal_fade(近似) */
void tick_wait(void);                              /* ppu_waitnmi */
unsigned char pad_poll(void), pad_trigger(void);
void mus_play(const void *data), mus_stop(void), mus_pause(unsigned char);
void sfx_play(unsigned char n,unsigned char ch);
unsigned char rnd(void); void setrand(unsigned char s);
```

---

## 6. 分階段計畫

| Phase | 交付物 | 驗證方式 |
|---|---|---|
| **0 工具鏈驗證** | `cl65 -t apple2enh` 出 BIN → Cadius/AppleCommander 打包 → AppleWin 跑起來 | 螢幕出現字串 |
| **1 資產轉換器** | `chr2dhgr.py`/`rle2dhgr.py` 產出 DHGR 圖元與 26 關畫面 | 產生 PNG 預覽比對 NES 版 |
| **2 DHGR 顯示核心** | 開 DHGR + 解壓畫面 + 雙頁切換 | AppleWin 截圖 26 關 |
| **3 軟體精靈引擎** | 8×16 blit + 背景還原 + 反轉 | 移動測試 + 週期計時(實測 cycles/frame) |
| **4 時序 + 輸入** | 60Hz tick + 搖桿/鍵盤 | 影格計數器 + 搖桿測試 |
| **5 Mockingboard 音樂** | `ftm2ay.py` + AY 引擎(4 通道 + noise + envelope) | AppleWin Mockingboard 啟用聆聽 |
| **6 遊戲接合** | game.c 接抽象層,單關可玩 → 26 關 | 通關測試 |
| **7 磁碟打包** | 單片 DOS 3.3 影像(`BRUN`) | 真機/AppleWin 開機即玩 |
| **8(備援)VERA backend** | 接 llvm-mos apple2e + TimePilot 打包管線 | a2vera 真機 |

**Phase 3 結束時做「go/no-go」**:若實測 cycles/frame > 17,050×0.85,則(a)降 30fps,或(b)改 HGR(280×192,6 色,繪圖成本減半),或(c)走路線 B(VERA)。

---

## 7. 風險清單

| 風險 | 影響 | 對策 |
|---|---|---|
| 軟體精靈週期超預算 | 掉 fps | Phase 3 實測;dirty-rect;30fps 降階 |
| 6 色固定 → 視覺差異大 | 賣相 | 用 dither 圖元做亮度級;精靈用第二組调色板 |
| DOS 3.3 無 cc65 檔案 I/O | 無法載入資產 | 資產直接編進 BIN(27KB 可容納),或改 ProDOS |
| Mockingboard 位址/偵測依板子而異 | 真機無聲 | 同時支援 VIA 版($C400/$C480)與 clone($C600/$C610),開機偵測 |
| 影格同步需 ROM 寫入權(IRQ 方案) | 相容性 | 主用 `$C019` 輪詢(不需 ROM 權限) |
| FTM 的 triangle 音色無對應 | 音樂變味 | AY 用 50% duty + envelope 近似;必要時重編曲 |

---

## 8. 本輪實作成果(已落地並可建置)

### 9.1 Phase 0 工具鏈 — **已通過**

```
cl65 -t apple2enh -Os -C src/a2/a2.cfg -o build/a2/ae2 \
     build/dhgr_lines.s src/a2/dhgr.s src/a2/demo.c build/dhgr_tiles.s build/dhgr_screen0.s
```
→ `build/a2/ae2` = **15,221 bytes**,AppleSingle magic `00 05 16 00`,2 個 entry,data fork load address **$0803**,filetype `$06`(BIN)。
實測注意:`apple2enh.cfg` 的 ZP 只有 `$1A` bytes,DHGR 引擎需要 7 個零頁指標 → 自建 [src/a2/a2.cfg](../src/a2/a2.cfg) 把 ZP 放大到 `$40`(否則 `ld65` 出現 `Segment 'ZEROPAGE' overflows memory area 'ZP'`)。
零頁限制:`(zp),y` 的指標**必須**在 $00-$FF,放進 BSS 會報 `Range error (Address size 2 does not match fragment size 1)`。

### 9.2 資產管線 — **已驗證**

[tools/a2_assets.py](../tools/a2_assets.py):
- **RLE 解碼器逐字對應 [_unrle_vram](../src/neslib.s#L334-L372)**,26 關全部解出 **恰好 1024 bytes** nametable(實測輸出)。
  關鍵陷阱:neslib.s:351 的 `bne @1` 前面是 `sta`,**`sta` 不影響旗標**,所以該分支恆真 → 字面值(含 `$00`)永遠不會落入重複分支;終止條件只有「TAG 後接 $00」。第一版照直覺實作會在中途提前結束(解出 34~920 bytes 不等)。
- CHR → DHGR:512 張圖元 × 16 bytes = 8,192 B,輸出 [build/dhgr_tiles.s](../build/dhgr_tiles.s)。
- 地圖 → DHGR 畫面:遊戲區 32×20 格 = 256×160 px,對應 nametable 第 6-25 列(`SCREEN_START_Y 48`)。DHGR 只有 192 條 scanline,所以**重映射到第 0-159 列**,160-191 留給 HUD。
- 每關 RLE 後 1,473–5,867 bytes(平均 3,364);26 關合計 87,466 bytes → 走磁片逐關載入,不全部內嵌。
- 預覽圖 [build/level0_dhgr.png](level0_dhgr.png) 可辨識出關卡結構(平台/牆/梯子)。

### 9.3 DHGR 引擎 — 已建立,佈局待真機確認

[src/a2/dhgr.s](../src/a2/dhgr.s):`dhgr_init`(soft switch 序列)、`dhgr_clear`($4000-$7FFF 填黑)、`dhgr_set_tiles`、`dhgr_set_row`、`dhgr_put8`(8×8 圖元 blit)、`dhgr_draw_screen`(RLE 解壓直接寫顯存,每 80 bytes 換下一條線)。

**scanline→位址被抽成一張產生出來的表格**([tools/dhgr_layout.py](../tools/dhgr_layout.py) → `build/dhgr_lines.s`),引擎本身與佈局無關;換佈局只改一個產生腳本的 `--model`。

### 9.4 本輪查證到的 DHGR 幾何(附證據)

| 事實 | 證據 |
|---|---|
| 一個 DHGR page = **16 KB** | ProDOS /RAM 把第一頁 DHGR 存於 `0x012000-0x013FFF`(16 KB),第二頁 `0x014000-0x015FFF` — https://en.wikipedia.org/w/index.php?title=Apple_II_graphics&action=raw&section=14 |
| 640×192、2 bpp → **160 bytes/scanline**、全圖 30,720 B | 640×192×2 = 30,720 |
| 一條線的 bytes **交錯於兩個 64KB bank** | 「each byte of pixels alternated between the first and second bank of 64KB memory」同上 |
| 存在 **64:1 interleaving** | 同上(「In addition to the 64:1 interleaving…」) |
| 主/aux 寫入要 `sei`+`sta WRAUX($C005)` … `sta WRMAIN($C004)`+`cli` | deater `graphics/dgr/animations/patch_graphics.s` 逐字(見 9.5) |
| 現成 DHGR 工具把**位址預先算好塞進資料流**(不是公式) | 同上:寫入位址是 self-modifying code,由資料流裡的 16-bit 增量累加(`adc patch_*_smc+1/+2`),寫入長度也是資料流決定(`cpx #5` 被 patch 成實際長度) |

**仍未定案(必須在 AppleWin/真機確認的一項)**:一條線 160 bytes 在 main/aux 兩 bank 的**交錯粒度**(4-byte 群交錯?每線 80+80 半段?),以及 scanline 的 64:1 交錯確切表格。
本輪用 cc65 附的 `.dhgr`/`.hgr` 範例檔做實證(線性、多種交錯家族、位移自相關)全部失敗,且 cc65 自己標註 `samples/apple2/dhgrshow.c`「**is not actually functional**」([samples/readme.txt](C:\dev\cc65\samples\readme.txt))→ 該批範例檔**不能**當實證依據。故引擎採表格化設計,把此項隔離。

**下一條要試的線索**:cc65 盤點報告把 DHGR 缺口寫成「DHGR 位址交錯表(**16 段 × 40 位址**)」且稱 DHGR 為 **560×192**、需 **$2000-$3FFF 雙 bank 切換**。16 段 × 40 位址 = 640 個位址,與「一條線 160 bytes、每 4 bytes 切換 bank(160/4 = 40 段/線 × 16 條線)」的結構吻合 → 優先驗證假設:**每條線以 4-byte 為單位在 main/aux 間交錯,交錯表以 16 條線為一段**。

### 9.8 DOS 3.3 打包器 — **已完成並雙重驗證**

[tools/dos33_pack.py](../tools/dos33_pack.py)(僅標準函式庫)。查證方式:**原始碼 + 真實 DOS 3.3 磁片逐位元組比對**(非憑記憶)。

| 事實 | 內容 | 證據 |
|---|---|---|
| VTOC | **T17,S0** | `dos33.h`:`VTOC_TRACK 0x11` / `VTOC_SECTOR 0x00`;真實 `empty.dsk` T17S0 逐位元組吻合 |
| VTOC 欄位 | `0x01` = catalog track、`0x02` = catalog sector、`0x03` = DOS 版本、`0x06` = volume、`0x27` = maxTS(122)、`0x34` = tracks、`0x35` = sectors/track、`0x38` = 空閒位圖 | `dos33.h` 逐字 + 實盤 `00 11 0F 03 00 00 FE 00 … 7A … 1B 01 00 00 23 10 00 01` |
| ⚠ 常見文件錯誤 | 文件常寫「$00 = next-VTOC track、$01 = next-VTOC sector、$02 = catalog track」→ **實盤 $01 就是 catalog track(17)、$02 是 catalog sector(15)** | 實盤逐位元組 |
| 空閒位圖 | 在 **VTOC 內偏移 $38**,每 track 4 bytes(byte+0 = sector 8-15,byte+1 = sector 0-7);**bit=1 表示空閒** | `dos33_vtoc_bitmap.c` 逐字 `/* 1 indicates free, 0 indicates used */`;實盤 T17 bitmap `0F FE` 正好把 VTOC 與 catalog 鏈標為已用 |
| Catalog | **起於 T17,S15,往回走 S14→S13→…**(不是 T18,S1-S3);**每 sector 7 個檔目**,檔目 **35 bytes**,由 byte 11 開始 | `dos33.h`:`CATALOG_FILE_LIST 0x0b`、`CATALOG_ENTRY_SIZE 0x23`;`dos33_catalog.c`:`while(i<7)` |
| 檔目欄位 | `+0` = TSL start track(**$FF=已刪、$00=空 slot**,兼 in-use 旗標)、`+1` = TSL start sector、`+2` = file type、`+3..32` = 檔名 **30 bytes 高 ASCII、空格補齊、無長度欄**、`+33/+34` = 用過的 sector 數(LE) | `dos33.h`:`FILE_TS_LIST_T 0x0`/`FILE_TS_LIST_S 0x1`/`FILE_TYPE 0x2`/`FILE_NAME 0x3`/`FILE_SIZE_L 0x21`/`FILE_SIZE_H 0x22`/`FILE_NAME_SIZE 0x1e` |
| file type | 位元旗標:T=0x00 I=0x01 A=0x02 **B=0x04** S=0x08 R=0x10 N=0x20 L=0x40,鎖定 `\|0x80` → **BIN = $04** | `dos33_char_to_type` 逐字 |
| TSL 鏈 | 由 byte 12 開始,每筆 (track,sector) 2 bytes,最多 122 筆,next=(0,0) 結尾;byte5/6 = 該清單對應的檔案 sector 偏移 | `dos33.h`:`TSL_NEXT_TRACK 0x1`/`TSL_NEXT_SECTOR 0x2`/`TSL_OFFSET_L 0x5`/`TSL_OFFSET_H 0x6`/`TSL_LIST 0xC`/`TSL_ENTRY_SIZE 0x2`/`TSL_MAX_NUMBER 122` |
| BIN 資料格式 | 每檔開頭 **4 bytes = `load_lo, load_hi, len_lo, len_hi`**,其後為資料 | `make_b.c` 逐字 + 實盤 HELLO 資料 sector 開頭 `57 00 07 08` |
| sector 順序 | `.do`(AppleWin DOS 順序)= **身份映射** `off=(track*16+sector)*256`;`.po`(ProDOS 順序)= 4:3 交錯 `map={0,7,14,6,13,5,12,4,11,3,10,2,9,1,8,15}` | `DISK_OFFSET` 巨集逐字 + 實盤證明 empty.dsk 是 .do;`dos33_raw.c` 的 `dos33_sector_map` 逐字 |
| cc65 AppleSingle | magic `00 05 16 00`,版本 `00 02`,**entry 數在偏移 24**,每筆 12 bytes 大端由偏移 26 開始;header 總長 **58**;**load address = header 偏移 56 的 2 bytes BE**(ProDOS auxiliary type),filetype 在偏移 54 | `libsrc/apple2/exehdr.s` 逐字;ae2 實測 data fork 15,163 B @58(58+15163 = 15,221 = 檔大小 ✓)、load `$0803`、type `$0006` |

**實測(本輪重跑,兩種順序皆通過)**:
```
AE2   AppleSingle data fork 15163 bytes, load $0803, ProDOS type $0006
added AE2   61 sectors (60 data + header)
wrote build/a2/ae2.dsk  143360 bytes  .do/DOS order
  OK  AE2  type $04  61 sectors  TSL T18/S0  cat T17/S15  15360 bytes (193 pad)
verify: 467 free sectors (119552 bytes)
verify: 77 sectors referenced by catalog/TSL/data, all marked used: yes
VERIFY PASS        (.do 與 --po 皆通過)
```
盤上首個資料 sector = `03 08 3B 3B a2 ff 9a 20 …` → load `$0803`、len 15,163、接著就是程式碼 ✓
同一解析器讀**真實** `empty.dsk` 得到 `HELLO type $02 used=2 TSL T18/S15 head 57 00 07 08` ✓ → 解析器對真實 DOS 3.3 磁片有效。

**使用限制**:影像內不含 DOS,需在 AppleWin 用 DOS 3.3 開機磁片開機,把 `ae2.dsk` 掛 D1,然後 `BRUN AE2`。

**容量**:單檔 61 sectors;整片 143,360 B,扣掉 DOS 佔用後可用約 119 KB → 全部資產(27,138 B)+ 程式一次放得下。

以 `C:\dev\cc65\samples\apple2\superman.dhgr`(16,384 B)與 `werner.hgr`(8,184 B)為輸入,以下全部渲染成雜訊:

| # | 假設 | 結果 |
|---|---|---|
| 1 | DHGR 線性:80 B/線(main)+ aux 鏡像於 +$2000 | 雜訊(預覽 `tools/dhgr_h1.png`) |
| 2 | 64:1 縮放家族 `5120*(y//64)+640*((y//8)%8)+80*(y%8)` | 雜訊(`tools/dhgr_h2.png`) |
| 3 | 40 B/線 + 經典 HGR 交錯 `1024/40/128` | 雜訊 |
| 4 | 40 B main @ `H(y)` + 40 B aux @ `0x2000+H(y)`(= 560×192 模型) | 雜訊(`tools/dhgr_560.png`) |
| 5 | 位移自相關掃 lag 8..600 | `.hgr` 最佳 lag **128/256**;`.dhgr` 最佳 lag **128** → 皆由畫面內容(`11 44` 交錯底紋,週期 2)造成,**不是佈局訊號** |
| 6 | 逐線 stride 掃描(128 最佳)/ 3 層交錯家族窮舉 / 空洞測試 | 無有效佈局;stride-128 的訊號來自 `$7F` 背景佔 74% 的假象 |

`werner.hgr` 位元組統計:`$7F` 6,102/8,184(74%)、MSB 設定率 0.006、前 52 bytes 全 `$7F`。
→ **判定:cc65 附的 `.hgr`/`.dhgr` 範例檔不是可推導的 framebuffer dump**(cc65 自己標註 dhgrshow 不可用),佈局只能靠 AppleWin/真機 + 文件化表格定案。

### 9.5 本輪抓到的 Mockingboard 事實(附證據)

`Michaelangel007/apple2_mockingboard/test_mock.s` 逐字:原版 Mockingboard 是 **2× SY6522 VIA + 2× AY-8910**,透過 VIA port A(暫存器號/資料)+ port B(strobe)操作:
```
ADDR6522   = $C400   ; *** Default Mockingboard to slot 4 ***
MOCK1_OR_B = $C400 / MOCK1_OR_A = $C401 / MOCK2_OR_B = $C480 / MOCK2_OR_A = $C481
_6522_LATCH=$7  _6522_WRITE=$6  _6522_PORT_B=$4
MOCK1_PokeXY: stx MOCK1_OR_A / jsr MOCK1_SetReg / sty MOCK1_OR_A / jmp MOCK1_SetData
MOCK1_SetReg: lda #_6522_LATCH ; MOCK1_SetData: lda #_6522_WRITE / sta MOCK1_OR_B / lda #_6522_PORT_B / sta MOCK1_OR_B
MOCK_TONE_LOW=$0(Reg 0/2/4,lo 8-bit) MOCK_TONE_HIGH=$1(Reg 1/3/5,hi 4-bit)
MOCK_NOISE=$6(5-bit) MOCK_CHANNELS=$7(6-bit mask) MOCK_AMPLITUDE=$8(Reg 8/9/A,5-bit)
MOCK_ENV_LOW=$B MOCK_ENV_HIGH=$C MOCK_ENV_TYPE=$D(4-bit)
demo_note_1: .byte $0F,$0F,$0F   ; Amp A,B,C → 音量 16 級
```
→ 每顆 AY = 3 音道(12-bit)+ 1 noise(5-bit)+ 1 envelope;Mockingboard 共 **6 音道 + 2 noise**。
**未定案**:`MOCKINGBOARD` 字串偵測位址、以及無 VIA 的 clone(Echo/Mockingboard Clone,$C600/$C610 直接 I/O)的確切位址與寫入順序。實作時**兩種都要支援並開機偵測**。

### 9.6 本地環境盤點(影響打包方式)

| 工具 | 本地狀態 |
|---|---|
| cc65 V2.19(`C:\dev\cc65`) | ✅ 可用,已實測產檔 |
| llvm-mos SDK(`C:\dev\llvm-mos-sdk`) | ✅ 可用(`mos-apple2e`,VERA 導向) |
| AppleWin | ❌ 無 → 圖形/音效**無法本地目視驗證** |
| Java / AppleCommander(ac.jar) | ❌ 無 |
| Cadius / ACME | ❌ 無 |
| `C:\dev\a2vera\a2vera\a2vera_dos33.dsk` | 143,360 B,但**不是標準 DOS 3.3 扇區影像**:以 raw / .po→.do / .do→.po 三種映射掃遍全圖都找不到 VTOC 特徵;T17S0 = `04 11 0f 03 00 00 01 00 00 …`,尾段有 ASCII(`…KIPPING.\r\0DONE. BRUN AN INIT TO`)→ 符合 **master-index(shasht)** 發行格式,需 Cadius 轉換 |

→ 結論:本地**沒有現成打包工具**,故自寫 `tools/dos33_pack.py`(標準 DOS 3.3 影像 + `--verify` 自我解析比對)。

---

## 10. Phase 3 週期預算 — **go/no-go 判定(算出來的,待 AppleWin 實測確認)**

### 10.1 每幀要畫幾隻精靈(實測自原始碼,不是猜)

[game.c:84-92](../src/game.c#L84-L92):`ENEMY_MAX = 8`、`PART_MAX = 4`、OAM 分區 `OAM_ENEMY 0` / `OAM_PAUSE (ENEMY_MAX<<1)` / `OAM_PARTS (52-PART_MAX)` / `OAM_STATS 52` / `OAM_PLAYER 60`。
繪製迴圈 [game.c:895](../src/game.c#L895)、[1400](../src/game.c#L1400)、[1445](../src/game.c#L1445):`for(i=0;i<enemy_cnt;i++)`。
→ 每幀 = **8 隻敵人 + 4 個粒子 + 主角 + HUD**,換算成 8×16 槽 ≈ **9 隻**(我先前用 22 是高估,22 是 OAM 陣列大小不是每幀繪製數)。

### 10.2 引擎實作的逐指令週期(已組譯,`src/a2/spr.s`)

每條 scanline(8×16 精靈 = 2 bytes/線,DHGR 線距 80 bytes):

| 步驟 | cycles |
|---|---|
| 讀 mask(`ldy#0`/`lda (spr_src),y`/`sta spr_m`/`iny`) | 12 |
| byte0:存背景 + 依 mask 寫(`lda (spr_ptr),y`/`sta (buf_ptr),y`/`lsr`/`bcc`/`lda (spr_src),y`/`sta (spr_ptr),y`) | 29 |
| `iny` | 2 |
| byte1:同上 | 29 |
| **三個指標各自前進**(screen +80、stash +2、sprite +3,各 `clc/lda/adc/sta/bcc`) | 36 |
| `dex`/`bne` | 5 |
| **每線合計** | **≈118** |

| 動作 | 每精靈 cycles |
|---|---|
| `spr_save_draw`(16 線) | 1,888 |
| `spr_restore`(16 線,每線 ≈53) | 848 |
| `spr_setup` + `spr_set_slot` ×2 | ≈90 |
| **每隻 8×16 精靈每幀** | **≈2,826** |

### 10.3 判定(預算 = 1.023 MHz ÷ 60 Hz = **17,050 cycles/幀**)

| 每幀精靈數 | cycles | 佔預算 | 判定 |
|---|---|---|---|
| 9(遊戲實際最大值) | 25,434 | **149%** | ❌ **超出** |
| 6 | 16,956 | 99% | ❌ 無空間給音樂/邏輯 |
| 4 | 11,304 | 66% | ⚠ 剩 5,746 給音樂+邏輯+輸入,**很緊** |

→ **DHGR + 軟體精靈在 60fps 下不可行**(以現行引擎)。這是 Phase 3 的 no-go 訊號。

### 10.4 三條出路(已算過)

| 方案 | 每精靈 cycles | 9 隻合計 | 佔預算 | 備註 |
|---|---|---|---|---|
| **A. 遊戲畫面改 HGR(280×192)** | ≈1,300(1 byte/線,工作量減半) | 11,700 | **69%** ✅ | 留 5,350 給音樂+邏輯;**DHGR 保留給標題/過場** |
| B. DHGR 降 30fps | 2,826 | 25,434 | 每 2 幀 149%→75% | 手感下降,音樂仍 60Hz |
| C. 走路線 B(II + VERA) | 硬體精靈 244 隻,0 cycles | — | ~0% ✅ | 需實體卡,AppleWin 驗不了 |

已試過並**確認無效**的省法:把 save 與 draw 合併成單趟(已實作,省掉一趟 16 線 traversal,但每線 3 個指標前進的 36 cycles 是主成本,合併只省約 12%)。
預先算好 16 條線位址表可把每線 36 → 11 cycles(每精靈 ≈2,052),9 隻 = 18,468 仍 **108%**,救不起來。

### 10.5 建議

**遊戲主畫面走 HGR(280×192,6 色),DHGR 只用於標題/過場/結算。**
理由:HGR 每線 1 byte → 精靈工作量減半,9 隻精靈落在 69% 預算,音樂與邏輯才有空間;而遊戲區原始解析度是 256×160(`MAP_WDT 32 × TILE_SIZE 8`),**HGR 的 280×192 本來就蓋得下**,DHGR 的 640 寬對本遊戲沒有必要(它主要多的是寬度,不是遊戲需要的解析度)。
代價:精靈可用色從 DHGR 的 6 色變成 HGR 的 6 色(相同),解析度 280×192 vs 640×192(標題畫面失去)。

---

## 11. 查證狀態總表

| 項目 | 狀態 |
|---|---|
| 遊戲規格、資產體積、RLE 格式 | ✅ 已驗證(實測) |
| cc65 Apple II 能力矩陣(TGI 無 DHGR、無 Mockingboard、AppleSingle @$803、DOS 3.3 無 disk I/O/interruptor) | ✅ 已驗證(本地盤點 + 官方文件) |
| 工具鏈可產出可執行檔 | ✅ 已驗證(15,221 B AppleSingle) |
| AY-8910 暫存器/音量/音調、Mockingboard VIA 控制序列 | ✅ 已驗證(逐字引用) |
| DHGR = 16KB/頁、160 B/線、雙 bank 交錯、64:1 交錯存在 | ✅ 已驗證(文件) |
| **DHGR scanline 交錯表格 + main/aux 交錯粒度** | ⚠ **未定案**,已隔離成表格,需 AppleWin/真機確認 |
| **Mockingboard 位址偵測(VIA 版 vs clone 版)** | ⚠ 未定案,實作需雙支援 |
| DOS 3.3 影像寫入格式(VTOC/bitmap/catalog/TSL/BIN header/.do-.po) | ✅ **已驗證**(原始碼 + 真實磁片逐位元組;打包器 `--verify` 通過) |
| 60fps 軟體精靈週期預算 | ⚠ 估算,需實測 |

---

## 12. 參考來源

- cc65 Apple II 官方文件:https://cc65.github.io/doc/apple2.html(TGI 驅動清單、§8.1 DOS 3.3 限制、AppleSingle/AppleCommander)
- 本地:`C:\dev\cc65\asminc\apple2.inc`(soft switch)、`C:\dev\cc65\lib\apple2enh.lib`
- 本地:`C:\dev\llvm-mos-sdk\mos-platform\apple2e\{apple2e.h,link.ld}`(VERA 介面、ProDOS BIN @ $2000)
- 本地:`C:\dev\Time-Pilot\TimePilot-IIvera\AGENTS.md`(llvm-mos + VERA + ProDOS 打包、DOS 3.3/ProDOS BIN header 4 bytes 陷阱)
- 本地:`C:\dev\a2vera\README.md`(VERA 卡、ACME `-f apple`、`a2vera_dos33.dsk`)
- deater(Dos33Filesystem)cc65/Apple II 範例集:https://github.com/deater/dos33fsprogs(`graphics/dgr/animations/`、`music/tiny_tracker`、`music/pt3_player`)
- PT3 音樂播放器 Apple II/Mockingboard + ProDOS(cc65):https://github.com/StewBC/pt3plr(用 **Cadius** 打包)
- Mockingboard 6522/AY 程式範例:https://github.com/Michaelangel007/apple2_mockingboard(`test_mock.s`、`freq.c` 音調表)
- Apple II graphics 概覽:https://en.wikipedia.org/wiki/Apple_II_graphics
- Famitone2(音樂格式來源):http://shiru.untergrund.net/articles/programming_nes_games_in_c.htm


---

## 13. 外部參考 `C:\dev\pom2games`(本輪新增,重大)

使用者指點:`C:\dev\pom2games` 內有成熟的 Apple II 開發套件(VERHILLE Arnaud,GPL-3.0)。
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

**重要推論(已落地):DHGR 位址表與 HGR 位址表是同一張。**
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
| `dev/tools/a2run` | **無視窗 Apple II 模擬器**(C99,6502 NMOS 過 Klaus Dormann 測試),腳本 `wait:/key:/shot:PNG/peek:/poke:/text:/spk/dsk:` | 本機無 C 編譯器;`C:\dev\llvm-mos-sdk\install\bin\clang.exe` 可用,zlib 僅供 PNG IDAT → 改 stored-deflate 即可,**建置中** |
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

### 13.9 管線現況(本輪)

`build\a2\build.bat` 已重寫並**全綠通過**,順序:

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


## 14. II+ 無頭驗證鏈落地(a2run)— 七個根因一次收干净

本節是 Phase 0/3 在 `tools\a2run`(Apple II+ NMOS 6502 核心)上跑出來的結果。
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

`build\a2\build.bat` 新增 **4b) II+ 驗證段**:`-t none` + kit `crt0_apple2.s`(排第一)
+ kit `apple2_hgr_c.cfg` + `rawbin.py ... 0x6000`,產物 `HGRDEMO6` 一併打包進
`ae2_boot.dsk`。管線全綠,實測:

```
a2run --disk build2e2_boot.dsk key:"HELLO" wait:1500 pc peek:400:2
  PC=6212  0400: 38      ; '8' = 已進入精靈迴圈
```

截圖 `build\a2\demo7.png`(560×384、6 色、約 108,200 個非黑點、24 個 16 列帶皆有墨)
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

## 15. 逐關串流（使用者指定：//e 128K，過關才載下一關）與 DOS 3.3 指令執行路徑

### 15.1 設計（已定案）

使用者指定：以 Apple //e 128K 為目標，**過關才從磁碟載入下一關**，不要把 26 關全塞進
binary。對應的記憶體配置在 `src/a2/a2_128.cfg`：

| 主記憶體 | 用途 |
|---|---|
| `$1000-$1FFF` | **關卡暫存區（LOWBSS）＝ BLOAD 目標**，4 KB |
| `$2000-$3FFF` | HGR page 1 |
| `$4000-$5FFF` | HGR page 2 |
| `$6000-$95FF` | binary + BSS + stack（13,824 B） |
| `$9600-$BFFF` | DOS 3.3 |
| `$D400-$DFFF` | language card（3 KB） |

輔助記憶體 `$6000-$BFFF` = **24 KB 全空**，留給 DHGR 過場圖。
HGR 每關 payload ≈ **1,960 B**，放得進 4 KB 暫存區；26 關 RLE 總計 84,108 B，
DOS 3.3 磁片可用約 140 KB → 84 KB 圖檔 + 約 15 KB 程式，容量成立。
kit 的 micro-sokoban 就是這個模式的現成先例（454 關以 `BLOAD <name>,A$1000` 逐包載入）。

### 15.2 DOS 3.3 指令執行：實測結論（重要）

以 `src/a2/bloadtest.s`（純組語，可在 a2run 的 II+ 核心跑）逐步插樁，逐段定位：

| 步驟 | 結果 |
|---|---|
| `_main` 進入 | ✅ 抵達（`until` 命中，PC 確認） |
| COUT 輸出字串 | ✅ `ZZPROBE` 出現在螢幕 |
| `jsr $03EA`（DOS_HOOKS） | ✅ 有返回（`$03EA: 4C 51 A8` = `JMP $A851`） |
| 經 `$FDED` 發射 Ctrl-D 指令行 | ❌ DOS 完全沒看到 |
| **經 CSW 向量 `$0372` 發射** | ✅ **DOS 收到（螢幕出現 `*`，PC 停在 DOS 內）** |
| 指令本體被執行 | ❌ 未執行（`$1000` 仍是 power-on 圖樣） |

**根因（全部實測，非推測）：**

1. `cc65` 的 `asminc/apple2.inc` **沒有定義 `COUT`**；kit 的 `dev/lib/apple2/apple2.inc`
   定義 `COUT = $FDED`。
2. 實測 ROM：II+ 與 //e 的 `$FDED` 都是 `6C 36 00` = **`JMP ($0036)`，即 KSW**，
   而 KSW 指向 `$FDF0`（純 Monitor 輸出）。**`$FDED` 走的是 KSW，不是 CSW。**
3. 開機後 DOS 3.3 把 **CSW（`$0372/$0373`）hook 到 `$04FF`**，KSW 維持 `$FDF0`。
   → 用 `$FDED` 發射會**完全繞過 DOS 的攔截點**。
4. 改成 `csw_out: jmp ($0372)`（`jsr` 到此 stub，被呼叫端的 RTS 會回到 jsr 之後）後，
   **DOS 立刻攔截到 Ctrl-D**（螢幕 `*` = DOS 的 Ctrl-D 標記）。
5. 對照實驗：**kit 自己的 `dev/lib/apple2c/apple2dos_asm.s` + `dos.asm`（已上線遊戲在用）
   在 a2run 裡行為與我的 clean-room 版完全一致**（無 `*`、指令未執行）。
   → 我的實作與 kit 一致，**剩下的差距是環境，不是程式**。

**判定：** DOS 3.3 攔截 Ctrl-D 後接管，指令字元要由 **KSW（鍵盤）**路徑餵入；
kit 的協定是 //e 導向，而 **a2run 只有 II+ 核心**（無 //e firmware、aux RAM、
language card、80 欄、DHGR、6522 VIA），**無法跑完這條路徑**。
因此 `jmp ($0372)` 是比 `$FDED` 更穩的發射點（II+ 與 //e 上 `$0372` 都是 CSW），
**指令行的最終驗證必須在 AppleWin（真 //e）上做**。

### 15.3 插樁的兩個坑（記下來，避免重蹈）

1. **標記寫在文字頁 `$0400` 會被 DOS 回家時清掉** → 標記要放 BSS，用 `peek` 讀。
2. **BSS 標記位址必須從最終 map 算**：`dosload.s` 的 BSS（`CMD_MAX`+ix+256）排在
   `bloadtest.s` 前面，會把標記往後推。`tools/run_bloadtest.ps1` 已改成自動從 map 的
   `__BSS_RUN__` 推算，不要再用手算位址。
3. **16 位元 checksum 不能證明載入成功**：a2run 的 power-on RAM 圖樣
   `ram[k] = (k&2) ? 0xFF : 0x00`，在 2,048 位元組上的總和是 261,120，
   與測試 payload 的總和**完全相同**。要驗收就必須看 **首字节**（`stage[0] == 7`）。

### 15.4 目前狀態 / 下一步

- `src/a2/dosload.s`：clean-room 版，發射點已改為 CSW 向量，zero-page 整頁交換依 kit
  協定補上（`apple2_zp_buf` 由 kit `crt0_apple2.s` 在開機時快照）。
- `src/a2/bloadtest.s` + `tools/mk_payload.py` + `tools/run_bloadtest.ps1`：可重跑的
  串流測試（自動從 map 定位標記）。
- 逐關串流的**容量與記憶體配置已成立**；**指令執行路徑需在 AppleWin（//e）驗證**。
- 下一步：把 26 關輸出成 26 個 `.bin`（`tools/a2_assets.py`），過關時
  `a2_dos_cmd("BLOAD LVnn,A$1000")`；DHGR 過場圖走 aux `$6000-$BFFF`。

### 15.5 逐關 payload 實測（26 關全部放得進 4 KB 暫存區）

`tools/a2_assets.py` 新增逐關 HGR payload 產出（`build/lv/lv00.bin` … `lv25.bin`，
每檔就是 RLE 畫面串流，與 NES 端 `_unrle_vram` 同格式）：

| 項目 | 值 |
|---|---|
| 關卡數 | 26 |
| 最小 / 最大 / 平均 | **976 / 3,437 / 2,015 B** |
| 總計 | **52,402 B** |
| 暫存區上限 | 4,096 B（`$1000-$1FFF`） |

工具內建檢查：**任何一關超過 4 KB 就 `SystemExit`**（目前最大 3,437 B，安全邊界 659 B）。
容量結論：52 KB 圖檔 + 約 15 KB 程式 ≪ DOS 3.3 磁片可用 ~140 KB → **使用者的
「過關才載下一關」設計在容量與記憶體兩面都成立**。

### 15.6 暫存區契約的實測：打包 ≠ 載入（關鍵）

`src/a2/lvdraw.s`（純組語）：`hgr_init` → `hgr_draw_screen($1000)` → 停在迴圈，
標記寫在**固定位址 `$1FF0`**（在暫存頁尾、最大 payload 只到 `$1D6D`，永遠是空的；
文字頁 `$0400` 的標記會被 DOS 回家時清掉，BSS 位址從 map 推算又太脆）。

實測：

```
PC=62BD A=04 X=00 Y=00 S=FD P=25
1000: 00 00 FF FF 00 00 FF FF
1FF0: 04
```

- `1FF0 = $04` = 標記 `'4'` → **`hgr_init` 與 `hgr_draw_screen` 都跑完了**，
  解碼器在垃圾資料上也能自行收尾、不會卡死（穩健性通過）。
- `1000:` 是 **power-on RAM 圖樣**，不是 payload。

**教訓（寫下來，這是最容易誤判的一點）：**
`dos33.py --bin "LV00=lv00.bin@0x1000"` 只是把檔案**存在磁片上並記錄其載入位址**，
**不會把位元組放進 RAM**。要讓 `$1000` 真的有資料，必須**由程式自己去載入**
（`BLOAD` 或直接 RWTS）。所以「打包成功」跟「載入成功」是兩件事，
**驗收一定要 peek `$1000` 的實際位元組**。

### 15.7 載入路徑的取捨（決定：走 RWTS）

| 方案 | 狀態 |
|---|---|
| DOS 指令行（Ctrl-D + `BLOAD`） | 發射點已修正到 CSW 向量 `$0372`，DOS 會收到（`*`），但**指令本體在 a2run 的 II+ 環境跑不完**（DOS 接管後由 KSW 讀指令） |
| ROM 的 DOS 3.3 ML 介面（`$FB00 INIT` / `$FB11 LOAD` / `$FB49`） | **實查 ROM 後否決**：`$FB00` 開頭是 `CPX #$45`（是程式碼），但 `$FB11: C4 C2 C1 FF C3 FF FF FF C1 D8`、`$FB29`、`$FB49: A9 14 85 22 …` 看起來是**資料/master-catalog 記錄**，不是可直接 `JSR` 的入口。**不猜** |
| **DOS 3.3 RWTS 直接讀磁區** | **採用**。`JSR $03E3` 已在環境實測存在（`AD C2 AA`），`JSR $03D9` 為 RWTS 後收尾。kit 的 `micro-sokoban/src/fast_disk.inc` 就是這條路（454 關），協定完整可讀 |

RWTS 協定（自 kit 參考實作整理，非抄寫）：
1. 存下 DOS 的 `$0000-$004F`（RWTS 會借用 zero page）。
2. `JSR $03E3` 取得 DOS 自己的 **IOB** 位址（A/Y 回傳）。
3. 填 IOB：`+2`=drive(1)、`+3`=slot(0)、`+4`=track、`+5`=sector、`+9`=page、`+12`=命令字元。
4. 再 `JSR $03E3` 執行傳輸，`JSR $03D9` 收尾。
5. 還原 zero page（保留 carry 當成功旗標）。
6. 檔案定位：掃 **catalog（track 17 = `$11`）** 找 15 字元檔名 → 沿 **T/S 鏈**逐磁區讀進 `$1000`。

**採用 RWTS 的理由**：它**完全繞過指令攔截**，是 kit 上線遊戲在用的同一條路，
而且在 a2run 裡**可完整驗證**（不像指令路徑）。實作進行中（`src/a2/lvload.s`）。

## 16. Phase 6 工作清單：neslib 抽象層的確切符號清單（實測取得）

以最小固定位址 config（`build/a2/probe.cfg`）連結 `build/a2/game.o`，
`ld65` 報出 **69 個未解析符號**。分兩類：

### 16.1 由 cc65 標準函式庫自動提供（**不用實作**）

`__STARTUP__`、`_memcpy`、`c_sp`、`ptr1`、`sreg`、
`pusha`、`pusha0`、`pushax`、`push0`、`pushw`、
`incaxy`、`decaxy`、`incax2`、`incax4`、`decax1`、`decax4`、
`aslax1`、`asrax3`、`shlax1`、`shlax4`、`ldax0sp`、`ldaxi`、`incsp1`、`incsp2`、
`tosicmp`、`tosdiva0`、`tosudiva0`、`tosumoda0`、`tossuba0`

→ 這些在 //e 正式連結（`-t apple2enh` + cc65 函式庫）時自動解析。
**注意：`-t none` 沒有 C 函式庫，所以 a2run 的 II+ 驗證版只能寫純組語。**

### 16.2 需要實作的 neslib API（**28 個**，Phase 6 的範圍）

| 群 | 符號 | 呼叫次數 |
|---|---|---|
| VRAM | `_vram_adr` `_vram_put` `_vram_fill` `_vram_inc` `_vram_read` | 9 / 21 / 4 / 3 / 2 |
| 精靈表 | `_oam_clear` `_oam_spr` `_oam_meta_spr` | 3 / 24 / 9 |
| 调色盤 | `_pal_clear` `_pal_col` `_pal_all` `_pal_spr` `_pal_fade` `_pal_fade_to_all` `_pal_fade_to_bg` `_pal_fade_to_spr` | 5 / 8 / 2 / 1 / 1 / 1 / 2 / 2 |
| PPU | `_ppu_off` `_ppu_on_all` `_ppu_on_bg` `_ppu_waitnmi` | 5 / 2 / 2 / 14 |
| 音樂 | `_music_play` `_music_stop` `_music_pause` | 5 / 6 / 2 |
| 音樂資料 | `_music_title_data` `_music_level1..5_data` `_music_done_data` `_music_gameover_data` | 各 1 |
| 音效 | `_sfx_play` | 22 |
| 輸入 | `_pad_poll` `_pad_trigger` | 2 / 6 |
| 亂數 | `_rand` `_setrand` | 4 / 1 |
| 畫面 | `_scroll` `_set_vram_update` `_unrle_vram` `_bank_bg` | 6 / 4 / 7 / 1 |

**熱點（呼叫最密集）**：`_sfx_play` 22、`_oam_spr` 24、`_vram_put` 21、
`_ppu_waitnmi` 14 → 這四個是實作與效能的重點。

### 16.3 對應到 Apple II 的實作對應（設計）

| neslib | Apple II 對應 |
|---|---|
| `_ppu_waitnmi` | `tick_frame`（//e 輪詢 `$C019`；II+ 用計時延遲） |
| `_vram_adr/put/fill/inc/read` | HGR 掃描線表導向的寫入（`hgr_line_off` + `cur_ptr`） |
| `_unrle_vram` | `hgr_draw_screen`（已驗證可跑完、對垃圾輸入穩健） |
| `_oam_clear/_oam_spr/_oam_meta_spr` | `spr.s` 的 `_spr_setup/_spr_save_draw/_spr_restore` |
| `_pal_*` | HGR 只有黑/白 → 以 **DHGR 调色盤**在過場/選單層實作；遊戲層直接忽略 |
| `_pad_poll/_pad_trigger` | 鍵盤 + 搖桿（`$C000` 鍵盤鎖、`$C061-$C063` PADDL） |
| `_music_play/_music_stop/_music_pause` + 8 個資料 | `ftm.s`（FamiTone v1.24 → AY-8910，已組譯通過） |
| `_sfx_play` | AY 單通道短暫音效（與音樂共用通道需仲裁） |
| `_rand/_setrand` | 2 位元組 LFSR |
| `_scroll/_set_vram_update/_bank_bg` | HGR 無硬體捲動 → 以區域重畫實作（全頁重畫已證明不可行） |

### 16.4 容量警訊（實測）

**只連結 `game.o` 時 `RODATA` 就超過 13.5 KB 主記憶體區 5,479 B（≈19 KB）**
→ `game.c` 把關卡/圖資直接編進 binary。**這正是必須串流的原因**：
把關卡資料移出 binary 後，`CODE ≈ 7,151 B` + 引擎 + 函式庫才放得進
`$6000-$95FF`（13,824 B）。

---

## 17. Phase 6/7/8 完成：整組遊戲連結通過、音效上線、**磁片 image 生出**

本輪把「能跑的 demo」推進到「**整份遊戲可以從磁片開機執行**」。
產出物：`build\a2\ae2_game.dsk`（`BRUN AE2GAME`）。

### 17.1 建置管線（`tools\build_a2.ps1`，端到端綠燈）

| 步驟 | 產物 | 實測大小 |
|---|---|---|
| `a2_assets.py` + `a2_art.py` | 關卡 NES-RLE、圖資、HGR tiles | 26 關 total 10,398 B；圖資 total 1,317 B |
| `music_image.s` → `a2_music.cfg` | `music.bin` @ `$5000` | **3,986 B** |
| `a2_music_offsets.py` | `src\a2\music_offsets.h` | 8 個 `MUSPTR_*` |
| `ftm.s`+`sys.s`+`sfx_image.s` → `a2_cold.cfg` | `cold.bin` @ `$D000`（LC RAM bank） | **2,346 B / 4,096 B**（剩 1,750 B） |
| `a2_cold_stubs.py` | `src\a2\cold_stubs.s`（13 個 `jmp $ADDR` 轉接） | — |
| `game.c` + 引擎 + `apple2enh.lib` → `a2_128.cfg` | `game.bin` @ `$6000` | **12,282 B / 13,824 B** |
| `dos33.py` | `ae2_game.dsk` | 309 sectors free |

磁片目錄（35 檔）：`HELLO`、`AE2GAME`(49)、`COLD`(11)、`TILES`(18)、`MUSIC`(17)、
`LV00`–`LV19`（2–4 檔）、`TITLE`、`CREDITS`、`GAMEOVER`、`WELLDONE`。

主體記憶體配置（`-vm` 讀圖）：`DOSBUF $1800-$19FF`、`_vram $0800`、`_main $7DD3`、
`__ONCE_RUN__/__BSS_RUN__ $8F6B`、BSS 1,050 B、`__HIMEM__ $9600`、stack `$0100`。
`__LC_START__ == __LC_LAST__ == $D400`（`LC` 段是空的 → 函式庫那個寫死在 `$D39A` 的
`bltu2` 沒有發出位元組 → 與 cold image 不衝突）。

### 17.2 Cold image 切分（//e 專屬碼放 LC RAM）

`-t apple2enh` 的程式碼要放在 `$D000-$DFFF` 的 language-card RAM bank（RAM mode），
才不會跟 ROM 搶位址、也才不會用到 II+ 上不存在的东西。
`ftm.s`（AY 音樂+音效）、`sys.s`（60 Hz tick / 計時 / 鍵盤）、`sounds.s`（音效庫）
都進 cold image；主體用 `cold_stubs.s` 的 `jmp $ADDR` 轉接。

**ca65 不會自動 export 底線開頭的 label**（`sounds:` 在 NES 版是跟 crt0 同單元，
所以從來不需要 export）→ `src\a2\sfx_image.s` 結尾補 `.export sounds`。

### 17.3 FamiTone 音效語意的兩條硬事實（讀 `src/famitone.s` 得）

1. **SFX 串流是「每影格」推進一步，而且三種狀態都跑**（playing / paused / 完全沒載入音樂）。
   路徑全部彙聚在一起：`famitone.s:328-335` 只有 `FT_SONG_SPEED != 0 且 >= 0 且 新列` 才進
   `@row`(336) 做 channel stepping；`beq @noMusic`(329)、`bmi @noMusic`(330)、`bne @noRow`(335→388)
   全部落到 `@noMusic`(403) → `bpl @noPause`(406→414) → 輸出轉換(418-531) →
   `dec FT_FRAME_CNT`(533) → `@noSkipM`(537) → **SFX 區塊(539-551) → 輸出推送(553)**。
   所以只有 channel stepping 受「新列」限制，**音效每影格推進、每影格輸出**。
   暫停時走 407-413：把音樂音量強制設成靜音後 `jmp @noSkipM`(413→537)，音效照樣跑。
   （NTSC 的 `FT_PAL_ADJUST` 是負值 → 535 `bne @noSkipM` 成立 → 每影格只 dec 一次。）

   **我先前寫成「音效每音樂列推進一步、音樂停了音效就不動」，是錯的。**
   `ftm_tick` 原本把音效放在列區塊內、整段又被 `playing` 擋掉 → 音效推進慢 speed 倍
   （典型 4-6 倍），1 影格音效（sfx11/12/13）幾乎聽不到，且 `music_stop()` 後音效完全凍住。
   已改成：`dec frame_cnt` 每影格、只有 channel stepping 受新列限制、
   音效四條串流**每影格**推進、`ay_out` 每影格輸出。

2. **音效串流寫的是「opcode 點名的那個 NES 聲道」，不是「它所在的 slot」**
   （`famitone.s:970-1016` `@updateBuf`：buffer byte 1/2 = pulse1、4/5 = pulse2、
   6/7/8 = triangle、9/10 = noise）。
   → 我原先把 slot 0/1/2/3 直接映射成 AY 的 A/B/C/noise 是**錯的**：
   `game.c` 22 個 `sfx_play` 呼叫只用 channel 0/1/2，其中 `SFX_EXCHANGE`、`SFX_BRIDGE`、
   `SFX_WALK1/2`、`SFX_LADDER`、`SFX_NO_EXCHANGE` 是純 noise 串流，
   在舊映射下**完全無聲**。已改成「四條串流各自套到四個 AY 目的地」。

3. **暫停要保留模組**：`FamiToneMusicPause`(`famitone.s:296-305`) 只是把 song speed 變負，
   模組留著、音效照跑、resume 從原處接續。
   `neslib.c` 原本把 `music_pause(1)` 映射成 `ftm_stop()`、`music_pause(0)` 什麼都不做
   → `game.c:1123` 進暫停選單後音樂**永遠回不來**（選單裡的 `sfx_play(SFX_MENU)` 也無聲）。
   已加 `ftm_pause(flag)`（`paused` 旗標）並照 famitone 語意實作：暫停時 `ay_out` 跳過音樂貢獻、
   音效繼續、`music_pause(0)` _resume_ 接續。

### 17.4 Mockingboard 接線（查證，非猜）

來源：Tom Charlesworth 的 `mb-audit`（對真實 Mockingboard 硬體量測、並與 AppleWin 同步驗證）
<https://github.com/tomcw/mb-audit> 的 `MockingboardDefs.a`：

```
SY6522_ORB = base+0   port B output -> AY 控制線（register + strobe）
SY6522_ORA = base+1   port A output -> AY 資料匯流排
port B: AY_LATCH=7  AY_WRITE=6  AY_READ=5  AY_INACTIVE=4  AY_RESET=0
        （bit2/1/0 = /RESET, BDIR, BC1；BC2 固定高）
AY R7:  AY_DIS_A = %00001001 -> bit0 tone A off, bit1 B, bit2 C, bit3 noise
        => $0F 全靜音、0 全發聲
AY R8/9/10 bit4 = amplitude mode（0 = 固定音量）=> 0 = 靜音
```

**我原先把「值」寫到 base+0（port B）→ 全部音效/音樂都寫錯埠。** 已修正：
控制線走 `base+0`、資料走 `base+1`；讀取時先把 DDRA 設成輸入、讀完還原。
另外補上 6522 復位後 DDRB/DDRA 預設是**輸入**這件事（設成輸出），以及 AY `/RESET` 脈衝。

Mixter 初始值也是抓錯的：原本 `mix = $08`，而 `$08` 的 tone-disable 位元（bit0-2）
本來就是 0 → `mix &= ~bit` 永遠沒作用 → **R7 永遠 = $08，tone 永遠開著、無法靜音**。
改成 `$0F` 後離線模擬才看到 `R7 = $0E`（只開 tone A）這種正確輸出。

### 17.5 離線 AY 模擬器 `tools\a2_sfx_probe.py`（本機無聲卡、a2run 無 VIA）

把 `sfx_start` / `sfx_step` / `mix_cand` / `ay_out` 逐位元組模型化，直接吃真的 `src/sounds.s`：
`noise_tab` 從 `ftm.s` 解析（不是 32 筆就中止）、`sounds` 的真實位址從 `build\a2\cold.map` 解析。

探測過程抓到兩個**探測器自己的**錯（不是驅動錯），值得記：
* 位址表基址設 0 → 每條串流的 pointer 高位元組 = 0 → `ftm.s` 視為未啟動 → 多數音效顯示 0 影格。
* `sounds:` 的位址表是 **15 個 word（30 B）**，我按 16 個算 → 每條串流的位址都**偏 2 位元組**
  （`@sfx11` 開頭變成 `0A 0F 10 09 30 FF`，少了 `09 3A`）。

修正後全綠：

```
  sfx0  61f  clean $FF end  drives: toneA        sfx8  11f  clean  drives: noise
  sfx1  43f  clean          drives: toneA        sfx9   9f  clean  drives: toneC
  sfx2  13f  clean          drives: noise        sfx10  6f  clean  drives: noise
  sfx3  13f  clean          drives: toneA        sfx11  2f  clean  drives: noise
  sfx4  13f  clean          drives: toneA        sfx12  2f  clean  drives: noise
  sfx5  49f  clean          drives: toneA, toneB sfx13  3f  clean  drives: noise
  sfx6  25f  clean          drives: toneA        sfx14 91f  clean  drives: toneA
  sfx7  22f  clean          drives: toneA
all 15 streams decode, terminate, and stay inside the AY 12-bit range
```

影格輸出範例（音效 0，注意 R7 只開 tone A、R8 音量逐段變化）：
`f1 R0=02 R7=0E R8=0C` → `f6 R0=00 R7=0E R8=0E` → `f11 R7=0E R8=05`。

### 17.6 待辦（老實講）

* **Phase 0/7/5 的真機驗證還沒做**：a2run 只有 II+ 核心（無 //e firmware、aux RAM、
  language card、6522 VIA、DHGR），所以 cold image 在 `$D000` 執行、DOS 指令載入、
  Mockingboard 發聲這三件事**只能在 AppleWin/真機確認**（AppleWin 用 `-wav-mockingboard`）。
  DOS 指令路徑的對照實驗已證明我的實作與 kit 的 `dos.asm` 行為一致（在 a2run 裡都停在 DOS 內），
  差距在環境，不在程式。
* 音準：`N = 1.9865·P`（AY 時鐘 1.773447 MHz）自我一致；網路上一份常用對照表
  （Michaelangel007 `apple2_mockingboard`）用 ~1.0 MHz 基準，差約 1.77 倍。
  實測時若整體低一個八度，把倍數從 2 調成 1 即可（一行）。
* `ae2_demo.dsk` / `ae2_min.dsk` 是舊的 demo 片，未重包。

### 17.7 磁片 image 的**讀回驗證**（`tools\a2_dsk_verify.py`，已併入管線）

`dos33.py` 只有寫入、沒有讀回模式；印目錄**看不出** T/S 鏈斷掉、檔案被截斷、
BIN header 被包兩次。所以寫了獨立驗證器，照 DOS 3.3 的真實結構走一遍：
`VTOC → catalog → T/S lists → data sectors`，再把讀回的位元組跟打包前的 source 逐位元組比。

DOS 3.3 的 VTOC 在 **track 17 sector 0**、catalog 在 track 17 sector 15..1
（**track 1 是 DOS 程式碼**；track 1 才是 VTOC 的是 DOS 3.2 — 一開始按 3.2 假設會全部找不到）。
catalog 每 sector 7 筆、每筆 35 bytes，位於 `0x0B + k*35`：
`+0/+1` = T/S 起始、`+2` = 類型、`+3..32` = 名稱（high-bit）、`+33..34` = sector 數（LE）。
T/S list sector：`b1/b2` = 下一個 list、pairs 從 `0x0C` 起、每 sector 122 對。
**catalog 的 sector 數包含 T/S list sector 在內**（`nsect = data + lists`）。

結果（管線最後一步）：

```
build\a2\ae2_game.dsk: volume 254, 35 catalog entries
  AE2GAME B T/S T18/S7  49 sect 12282 B  load $6000  == game.bin exact
  COLD    B T/S T21/S10 11 sect   2346 B  load $D000  == cold.bin exact
  TILES   B T/S T21/S1  18 sect   4096 B  load $4000  == hgr_tiles.bin exact
  MUSIC   B T/S T23/S15 17 sect   3986 B  load $5000  == music.bin exact
  LV00..LV19  ... 全部 exact（26 關）
  TITLE/CREDITS/GAMEOVER/WELLDONE 全部 exact
data sectors claimed: 152 of 512 usable
RESULT: OK
```

順帶用 `tools\a2_pack_check.py` 直接問 packer 自己記的 T/S（`Dos33Image.catalog`），
兩邊對得上、沒有任何檔案指到 catalog track。

**踩到的坑（記下來）：驗證器用 hex 印 track/sector，`T17/S0F` 其實是 track 23。**
我一度按十進位解讀成「MUSIC 的 T/S list 落在 catalog track 17」，還去追一個不存在的 bug。
現在驗證器一律用十進位輸出，並對 `track >= 35 / sector >= 16` 的 pair 直接中止——
避免「越界 pair 湊出空 slice、比對剛好通過」這種假陽性（這次就真的差一點被騙過去）。

### 17.8 輸入對接：**搖桿 bit 常數跟 game.c 的 PAD_* 完全對不上**（已修）

`game.c`（neslib 的 NES 搖桿配置）：
`PAD_A 0x01`、`PAD_B 0x02`、`PAD_SELECT 0x04`、`PAD_START 0x08`、
`PAD_UP 0x10`、`PAD_DOWN 0x20`、`PAD_LEFT 0x40`、`PAD_RIGHT 0x80`。

`sys.s` 原本用的是自己一套 `JOY_RIGHT $01 / JOY_LEFT $02 / JOY_DOWN $04 / JOY_UP $08 /
JOY_B $40 / JOY_A $80`。遊戲 26 處 `PAD_*` 測試裡，`PAD_LEFT/PAD_RIGHT/PAD_UP/PAD_DOWN`
（走路、爬梯子 L1330-1375）看的是 0x40/0x80/0x10/0x20，搖桿只會送出 0x01/0x02/0x04/0x08
→ **角色完全不會動**；反向選單的 `PAD_UP/PAD_DOWN`(L661/666) 同理。
已把常數改成遊戲的位元定義，搖桿 → `PAD_LEFT/RIGHT/UP/DOWN`、按鈕 → `PAD_A`。

鍵盤 fallback 也補齊（原本只有 a/d）：
`a/d/w/x` = 左/右/上/下、`space` = A、`/` = B、`Return` = START、`s` = SELECT
（`SELECT` 是 `game.c:617` 的 cow-level 彩蛋、`START` 是暫停選單 L1121）。
對照表放在 RODATA 的 `kb_map`，`input_poll` 走表對應，結尾 0x00 终止。

本輪最終產出（管線綠燈 + 磁片讀回驗證 OK）：
`cold.bin 2,405 B`（LC RAM 4,096 B 內）、`game.bin 12,287 B`（視窗 13,824 B）、
`music.bin 3,986 B`、`ae2_game.dsk` 35 檔、308 sectors free。

## 18. AppleWin 實測期：六個真實缺陷（每個都有量測依據）

這節只記**量測到的**東西。前面 §17 的管線是綠燈、磁片是讀回驗證過的；這輪把磁片放進
AppleWin（`C:\dev\applewin\AppleWin-x64.exe -d1 build\a2\ae2_game.dsk -model apple2e`，
`HKCU:\Software\AppleWin\CurrentVersion\Configuration\Slot 4\Card type = 3` 裝 Mockingboard）
跑，逐條挖。下面每一條都改到 code 了。

### 18.1 RLE 格式：tag 式，不是 (count, value) 對（雪花根因之一）

`src/neslib.s` 的 `_unrle_vram`（neslib.s:334-372）是 **tag 式**：

```
tag = *p++
loop: b = *p++
      if b == tag:  count = *p++;  if count == 0 -> end;  把「上一個 byte」重寫 count 次
      else:         last = b; 寫 b
```

`src/a2/neslib.c` 先前實作成 (count, value) 對，同一份 `credits.bin` 解出 **8,010** 個索引
（正解 1,024）→ 整屏彩色雪花。改成 tag 式後，**30 個 art/level payload 全部剛好解出 1,024**。
驗證工具：`tools\a2_render_art.py` 離線解 tag 式串流 + 套 `build\hgr_tiles.bin`（每 byte `|0x80`）
→ 280x192 PNG。`TITLE` 渲染出藍字 magenta 條紋的 **「ALTER EGO / PRESS START」**，
證明 tileset、索引對應、scanline 排布三者皆正確。

### 18.2 HGR 的 bit 7（雪花根因之二）

tileset 是 NES pattern 資料，bit 7 **清**；HGR 每個 byte 的 bit 7 是**最左那個白色像素**，
必須**設**。直接寫 raw 會讓 7-pixel 格全部左移一格 → 讀起來是雜訊。
修法：`hgr.s` 的 `hgr_put8` 與 `spr.s` 兩處 sprite 寫入，全部 `ora #$80` 後才 `sta (cur_ptr),y`。

### 18.3 cc65 `apple2enh.lib` 的 `pushax` 是壞的（V2.19，Git e11fb5c）

`pushax.o` 存低 byte 用的是 `$92` — **6502 沒有這個 opcode**（1-byte JAM），
所以 C-stack slot 的低 byte 根本沒寫进去。實測：PC 卡 `$8B59`、SP `$01FD`，
而且 `_main`/`_neslib_init` 的 breakpoint 永遠不觸發，因為 `callmain()` 在 call `main`
之前就先进 `pushax`。
管線自癒：複製 `apple2enh.lib` → `apple2enh_patched.lib`，用 `ca65 -t apple2enh
src\a2\pushax_fix.s` 組出正確符碼，`ar65 d` 刪掉壞 member、`ar65 r` 放進新的。
連結後全部 stack helper 都核過位址：`pushax $8CB0`、`pusha $8B7F`、`popax $8ACA`、
`pushw $8B91`、`popptr1 $8B6D`、`incsp1 $8AC3`、`decsp1 $8A46`、`callmain $89C3`。

### 18.4 零頁歸屬：//e 上 $0050 不是我們的

cc65 標準 `apple2enh.cfg` 用 `ZP: start = $0080, size = $001A`。本專案一度放 `$0050`，
正壓到 Monitor 的 `SPTR`（$0050-$0051，它的 text-output store pointer）→ Monitor 的 COUT
走到垃圾裡去。實測到的現象：BRUN 之後 `$0300-$0364`（DOS/Monitor 的 vector 區）**全零**、
SP `$01EA`、stack 上全是 Monitor 的 return address。

//e 零頁歸屬（本專案採用）：

| 區間 | 歸屬 |
|---|---|
| `$0050-$0051` | Monitor `SPTR` |
| `$0068-$0073`, `$00B2-$00B7`, `$00BE-$00BF`, `$00C6-$00C7`, `$00D0-$00D3`, `$00E0-$00E3`, `$00E8-$00EB`, `$00F0-$00F5` | Applesoft（**resident**，因為是 HELLO 去 BRUN 遊戲） |
| `$0074-$007B` | Monitor text-window 變數 |
| `$00B8-$00C4` | DOS 3.3 RWTS parameter block（`lvload.s` 刻意使用） |
| `$0080-$00AF` | **本程式零頁（48 B）** |

連結需求 58 B > 48 B，所以把 `hgr.s` 尾端那組**死碼**（一份重複的 sprite blitter，
`scrn_ptr/buf_ptr/buf_base/spr_ptr/spr_m/spr_x` 共 11 B，`hgr.s` 自己 `.import` `spr.s` 的版本、
自己沒 `.export`）連同程式碼一起砍掉 → 47 B，進窗。
砍除工具 `tools\a2_strip_hgr_sprites.py`；零頁用量統計 `tools\a2_zpusage.py`。

### 18.5 LC RAM bank 的 soft switch：`$C082`/`$C089` 是 ROMIN，不是 RAM

`lv_assets()` 要把 HELLO BLOAD 到暫存區的 COLD image 搬進 language-card RAM bank。
原本寫 `lda $C082`（以為是 WRRAM8）→ 搬 → `lda $C089`（以為是 READRAM8）。

Apple //e I/O 表（[Jon Relay's Apple II I/O Memory](https://www.kreativekorp.com/miscpages/a2info/iomemory.shtml)）：

| 位址 | 名稱 | 效果 |
|---|---|---|
| `$C080` | | read RAM bank 2, no write |
| `$C081` | | read ROM, write RAM bank 2 |
| `$C082` | **ROMIN** | **read ROM, no write** |
| `$C083` | **LCBANK2** | **read + write RAM bank 2** ← 要的就是這個 |
| `$C088` | | read RAM bank 1, no write |
| `$C089` | ROMIN | **read ROM**, write RAM bank 1 |
| `$C08B` | LCBANK1 | read + write RAM bank 1 |

所以舊寫法是「寫入被關閉 → 搬了個空的」+「讀取走 ROM → cold stub 的 `jmp $D093`
跳進 Monitor/Applesoft ROM」。改 `lda $C083` 後，$D000-$DFFF 同時可讀可寫 RAM。

順帶把 soft switch 名稱核過（同一份表）：`TXTCLR $C050`、`TXTSET $C051`、`MIXCLR $C052`、
`MIXSET $C053`、`LOWSCR/TXTPAGE1 $C054`、`TXTPAGE2 $C055`、`LORES $C056`、**`HIRES $C057`**、
`DHIRESON $C05E`、`DHIRESOFF $C05F`。`$C022 TBCOLOR` 是 **IIgs only**，//e 上寫它無效（無害）。
→ `hgr_init` 的 `TXTCLR/MIXCLR/HIRES/LOWSCR` 組合是正確的。

### 18.6 啟動程式：cc65 的 apple2enh crt0 不守 DOS 3.3 BRUN 的三條契約

cc65 內建 crt0 是為 apple2enh runtime 寫的（裝 COUT hook、解 DOS 命令列、由 apple2enh
exit 路徑離開）。它**不做** DOS 3.3 BRUN 程式必須做的三件事（依 kit 的
`dev/cc65/crt0_apple2.s` 文件化契約）：

1. **零頁是 Monitor/DOS/Applesoft 的，離開時要還回去**（整頁 256 B）。
2. **`SOFTEV`（$03F2-$03F4）** 是 soft-reset event vector；Ctrl-RESET 走它。不裝，程式內
   按 Ctrl-RESET 就 warm-boot 到Nothing，機器卡在 Monitor。
3. cc65 的 C-stack pointer `sp` 要指到自由 RAM 頂（`__STACKSTART__`）。

已寫 `src/a2/crt0_dos33.s`（`.export __STARTUP__` → 把 library 的 `crt0.o` 擠出 image，
`zerobss/copydata/initlib/donelib` 照用 library），並連結在**第一個**。
`DOSWARM = $03D0`（DOS 3.3 warm start，`]` 提示字元）。
cfg 因此需要 `__STACKSTART__`、`DATA: define = yes`（`copydata` 要 `__DATA_LOAD__/RUN__/SIZE__`）。

### 18.7 `zerobss` 把 `initlib` 自己清掉（BRK at $8F82）

`initlib` 在 segment **ONCE**。cfg 照 cc65 標準寫 `BSS: start = __ONCE_RUN__` →
BSS 起址 = ONCE 起址 = `$8F80` → `jsr zerobss` 把 `initlib` 的**程式碼**清成 0，
接著 `jsr initlib` 執行全零 = **BRK**。
Monitor 印出 `8F82-  A=60 X=00 Y=9F P=37 S=F9` + `*※`（Monitor 的 BRK handler），
`a2_where.py` 對 map：`$8F82` 在 `initlib`（$8F80）內 2 bytes 處。
修法：`BSS: start = __ONCE_RUN__ + __ONCE_SIZE__`。

### 18.8 `ZPSAVE` 跟 `BSS` 同址 → `zerobss` 清掉零頁快照（本輪主因）

`ZPSAVE`（零頁快照，259 B）原本 `load = MAIN` → ld65 把它放在 `$8F8C`，
**正是 `__BSS_RUN__`**。crt0 的順序是「存零頁 → `jsr zerobss`」，
於是 `zerobss` 把剛存的快照清成 0；離開時 `restore()` 就**把 256 個 0 蓋到 $00-$FF**，
Monitor 的零頁全毀，`JMP $03D0` 沿著歸零的指標跑 → 實測 **PC = $000E**（`ENDCHR`，
零頁變數）、`cycles: 021A950A`（跑過 35M cycles）、`$0300-$0364` 全零、整屏 raw HGR 雪花。
修法：`ZPSAVE: load = ZPBUF`，`ZPBUF: start = __BSS_RUN__ + __BSS_SIZE__`
（實測 `ZPSAVE $93A8-$94AA`，BSS 到 `$93A7`，stack `$9500-$95FF`，互不重疊）。

### 18.9 `vram` 陰影壓在 Applesoft 的程式文字上（$0800）

cfg 註解原本寫「$0800-$0FFF 是 BASIC HELLO 區，BRUN 過的 binary 擁有它」。**錯**。
HELLO 是 Applesoft，它 BRUN 遊戲後**仍 resident**：程式文字在 `$0801`、變數由 `LOMEM $0800`
往上長。`neslib_init()` 的 `fill_mem(vram, 0, GRID_COLS*GRID_ROWS)` = **1,920 個 0 蓋過去**。
實測 `$0800` 前 32 bytes 是 `... 41 44 20 43 4f 4c 44 2c 41 24 31` = **"AD COLD,A$1"**
（HELLO 那行 `BLOAD COLD,A$1A00` 的尾巴）。
修法：`vram` 搬到 **$1800-$1AFF**（HGR 之外的自由 RAM）。
順帶把低頁重排，並把 COLD 暫存位址從 `$1A00`（现在是 RWTS T/S list 區）搬到 **$2000**
（HGR page，`lv_assets` 之後 `hgr_clear` 就把它填黑）：

| 區間 | 用途 |
|---|---|
| `$1000 / $1200 / $1400 / $1600` | HELLO BLOAD 的 art（CREDITS 187 / TITLE 429 / GAMEOVER 201 / WELLDONE 500，每槽 512） |
| `$1800-$1AFF` | **VRAM 陰影 1,920 B** |
| `$1B00-$1BFF` | LSTBUF（`lvload.s` 建的 RWTS track/sector list） |
| `$1C00-$1E3D` | level stream（最大 payload 實測 573 B） |
| `$1E40-$1EFF` | DOSBUF（DOS 命令用的零頁 swap） |
| `$2000-$29FF` | COLD 暫存（HELLO `BLOAD COLD,A$2000`） |

### 18.10 AppleWin 自動化：量測到的限制（下次直接照做，別再摸）

* **截圖只能 `PrintWindow` + `PW_RENDERFULLCONTENT`**（`tools\aw_cap.ps1` 的 `Shot3`/`HS3`）。
  `CopyFromScreen`（`Shot2`/`HS2`）在本機固定 `The handle is invalid`，而且**靜默回傳舊畫格**
  → 之前所有 `aw_cmd.ps1` 的截圖 hash 都固定是開機畫格，等於沒量到東西。已把 `aw_cmd.ps1` 改走 `Shot3`。
* **F7 要用 `PostMessage(WM_KEYDOWN/WM_KEYUP)`**，`lParam = 1 | (sc<<16)`（keyup 再 `+2147483648`）。
  `SendInput` 按 F7 實測**不會**開 debugger。
* **debugger console 打字走 `WM_CHAR (0x0102)` 逐字元，再 `Tap 0x0D 0x1C`。**
* console 指令（實測 + `HELP` 取得）：可用 `BSAVE "f",$2000,$1E00`（檔名**必須**加引號；
  AppleWin 寫**純 memory、無 header** 到 `g_sCurrentDir`）、`HELP <CATEGORY>`、`U <addr>`（反組譯）、
  `T`/`TF`/`TU`（trace）、`A`（assemble）、`H`（disasm 游標）、`=`（PC 設成目前指令）、`PC = <addr>`。
  **`G` 在 console 是 `Illegal Command`**（run 是 debugger 主視窗的指令，不是 console 的）。
  `C2D0/20` 是 disasm pane 語法，不是 console 語法。
* console 輸出會分頁（`...press SPACE continue, ESC skip...`）；要第一頁就**別按 SPACE**
  （`tools\aw_one.ps1`），要全部就連續按 SPACE（`tools\aw_help_pages.ps1`）。
* **`BSAVE` 前必須確認機器真的在跑**：右側 `cycles:` 若只有個位數（實測看過 `00000002`），
  表示機器剛 reset，dump 到的是開機狀態、不是執行中狀態 — 之前多次「各 build 的 dump 完全相同」
  就是這個原因，那些 memory 結論全部作廢。
* 上一輪遺留的 `C:\dev\applewin\ae2_bp.txt`（`BP $7DA9/$8688/$8792/$C2B0/$04FF`）是舊 build 的
  位址；位址會随連結漂移，舊 breakpoint 會把機器停在無意義的地方。
* 本機無聲卡 → AY 音高**無法**用聽的驗證（`N = P + ((P*9+32)>>6)`，AY clock 1,020,432 Hz
  = `CLK_6502_NTSC`，`f = CLK/(16N)`，對 NES `f = 1789772.5/(32P)` → `N = 1.140293 P`）。

### 18.11 目前狀態（老實講）

管線綠燈、2 次 link/pack 收斂、`game.bin 12,172 B`（視窗 13,824 B）、
`ae2_game.dsk` 35 檔 / 153 of 512 data sectors / **`RESULT: OK`**（每檔逐 byte 讀回比對 exact）。

AppleWin 實測：磁片開機進 DOS 3.3 → 自動跑 HELLO（BLOAD COLD/TILES/MUSIC/CREDITS/TITLE/
GAMEOVER/WELLDONE → `BRUN AE2GAME`）→ 程式載入 `$6000` byte-exact → **跑過 35M cycles**
（§18.7/§18.8 修好前是停在 BRK）。

**尚未解決**：螢幕是整屏 raw HGR 雪花，且內容正是 COLD image 的 bytes（`hgr_init` 已執行、
`hgr_clear` 未執行），PC 終止在 `$000E`。故障點已縮到 `neslib_init()` 的
`hgr_init()` 與 `hgr_clear()` 之間。下一步要用 debugger 的 `T`（trace）逐指令走
`_lv_assets → _hgr_init → _hgr_set_tiles → _hgr_clear`，並先確認 `cycles:` 是執行中的值。

---

## 19. 本輪：畫面為什麼是條紋 — 五個實測結論

### 19.1 「條紋」不是 tile mapping 錯誤，是整頁填同一個 byte

HGR 下整頁填同一 byte 就畫出等距垂直條紋（`$20` = 8 個像素亮 1 個、`$0F` = 4 亮 4 滅）。
所以「螢幕是條紋」本身不是證據，必須量 bytes。

### 19.2 螢幕 hash 全部作廢：抓的是 Configuration 對話框

實測 `Get-Process MainWindowHandle` 回傳的是 **'Configuration'** 對話框，
`'Apple //e (original) Emulator'` 是另一個 top-level window（`vis=False`）。
所有打給 main window 的按鍵與截圖都落在對話框上。

**鐵證**：三個會畫出明顯不同 HGR 頁的 build，螢幕 hash 完全相同
（`477F1CAE13BA → EDDC92899815 → 655B4A4900A7`）。
hash 相同 = 抓的不是遊戲。§18 裡所有靠 hash 得到的結論一併作廢。

可用的擷取路徑（`tools/aw_emu.ps1` + `tools/aw_child.ps1`）：
依 title 找 emulator window → `WM_CLOSE` 掉 Configuration → `ShowWindow(SW_SHOW)` →
`PrintWindow(flags=2)` 成功（`CopyFromScreen` 在本機一律 "The handle is invalid"）。

### 19.3 `hgr_page()` 的 index 寫錯（`tools/a2_art.py`）

```python
page[out_row * 8 + r * 40 + col]      # 錯：40 乘到 tile 內的那一列
page[(out_row * 8 + r) * 40 + col]    # 對：40 乘到 scanline
```
錯的版本把 tile 打散到少數幾條線上，整頁 99% 是 0（title 實測 7,680 中只有 34 個非零 byte）。
修好後 title 1,164、credits 870 個非零 byte，離線渲染直接讀出 **ALTER EGO / PRESS START**。

### 19.4 NES 32×30 nametable 裝不進 192 條 scanline

NES 畫面 32×30 tiles = 256×240 px；HGR 是 280×192。
實測 art 本身：title 用 nametable 第 4–23 列（加 30–31 邊框），credits 用 7–25 列。
取 **第 3–26 列**（24 列 = 192 條）是最小同時包住兩者的窗口；
原本取 0–23 會切掉 credits 最後一列文字，並讓 HGR 頁最下面 32 條完全沒被畫到。

### 19.5 `asl a` 索引 384-byte 表在 scanline 128 溢出

`hgr_line_off` 是 192 個 word = 384 bytes，byte index 走到 382，會跨頁。
`hgr_set_row` 與 `hgr_draw_screen` 都用 `asl a / tay / hgr_line_off,y`：
scanline 128 時 `asl a` 溢成 0 → **第 128–191 條畫到第 0–63 條**，頁的下面三分之一永遠沒寫到。
實測畫面正是「上面約 160 條有畫、下面 32 條是原封不動的 `$20`」。
修法：`line_addr` 把 index 的高 byte 加進 word 的高 byte（`scanline>>7` = 0 或 1）。

### 19.6 本輪修好但仍未解決的問題

* `lv_assets()` 之前不能畫任何東西：它把 `$2000` 的 2,560 bytes 复制到 LC bank `$D000`，
  在它之前畫 page 會讓它复制那個填充而不是 cold code（實測 LC bank 整片 `$A5`）。
* `fill_mem()`（C）換成 asm `vram_zero()`；zeropage 已滿（`$007C–$00B1`，Applesoft 由 `$00B2`
  開始），所以 `vram_zero` 借用 `hgr.s` 的 `cur_ptr`（`.importzp` + `.export cur_ptr`；
  `.import` 会让 ca65 無法證明是 zero page，`(ptr),y` 直接 range error）。
* `hgr_init` 加上 `$C002 RDMAINRAM` / `$C004 WRMAINRAM`（Applesoft 80 欄模式留 80STORE on，
  寫 `$2000-$3FFF` 會進 aux display memory，畫面顯示 main → 畫了看不见）。
  **加上後可見輸出沒有變化**，所以這不是本輪條紋的成因。
* 目前狀態：離線渲染證明 asset 與幾何正確（文字清楚），模擬器上畫面仍是極少量內容
  （實測：整頁 `$20` 加約 4 條白色虛線）。**遊戲畫面仍未可讀。**

### 19.7 本機自動化限制（新增）

* AppleWin 啟動必開 'Configuration' 對話框，且它搶走 main window 角色 → 必須 `WM_CLOSE`。
* Debugger window 開起來是 **title 空字串 + `vis=False`**，要 `ShowWindow(SW_SHOW)` 才收得到按鍵；
  它 **沒有任何 child window**（console 是自繪的）。
* 本輪實測：`ShowWindow` 後 `IsWindowVisible=True`，但 `BSAVE` 仍不會產生檔案
  → 打進 debugger 的字元沒有進入 console。截圖 debugger window 得到整片黑。
* **結論：本機無法可靠操作 debugger console，也無法 `BSAVE` 驗證記憶體。**
  可信的驗證手段只剩：離線渲染 asset（`tools/a2_render_hgr.py`）+ emulator window 的
  `PrintWindow` 截圖（`tools/aw_child.ps1`）。

---

## 20. 本輪（goal round 2）：畫面寫入路徑已被證明可用，卡點移到「程式有沒有執行」

### 20.1 量測方法：可數的填充

`hgr_clear()` 填整片同一個 byte 是**不可判讀**的 — 填的值剛好等於頁面原有內容時完全看不出來。
改成 `hgr_diag()`：每條 scanline 填 `$FF`/`$00` 交錯（96 條橫帶），覆蓋率變成可數。

### 20.2 本輪修掉的三個真 bug（都在診斷程式碼裡，每個都有畫面依據）

1. **`sta (dst_ptr),x` 在 6502 不存在**（indexed indirect 只有 Y）。ca65 直接報
   `Expected 'Y' but found 'X'`。
2. **Y 沒有遞增**：`ldy #$00` 後用另一個 ZP byte 計數、`(dst_ptr),y` 的 y 永遠是 0 →
   每條線只寫到 1 個 byte。畫面實測 = 整頁密集雜點（coverage 完整、內容是雜訊）。
3. **`lda #$00` 之後接 `bne @put` 永遠不跳**：`lda` 會設 Z，Z=1 → `bne` 不跳 → 直落進
   `@even: lda #$FF` → 每條線都變 `$FF`，畫面實測 = 整片全白。要 `bra`。

### 20.3 `line_addr` 的 16-bit 加法（第二個錯法）

`hgr_line_off` 是 192 個 word = 384 bytes，byte index 0..382 會跨頁。
**錯法**：`asl a / tay`，再把 `scanline>>7` 加到**讀出來的 word 的高 byte**。
`hgr_line_off+256` 的**位址**高 byte 和 `hgr_line_off+0` 不同，低 byte 也不同 →
scanline 128 以上全部讀錯 entry。
**對法**：`asl a` 的 carry 就是 index 的高 byte，用它分支，走兩個 linker 可解析的
absolute 形式：

```asm
line_addr:
	asl a
	tay
	bcs @hi
	lda hgr_line_off,y
	sta dst_ptr
	lda hgr_line_off+1,y
	sta dst_ptr+1
	...
@hi:	lda hgr_line_off+256,y
	sta dst_ptr
	lda hgr_line_off+257,y
	sta dst_ptr+1
```
（`lda #>hgr_line_off` 用不了：ca65 對 imported absolute 的 `#<`/`#>` 會 range error，
跟 `#<_vram` 同一件事。）

### 20.4 已證明的正面結論

* **寫 HGR 頁的路徑是可用的**：`hgr_diag()` 走 `line_addr`/`dst_ptr` 把整頁 7,680 bytes
  都寫進去（畫面從 DOS 文字頁變成整片 `$FF`，且跨 build 穩定）。
* **asset 與幾何正確**：離線渲染 `titleh.bin` 直接讀出 ALTER EGO / PRESS START。
* **zeropage 乾淨**：map 實測 `cur_ptr=$007E`、`sp/c_sp=$0098`、`sreg=$009A`、
  `ptr1..4=$00A0-$00A7`、`tmp1/2=$00A8/$00A9`，都在 `$007C-$00B1` 內，無重疊。
* **`hgr_line_off` 表本身正確且是視覺順序**：y=0→$2000、y=1→$2400、y=7→$3C00、
  y=8→$2080、y=64→$2028、y=128→$2050、y=191→$3FD0。

### 20.5 收斂到的卡點

對 `s6`（真實 init：`hgr_clear` + `hgr_draw_screen(title)`）與 `e7`（`hgr_clear` 填 `$FF` 探針）
做色彩直方圖，**兩者完全相同**：black 199,563 / green 15,236 / violet 15,232 / white 4,871。
`hgr_diag` 的兩個版本（line-table 版與 linear `cur_ptr` 版）則產生**同一張**全白畫面
（white 219,347、green 0、violet 0）。

判讀：
* 全白 = AppleWin //e 記憶體初始值 `$FF` → **頁面根本沒被寫**。
* 真實 init 的畫面 = DOS/Applesoft 留在頁面的內容 → **也沒被寫**。
* 再加 `a2_mark()`（走 DOS/Monitor CHROUT `$FFD8` 印 `"AE2MAIN OK"`，完全不依賴 HGR）：
  畫面是整片黑，**沒有任何文字**。

→ **卡點不在 HGR 繪圖，在 `BRUN AE2GAME` 之後 C 程式碼有沒有真的執行。**
`hgr_init` 的 soft switch 有生效（AppleWin 狀態列顯示 `H` = HiRes），但 CHROUT 沒有輸出、
頁面也沒有被寫。

### 20.6 本機無法繼續收斂的原因（具體條件）

要判「程式有沒有執行 / PC 停在哪」需要 debugger 的 `PC =`、`BSAVE`、trace；
本機（§18.11、§19.7）已實測：debugger console 收不到按鍵、`BSAVE` 不產檔、
debugger window 截圖是整片黑；`CopyFromScreen` 一律 "The handle is invalid"；
`web_search` 無 API key。
**只剩的觀測管道是 emulator window 的 `PrintWindow` 截圖，而它只能看到畫面，看不到暫存器與記憶體。**





---

## 21. 本輪（goal round 3）：離線驗證 BRUN handoff — 全部正確；並撤回一個錯判

### 21.1 新增離線工具 `tools/a2_read_dos33.py`

直接從 `.dsk` 讀 catalog entry 與檔案資料，解出 DOS header。不依賴 emulator。

### 21.2 撤回：「header 少了 load 低 byte」是錯判

我先前用 catalog 欄位 `+$26/$27` 大端讀 load address，讀出 `load $C3CF / blocks 12544` 這種荒謬值，
據此宣稱「packer 寫了 4-byte header、少了 load 低 byte，所以 BRUN 載到 `$60D2`」。**這是錯的。**

**事實**：DOS 3.3 的 binary header 就是 **4 bytes 小端** `struct.pack("<HH", load, len)`，
kit 自己的 `dev/tools/dos33.py:290` 與 `build_disk.py:47` 都這樣寫，且 kit 的磁片在 emulator 跑得動
（`micro_sokoban.s:1594` 註解 `ADC #4 ; DOS binary header precedes payload` 也印證是 4 bytes）。

實測解碼：

| 檔 | header bytes | 解出的 load | len |
|---|---|---|---|
| AE2GAME | `00 60 c7 2f` | **$6000** ✓ | 12231 ✓ |
| COLD | `00 d0 99 09` | **$D000** ✓ | 2457 ✓ |

`a2_dsk_verify.py` 也獨立回報 `AE2GAME ... load $6000 len 12231` ✓。

**教訓**：欄位偏移/端序沒先驗證就下結論，會生出聽起來很合理、實際全錯的 root cause。
**header 與 load address 是正確的，BRUN handoff 沒有問題。**

### 21.3 離線驗證過的完整鏈路

* `.map`：`STARTUP $006000`、`LOWCODE $607A`、`CODE $62A8-$8CBF`、`RODATA $8CC0`、
  `DATA $8F1C`（`__DATA_LOAD__ == __DATA_RUN__` → `copydata` 不需搬）、
  `BSS $8FD2-$93ED`、`ZPSAVE $DC00`、`__STACKSTART__ $9600`。
* 磁片上 AE2GAME 資料的前 48 bytes 逐 byte 反組譯，與 `crt0_dos33.s` 逐條對上：
  `d8`=CLD、`a2 ff`=LDX #$FF、`9a`=TXS、`a2 00 / b5 00 / 9d 00 dc / e8 / d0 f8`=存整個 zero page 到 `$DC00,x`、
  `a2 02 / bd f2 03 / 9d 00 dd / ca / 10 f7`=存 SOFTEV 3 bytes 到 `$DD00,x`、
  `a9 45 / 8d f2 03 / a9 60 / 8d f3 03 / 49 a5 / 8d f4 03`=裝 `reset_exit`($6045) 進 SOFTEV + `$A5` 標記、
  `a9 00 / 85 98`= `sp` 低 byte（`sp` 實測在 `$0098`，`sp+1` 接著設 `$96` → `sp=$9600` ✓）。
* `__CONSTRUCTOR_COUNT__ = 0` → `initlib` 不跑東西。

**→ 從磁片到 `jsr _main` 之間的每一步都驗證過，是對的。**

### 21.4 CHROUT 探針的兩個教訓

1. 第一版探針印完就掉進 `credits_screen()`，而 `credits_screen` 寫 `$2000-$3FFF`；
   在 LORES/text 模式下 **`$2000-$3FFF` 就是文字頁** → 印出來的字被下一個 call 蓋掉。
   「看不到字」因此**不構成**「程式沒跑」的證據。
2. 第二版印完立刻 `return`（不碰任何繪圖）：畫面仍是**整片黑**，
   且 AppleWin 狀態列顯示 `H`（HiRes）+ `A`（80col）—— 這個 build 裡我的程式碼完全沒有設 HIRES。
   該幀 `F63049003A07` 與三個差異很大的 build **完全相同**。

### 21.5 本輪收斂到的狀態

離線鏈路全對（21.2、21.3），但三個互不相同的 build 產生**同一張**畫面
（`F63049003A07`），且 CHROUT 探針沒有留下任何可見字元。
**要判「`jsr _main` 之後發生了什麼」需要 PC / trace / 記憶體 dump；本機拿不到（§18.11、§19.7、§20.6）。**

### 21.6 順帶修掉：stdio 探針不可用

試過用 `fopen("AE2RUN","w")` 在磁片上建檔做離線可驗證的執行探針（`a2_dsk_verify.py` 可直接查 catalog）。
**cc65 的 stdio 對這個記憶體配置太重**：`RODATA` 溢出 `MAIN` 552 bytes、`BSS` 變成 -1159 → ld65 直接失敗。
已回退。要離線可驗證的執行探針需要直接呼叫 DOS 向量，不能走 stdio。

---

## 22. 本輪（goal round 3）真正的突破：**找到並修掉 65C02 opcode**，並建出可觀測的執行環境

### 22.1 根因：ca65 預設 CPU 是 65c02，Apple //e 是 6502

實測（`build/bra_test.s`）：

| 指令 | ca65 預設 | ca65 `--cpu 6502` |
|---|---|---|
| `bra @x` | **接受**，發出 opcode `$80` | **拒絕**（exit 1） |
| `inc a` | 接受 | **拒絕**（`Illegal addressing mode`） |

**`$80` 在 6502 上是 `STY ($00,X)` — 一個存檔，不是分支。**
**`inc a`（opcode `$FF`）在 6502 上根本不存在。**

**//e 是 6502。AppleWin 的 //e 也模擬 6502。**
**所以 binary 裡只要有 65C02-only 的 opcode，在真機與 emulator 上就會執行成完全不同的東西。**

**修法（已做）**：`tools/build_a2.ps1` 全部 17 處 ca65/cc65 都加上 `--cpu 6502`
（`'-t','apple2enh','--cpu','6502'`）。這樣任何 65C02-only 的程式碼在**編譯期**就會失敗，
不會溜進 binary。

修掉的兩處：
* `src/a2/hgr.s:170` `bra @put` → `bpl @put`（`lda #$00` 後 N=0，`bpl` 必定跳）
* `src/a2/lvload.s:357` `inc a` → `clc / adc #1`

**代價**：6502 codegen 較大 → `BSS` 溢出 75 bytes。
`src/a2/a2_128.cfg` 的 `__HIMEM__`/`__STACKSTART__` 從 `$9600` 提到 `$9C00`
（DOS 3.3 佔 `$9D00-$BFFF`，`$9600-$9CFF` 是空的）→ 程式窗口 13,824 → 15,360 bytes。
`game.bin` 12,242 → **12,591 bytes**，`RESULT: OK`，`AE2GAME load $6000 len 12591` ✓。

### 22.2 新工具 `tools/a2_emu.py`：6502 + //e core，離線跑真正的 binary

**這是本輪最重要的產出。** 之前所有卡住的原因都是「只能看到畫面，看不到 PC / 暫存器 / 記憶體」。
這個工具把 `.dsk` 的 payload 依 HELLO 的方式 seed 進記憶體
（COLD→$2000、TILES→$4000、MUSIC→$5000、四張 art→$1000/$1200/$1400/$1600、binary→$6000、RESET vector=$6000），
然後跑 CPU，可以輸出：PC trace、soft switch 狀態、任意記憶體範圍、$2000-$3FFF 的 HGR 渲染 PNG、
「第一次跳出程式範圍的 JMP 在哪」、以及「誰寫了某個位址」。

**title 這條路徑完全不碰磁碟**（`lv_assets` 只是記憶體搬移），所以不需要模擬 RWTS。

實測結果（`--max-steps 2000000`）：

* **程式真的在跑。** 不是沒執行。
* **HGR 頁 `$2000-$3FFF` 8,146 / 8,192 bytes 非零** → 頁面**有被畫上去**。
* `soft switches: lores=False text=False lc_bank=2 rom=False` → `hgr_init` 的 HIRES 生效、
  `lv_assets` 的 `$C083`（LCBANK2）生效。
* `FIRST ESCAPE: PC=$8AD3 op=$4C -> $D093` = `_mb_init` ✓ 正常。
* 之後 `PC=$D093 op=$00 (BRK) -> $F000` → **`_mb_init` 的位置是 $00**。

### 22.3 順帶修掉 emu 自己的三個錯（都是我的錯，不是產品的錯）

1. **分支 opcode 全部錯位**：我寫成 `0x50=BCC / 0x70=BCS / 0x90=BNE / 0x80=BRA / 0x82=BNE`，
   且**漏掉 `0xD0 BNE`**。正確表：`10 BPL / 30 BMI / 50 BVC / 70 BVS / 90 BCC / B0 BCS / D0 BNE / F0 BEQ`。
   也漏了 `CA DEX`、`BA TSX`、`B8 CLV`。`0x6A` 被前面的分支搶走變成 `ASL A`（正解 `ROR A`）。
2. **soft switch 解碼用 `addr & 0x0F`** → `$C083` 解成 `$03`，語言卡切換永遠不會觸發。
   正解是 `addr & 0xFF`。
3. **只在寫入時觸發 soft switch**。//e 的 soft switch **讀取也會觸發**，
   而 `lv_assets` 用的是 `lda $C083`（讀）。所以 `rd()` 也要走 soft switch。

### 22.4 目前鎖定的下一個真 bug（已定位到指令層級）

`COLD` 搬移後 `$D000` 的前 246 bytes 是**音樂資料**（FT2 block header `1C 00 01 16 ...`），不是 cold.bin。

寫 `$D000-$D0FF` 的來源（觀測）：

| PC | 寫入次數 | 身分 |
|---|---|---|
| `$88E5` | 256 | `_lv_assets`（$88CC 起）✓ 正常 |
| `$60E1` | 16 | `hgr_clear` 的 `STA ($7E),Y` |
| `$61BD` | 16 | `hgr_draw_screen` 的 `put_byte`：`STA ($7C),Y` |

`hgr_clear` 反組譯確認是正確的 32 頁 `$2000-$3FFF`：
```
60D5: A9 00 85 7E   LDA #$00 / STA cur_ptr
60D9: A9 20 85 7F   LDA #$20 / STA cur_ptr+1
60DD: A2 00 A0 00   LDX #0 / LDY #0
60E1: 91 7E         STA (cur_ptr),Y
60E3: C8 D0 FB      INY / BNE
60E6: E6 7F E8      INC cur_ptr+1 / INX
60E9: E0 20 D0 F2   CPX #$20 / BNE
```
**所以 `$60E1` 要寫到 `$D000`，`cur_ptr+1` 必須是 `$D0`；`$61BD` 要寫到 `$D000`，`dst_ptr` 必須跑到 `$D000`。**
→ **指標跑飛（runaway pointer）**，而且 `hgr_draw_screen` 的 `next_byte` 對 `src_ptr` 沒有邊界檢查，
字串沒終止就會一路讀過 LSTBUF / DOSBUF / HGR 頁 / TILES / MUSIC。
**這是下一輪要收的目標。**

### 22.5 離線鏈路（本輪驗證過，全部正確）

* DOS 3.3 binary header 是 **4 bytes 小端** `struct.pack("<HH", load, len)`，
  kit 的 `dos33.py:290` / `build_disk.py:47` 就是這樣，`micro_sokoban.s:1594` 註解 `ADC #4` 印證。
  實測 `AE2GAME -> 00 60 c7 2f` = **load $6000**, len 12231 ✓；`COLD -> 00 d0 99 09` = **$D000**, 2457 ✓。
  （我先前用 catalog `+$26/$27` 大端讀出 `$C3CF` 並據此宣稱 root cause，**已撤回**，見 §21.2。）
* `.map`：`STARTUP $006000`、`__DATA_LOAD__ == __DATA_RUN__`、`__CONSTRUCTOR_COUNT__ = 0`、
  `sp=$0098`、`__STACKSTART__=$9C00`。
* 磁片上 binary 前 48 bytes 逐 byte 反組譯與 `crt0_dos33.s` 逐條對上。

---

## 23. 本輪（goal round 4）：抓掉兩個真 bug，磁片佈局重做

### 23.1 `hgr_clear()` 填的是 `$20`，不是 `$00` — **這才是「條紋畫面」的来源**

`tools/a2_emu.py` 抓到寫入時的暫存器狀態：

```
PC=$60E1 addr=$2000 val=$20 | cur=$2000
```

`hgr_clear` 原本：

```asm
lda #$00
sta cur_ptr        ; A = $00
lda #$20           ; <-- A 被蓋掉
sta cur_ptr+1
...
@b: sta (cur_ptr),y   ; 存的是 $20！
```

**A 同時當「填值」與「頁面高位址」，最後一次 `lda #$20` 贏了 → 整頁填 `$20`。**

**`$20` 在 HGR 是單一 bit 設定的 uniform byte → 均勻間隔的綠色像素 → 就是使用者看到的「條紋」。**
**之前所有「修了沒變化」的觀察全部由此而來：頁面每次都被 `$20` 蓋掉。**

修法：填值放進 zero page 的 `fill_v`，每次存檔前 `lda fill_v`。
**驗證：HGR 頁非零 bytes 由 `8,146 / 8,192` → `0 / 8,192`（全黑）✓**

（`hgr_fill()` 檢查過是正確的 — 它先 `sta fill_v`。）

### 23.2 磁片 art 佈局重疊，**蓋掉 COLD staging page**

`src/game.c` 的 art 指標是 `$1000/$1200/$1400/$1600`，間隔 512 bytes —
那個間隔是照 **NES nametable stream** 的尺寸排的（429/187/201/500 bytes）。
**HGR 形式的檔案是 1,230 / 2,059 / 1,230 / 2,806 bytes。**

實測後果：
* `WELLDONEH` 在 `$1600`，2,806 bytes → 跑到 **`$20F6`**，**蓋掉 `$2000-$20F6` = COLD staging page**。
* `CREDITSH` 在 `$1000`，1,230 bytes → 蓋到 `TITLEH`（`$1200`）。

`lv_assets()` 把污染的 staging 複製進 `$D000` → `_mb_init`（`$D093`）變成 `$00` →
**第一次呼叫它就在執行 BRK**。

emu 的 `COLD copy check` 直接量化了它：**2,215/2,457 相符，242 不同，全部集中在前 246 bytes**，
且 `$D000` 的內容是 FT2 音樂資料（block header `1C 00 01 16`）。

### 23.3 修法：art 改為 **RWTS 逐檔載入** 到單一 `$1000` buffer

`lv_load_name()` 走的是 DOS 命令發射路徑，**實測永不返回**（lvload.s:137-143 記錄），不能用。
`lv_load()` 走 RWTS，是可用路徑。

* `lvload.s`：把 `_lv_load` 拆成共用核心 `lv_stream_at`（A = `lv_tab` 索引，`rv_dst` = 目的地），
  新增 `_lv_load_art`（目的地 `ART_BASE = $1000`）。
* `tsmap.inc` 由 26 條擴成 **30 條**（26 關 + CREDITSH/TITLEH/GAMEOVERH/WELLDONEH 在索引 26..29）。
* `src/game.c`：`credits/title/gameover/welldone` 由「固定指標」改成「索引 26..29」，
  `art_screen(i)` = `lv_load_art(i)` 後 `hgr_draw_screen($1000)`。
* `HELLO` 移除四條 art BLOAD（只留 COLD/TILES/MUSIC + BRUN）。
* `neslib_init()` 移除從 `$1200` 畫 title 的那一行（art 現在由 `title_screen()` 載入後畫）。

**驗證：`COLD copy check: 2457/2457 bytes match, 0 differ` ✓**
磁片重建 `RESULT: OK`，`game.bin = 12,660`，`tsmap.inc (30 entries)`，全部檔案 read-back byte-exact。

### 23.4 emu 自己的兩個錯（已修）

* `seed()` 還照舊 HELLO 預載四張 art → `welldoneh` 在 emu 裡也蓋掉 `$2000`。移除後才看到乾淨的 COLD 複製。
* `if WATCH and ...` 檢查的是 list（永遠 truthy），不是 `WATCH[0]` → 觀測永遠開著。改成 `WATCH[0]`，並加 `--watch` 開關。

### 23.5 下一個已定位的 bug（下一輪目標）

```
FIRST ESCAPE: PC=$D131 executed op=$60 (RTS) and landed at $3ED1
   at that moment SP=$FA A=$04 X=$00 Y=$03
   stack at $0100+SP: 3e 87 e1 7e 3b 60 00 00 ...
```

`$D131` 是 COLD 內 `_ftm_play`（`$D132`）前一個 routine 的 `RTS`。
**返回位址 `$3ED1` 落在 HGR 頁（全零）** → 執行 `$00` = BRK → 卡死在 `$F000`。
棧上還留著 `$603B`、`$7EE1`、`$873E` 這些**程式區**的合理返回位址，
所以是**某處 JSR/RTS 不平衡（多了一次 RTS）**，把呼叫者的返回位址吃掉，
露出底下先前 BRK 推進去的 `$3ED1`。
**下一輪：追誰跳進 HGR 頁、誰多 RTS。**

### 23.6 本輪也確認的事實

* `--cpu 6502` 全線生效後，`lvload.s:357` 的 `inc a` 在編譯期就被擋下（`Illegal addressing mode`），
  證明這條防線有效 — 65C02-only 程式碼現在**不可能**溜進 binary。
* `lv_assets()` 的指標實測正確：結束時 `cold_src=$2A00`、`cold_dst=$DA00`（10 頁 ✓）。
* `hgr_clear` 反組譯確認是正確的 32 頁線性走訪（`$2000-$3FFF`）。

## 24. 本輪（goal round 5）：收掉兩個開放問題，並找到「只畫出一列」的癥狀

### 24.1 `mb_init` **不是**楔子（收掉開放問題 c）

反組譯 `cold.bin` 的 probe 迴圈：

```
D0D3: A9 00      LDA #$00
D0D5: 20 0D D1   JSR $D10D        ; AY 讀取 -> A
D0D8: C9 FF      CMP #$FF         ; 浮空匯流排讀 $FF = 無裝置
D0DA: D0 0C      BNE $D0E8        ; 有裝置 -> mb_present=1
D0DC: E8         INX
D0DD: E0 03      CPX #$03         ; 最多 4 個槽位
D0DF: D0 BB      BNE $D09C
D0E1: A9 00 / 8D 27 DA            ; mb_present = 0
D0E6: AA / 60    TAX / RTS
```

**迴圈有界（`CPX #$03`），必定返回。** AY 位址表實測也正確：`$C400, $C480, $C600, $C610`
（`$E8/$E9` 指向 `$C400` = Mockingboard slot 4 ✓）。
`$D10D` 的 handshake（latch=7 → read=5 → 讀 ORA → inactive=4 → DDRA/DRB=$FF）`PHA/PLA` 平衡 ✓。

### 24.2 AppleWin 截圖通道**無法偵測變化**（重要觀測限制）

兩個**完全不同的 build** 開機後截圖，**檔案逐 byte 相同**：

```
3818D2DF6BFDC7AE1D8504E25D7DF6A09096162D35092E39FAD82C61462A8FF2  shot_r5.png
3818D2DF6BFDC7AE1D8504E25D7DF6A09096162D35092E39FAD82C61462A8FF2  shot_r5b.png
```

`PrintWindow` 回傳 True、尺寸 631x431 正確，但內容是**過期的 backing store**。
狀態列顯示 `H`（HiRes）+ `A`（80col）— 這證明 `hgr_init` 的 HIRES 生效 —
但畫面內容無法作為「有沒有畫上去」的判準。
**結論：AppleWin 截圖只能證明 soft-switch 狀態，不能證明畫面內容。
離線 emu（`tools/a2_emu.py`）才是可用的畫面觀測管道。**

### 24.3 讓 title 完全不碰磁碟，並修掉 art 佈局

* `HELLO` 預載 `TITLEH,A$1000`（2,059 B → 結束 `$180A`）、`CREDITSH,A$1900`（1,230 B → 結束 `$1DCD`）。
  **兩者都不碰 `$2000`**（COLD staging / HGR 頁）。
* `LSTBUF` 由 `$1B00` 搬到 `$1F00`，避開 `DOSBUF $1E40`。
* `GAMEOVERH`/`WELLDONEH` 維持 RWTS 逐檔載入（索引 28/29）。
* `neslib_init()` 直接 `hgr_draw_screen($1000)` 畫 title — **零磁碟存取**。
* 重建 `RESULT: OK`，`game.bin = 12,649`，`TITLEH load $1000`、`CREDITSH load $1900` ✓。

### 24.4 癥狀收斂：**只畫出一列 40 bytes**

emu 渲染 `$2000-$3FFF`：

```
HGR page $2000-$3FFF nonzero bytes: 40 of 8192
```

畫面是**一條綠色虛線**（一個 40-byte 的 scanline 列）。
指令歷史顯示 `hgr_draw_screen` 的 literal/run 迴圈**確實在跑**
（`61A8:20 / 61BD:85 / 61C1:91 / 61C5:D0 / 61C9:C6 / 61CB:D0 / 61D6:60 / 61AB:CA / 61AC:D0`），
然後 `8721:20 -> 8AFD:4C -> $D093`（mb_init）✓。

**離線用文件記錄的 tag-RLE 規則解 `titleh.bin`：不終止，200 步就發出 1,643 bytes。**
流頭是 `05 00 05 FF 00 05 50 10 00 05 1F 08 00 05 12 02 00 05 19 01 00 05 92 04`
（tag=`$05`，`05 FF` = 255 個 `$00`，`05 50` = 80 個…）。
**n 在開頭絕不為 0，所以解碼器「不該」終止。**

→ **下一輪目標：反組譯目前版本的 `hgr_draw_screen`（位址已隨重建位移），找出它為何在約 40 bytes 後就走到 `CMP #$00 / BEQ done`。**
重點檢查：`row_cnt` 初值、`arg_y` 與 `line_addr` 的互動、以及 run 長度 `TAX/DEX/BNE` 跨越 `row_cnt` 邊界時的行為。

### 24.5 也確認的事實

* `page_hit` 觀測（PC 進入 `$2000-$3FFF` 當程式碼執行）**從未觸發** →
  上輪看到的 `$3ED1` 不是 BRK 推進去的，而是**棧上多了一個位元組**（BRK 推 3 bytes 造成位元位移）
  → 這是 emu **未 seed ROM 向量**（`$FFFE/$FFFF` 讀成 0）造成的假象，不是產品 bug。
  **emu 需要 seed 向量才能追過需要 ROM/DOS 服務的路徑。**

### 24.6 更正：我上面的反組譯位移了 4 bytes（我的錯）

我用 \ase=\ 從 \\ 開始 dump，但 \.map\ 顯示 \_hgr_draw_screen = \。
**所以「JSR 指向 JMP / JMP 指向 JSR 的 operand」是我自己的位移錯誤，不是產品的 label bug。**
由 \_hgr_draw_screen = \ 重新對齊後，\jsr next_byte / jsr put_byte / jmp @loop\ 都落在正確位置。
**教訓：反組譯前一定先從 \.map\ 取符號位址，不要用假設的 routine 起點。**

真正的觀測癥狀仍然成立：**HGR 頁只有 40 bytes 非零 = 只畫出一個 40-byte 的 scanline 列**，
而 \	itleh.bin\ 離線解碼（tag=\）在 200 步內發出 1,643 bytes 且不終止。
下一輪：在 emu 裡於解碼器走到 \CMP #\ / BEQ done\ 的那一刻，記錄
\src_ptr / dst_ptr / row_cnt / arg_y / 已發出 bytes\，直接看它為何提前終止。

---

## 25. 本輪（goal round 6）：**畫面終於正確生出來了** — 根因是 `line_addr` 被傳了錯的 A

### 25.1 定位過程（全部可重現）

1. **離線解碼 `titleh.bin`**（文件記錄的 tag-RLE 規則）：
   `emitted 7680, nonzero 1164` — **檔案本身是好的**。
2. **emu 的 HGR 頁**：`nonzero bytes: 40 of 8192` — **畫出來的只有 40 bytes**。
   → 資料對、輸出對，**寫入位置錯**。
3. **加「依 256-byte 頁統計寫入」**：

   ```
   $2200-$22FF  7896 writes      <-- 全部 7,680 個畫點都落在同一頁
   $2000-$20FF   296 writes
   ```

   **整個畫面只寫進 `$2200` 那一頁。**
4. **`--probe` 記錄解碼器狀態**：`row_cnt` 正常遞減、`dst` 逐 byte 前進、
   `arg_y` 恒為 `$00` → 行切換發生在 `row_cnt=0`。
5. **讀 `put_byte` 原始碼**：

   ```asm
   @1: dec row_cnt
       bne @2
       lda #$28
       sta row_cnt
       inc arg_y
       jsr line_addr        ; <-- A 這時是 $28，不是 arg_y！
   @2: rts
   ```

   **`line_addr` 的契約是「A = scanline 編號」**（`asl a / tay / bcs @hi / lda hgr_line_off,y`）。
   **呼叫時 A 還留著 row_cnt 的重載值 `$28` = 40 → 192 行全部選到 scanline 40**
   （`y=40` → `$2000 + 5*$80 = $2280` → 正好是觀測到的 `$2200` 頁 ✓）。

### 25.2 修法與驗證

`src/a2/hgr.s` 的 `put_byte`：`inc arg_y` 之後、`jsr line_addr` 之前，**`lda arg_y`**。

**重建後實測：**

| 項目 | 修前 | 修後 |
|---|---|---|
| 寫入分佈 | `$2200` 一頁 7,896 次 | 每頁 496 次，均勻覆蓋 `$2100..$2A00` ✓ |
| HGR 頁非零 bytes | **40 / 8,192** | **5,113 / 8,192** ✓ |
| 離線解碼非零 | 1,164（基準） | — |

**`tools/a2_emu.py` 渲染 `$2000-$3FFF` 成 280x192 PNG：畫面清楚顯示大字「ALTER EGO」與下方「PRESS START」。**
**這是本專案第一次看到遊戲圖形正確成像。**

（非零 5,113 > 離線 1,164，因為 HGR 的綠色像素由多個 byte 值構成、且 `hgr_clear` 之後頁面含 art 的全部非零 byte；
重點判準是「均勻覆蓋 192 行 + 文字可讀」，兩者都成立。）

### 25.3 本輪新增的觀測工具（`tools/a2_emu.py`）

* `--probe ADDR[,ADDR...]`：PC 命中該位址時印出 `dst / cur / src / row_cnt / arg_y / tag / last / A / X`。
  **這是抓到 `line_addr` 契約錯誤的關鍵工具。**
* **依 256-byte 頁統計寫入**（`PAGEWR`）：直接看出「寫入全擠在同一頁」這種空間性錯誤。
  之前的 `nonzero bytes` 計數只能看出「有沒有畫」，看不出「畫到哪」。

### 25.4 教訓（要記住的規則）

**呼叫一個以 A 為參數的副程式之前，必須顯式把參數放進 A。**
`inc arg_y` 不影響 A；前面 `lda #$28` 的 A 會一路留到 `jsr`。
這類 bug 的指紋是「輸出資料正確、寫入位置全部擠在同一個 256-byte 頁」。

### 25.5 尚未完成（目標維持進行中）

* **關卡串流**：`lv_load`/`lv_load_art` 走 RWTS，emu 不模擬 RWTS → 需在 AppleWin 實機路徑驗證。
* **Mockingboard 發聲**：本機無音效裝置，無法聽證。
* **emu 的 `$D131 RTS -> $25D1`**：仍是 emu **未 seed ROM 向量**（`$FFFE/$FFFF` 讀成 0）造成的
  棧位元位移假象（`page_hit` 從未觸發已證明頁面沒被當程式執行）。
  **emu 需要 seed 向量才能追過需要 ROM/DOS 服務的路徑。**
* AppleWin 截圖通道**無法偵測變化**（§24.2），所以實機畫面驗證需要另找管道。

---

## 26. 本輪（goal round 7）：emu 補上 RWTS 與 LC 寫入路由；找到「棧位移 1 byte」的指紋

### 26.1 `tools/a2_emu.py` 新增兩項能力

1. **RWTS 服務**：`serve_rwts()` 攔截 `PC == $0100`（DOS 的 page-zero 跳板），讀
   `RVSLT=$B8 / RVDRV=$B9 / RVBUF=$BA / RVTRK=$BD / RVSEC=$BE / RVCALL=$BF`，
   以 `track*16*256 + sector*256`（與 `tools/a2_tsmap.py` 同一映射）從**真正的 `.dsk`**
   取 256 bytes 寫進 `RVBUF`，設 `RVSECN`、`RVERR=$0000`，然後按呼叫者 JSR 推的返回位址返回。
   **關卡串流與 art 串流終於可以在離線 emu 裡跑。**
   實測：`RWTS calls served from the disk image: 0` — **程式在抵達 RWTS 之前就楔住了。**
2. **RTI handler**：`$FFFE/$FFFF` 與 `$FFFC/$FFFD` 原本指向未 seed 的 `$F000`（全 0 = BRK），
   造成 `BRK -> $0000 -> BRK` 每次推 3 bytes 的迴圈。
   **在 `$F000` 放 `RTI`（$40）** →  stray BRK 的行為與真實 //e 在 Monitor 下一致（返回 BRK 的下一條）。

### 26.2 修掉 emu 的 LC 寫入路由錯誤

`wr()` 原本把 `$D000-$DFFF` 的寫入 **gate 在 `st["rom"]` 上**（ROM read 開著就丟掉寫入）。
**真實 //e：ROM 唯讀，寫入一律進 LC RAM。** 已改為「依 bank 直接寫 MAIN/AUX，與 rom 狀態無關」。

### 26.3 「棧位移 1 byte」的指紋（已量化，尚未收掉）

```
FIRST ESCAPE: PC=$D131 op=$60 (RTS) -> $25D1
   SP=$FA  stack at $0100+SP: 25 87 c1 7e 3b 60
```

棧上 `$1FA/$1FB = 25 87` → **$8725，正是 `JSR $8723`（`_mb_init` stub 的 JSR）的返回位址**。
**但它落在 SP+2/SP+3，比正確位置深了 1 byte。**
RTS 因此 pop 到 `$1F9=$D1`（lo）與 `$1FA=$25`（hi）→ **$25D1**。

**$25D1 的來源可完全對上一次 BRK：BRK 在 `$25CF` 執行（HGR 頁全 0），推 `PC+2 = $25D1` 與 `P`，共 3 bytes（奇數）。**
**一次奇數位元組的推入，會讓之後每一次 RTS 都回傳 byte-swapped 的垃圾 — 這正是觀測到的形態。**

候選（奇數推入）：`PHA` 沒有對應 `PLA`，或 BRK。
`mb_init` 內部 `$D10D` 的 `PHA/PLA` 平衡 ✓；呼叫鏈 `8723:20 -> 8AFF:4C -> $D093` 平衡 ✓。
**下一輪：在 COLD stub 與 C 端呼叫鏈中找出那一次「多出來的 1 byte 推入」。**

### 26.4 本輪也確認的事

* **`lv_assets()` 的複製迴圈是正確的**（反組譯自 `_lv_assets = $88F8`）：
  `LDA $C083`（讀取即斷言 LC bank2）→ `cold_src=$2000`、`cold_dst=$D000`、`LDX #$0A`（10 頁 = 2,560 B）。
  **watch 實測每一次寫入都 byte-exact**：
  `PC=$8911 -> $D000=$A2, $D001=$D0, $D002=$A0, $D003=$00, $D004=$88, $D005=$D0, $D006=$FD, $D007=$CA`
  （正是 `cold.bin` 的頭 8 bytes）。
* **`--probe` 印出 soft-switch 狀態後**才看出：`$88F8` 命中時 `lc_bank=1 rom=True`（在 `lda $C083` 執行**之前**），
  進入複製迴圈時已是 `lc_bank=2 rom=False` ✓。
* **`COLD copy check: 84/2457` 與寫入日誌互相矛盾** → 該檢查是 emu 端的診斷產物，
  **不是產品 bug**：程式確實從 `$D093` 執行真實程式碼（指令歷史可證），
  代表 COLD image 在執行期間確實生效。已把檢查改為走 `rd()`（與 CPU 同一路由）。
* **畫面仍然正確**：`HGR page nonzero = 3,192 / 8,192`，寫入均勻分佈在 `$2000/$2400/$2800/$2C00/$3000/$3400`
  各 9,880 次（title 被重複重畫 = 進入主迴圈的跡象）。

### 26.5 教訓

* **反組譯前必從 `.map` 取符號位址**（本輪又踩一次：`_lv_assets` 是 `$88F8`，我從 `$88CC` dump，位移 4 bytes）。
* **模擬器的記憶體路由必須照硬體語意**：ROM 唯讀 ≠ 寫入被丟棄。
* **診斷工具之間要互相一致**：寫入日誌與檢查必須走同一條路由，否則會得出互相矛盾的結論而浪費輪次。

---

## 27. 本輪（goal round 8）：**根因是 emu 的 `PLA` 實作** — 程式第一次跑完整條路徑並乾淨退出回 DOS

### 27.1 根因（一條指令）

`tools/a2_emu.py` 的 `PLA` 把 **A 與 P 都 pop**：

```python
elif op == 0x68:
    self.a = self.pop()
    self.p = (self.p & ~0x30) | (self.pop() & 0x30)   # <-- 多 pop 了 1 byte
```

**`PLA` 只 pop A。** 我把它寫成 `PLA + PLP`。

**用「記錄 `$D093-$D131` 之間每一次棧深度變化」直接點名：**

```
PC=$D122 op=$48 (PHA)  depth 8 -> 9     ✓ +1
PC=$D130 op=$68 (PLA)  depth 9 -> 7     ✗ -2   <-- PLA 吞了 2 bytes
PC=$D131 op=$60 (RTS)  depth 7 -> 5     ✓ -2
```

**一個平衡的 `PHA/PLA` 對因此每輪洩 1 byte → 之後每一次 RTS 回傳 byte-swapped 位址
→ `$D131` 的 RTS 回傳 `$25D1`（落在 HGR 頁）→ 執行 `$00` = BRK → 推 3 bytes → 恶性循環。**

**修完 `PLA`（只 pop A，N/Z 由 A 設定）後，一次就跑通。**

### 27.2 修後的量化結果（第一次程式跑完整條路徑）

```
steps: 503165  reached DOSWARM $03D0 (program exited)
COLD copy check: 2457/2457 bytes match, 0 differ
RWTS calls served from the disk image: 1
FIRST EXECUTION OF THE HGR PAGE:   （不再出現 — 頁面沒被當程式執行）
FIRST RTS AT ODD STACK DEPTH:      PC=$8DAB depth=9
```

* **`reached DOSWARM $03D0`** — **BRUN 契約走通：程式自己退出並交回 DOS。**
* **`COLD copy check: 2457/2457, 0 differ`** — 把檢查改成走 `rd()`（與 CPU 同一路由）後，
  與寫入日誌一致 ✓（上輪的 84/2457 是 emu 診斷產物，已證實）。
* **`RWTS calls served from the disk image: 1`** — **程式真的呼叫 RWTS，並從磁片取到真實磁區資料。**
  上上輪加的 `serve_rwts()` 生效。
* **寫入分佈**：`$2000/$2100/$2200/$2300/$2400/$2500…` 各 **752 次** = 均勻覆蓋整頁 ✓。

### 27.3 本輪也修掉的 emu 錯誤（都是「模擬器不照硬體語意」）

| 錯誤 | 實測後果 |
|---|---|
| `PLA` pop 了 A 與 P | 每輪洩 1 byte → RTS byte-swapped → 跳進 HGR 頁（**本輪主根因**）|
| `RTI` = `pc = rd16($FFFA)`，**完全不 pop** | 每次 BRK 洩 3 bytes，且跳去 `$6000` **重啟程式** |
| `$42` 被當成「跳 `$FFFE`」 | 6502 上 `$42` 是 1-byte NOP |
| 未實作的 opcode 直接 `SystemExit` | 追進 HGR 頁的追蹤會中斷 → 改成 6502 NOP 集合 + 1-byte NOP 計數 |
| `$D000-$DFFF` 寫入 gate 在 `st["rom"]` | 真實 //e：ROM 唯讀，寫入一律進 LC RAM |

### 27.4 新增觀測工具

* **`FIRST ODD STACK DEPTH`** — 第一次深度變奇的指令。
* **`FIRST RTS AT ODD STACK DEPTH`** — 第一次在奇數深度執行的 RTS（`PHA/PLA` 的暫時奇數會自動排除）。
* **`$D093-$D131` 之間的棧深度變化日誌** — **直接點名兇手的那個工具。**
* `--probe` 現在也印 `depth / SP / cold_src / cold_dst / lc_bank / rom`。
  **實測各 init 入口深度全部為偶數且平衡**：`main=2 → neslib_init=4 → lv_assets=6 →
  hgr_init=6 → hgr_set_tiles=6 → hgr_clear=6 → hgr_draw_screen=6 → mb_init=6 → 回到 main=2` ✓。

### 27.5 下一個 bug（已定位，尚未修）

**程式把 `$00` 寫進自己的程式碼。** 指令歷史尾端：

```
62A3:91 62A5:C8 62A6:D0   （STA (ptr),y / INY / BNE 的填充迴圈，重複數百次）
...
62A3:00                    <-- $62A3 原本是 $91，現在是 $00
```

**寫入統計顯示 `$9A00-$9AFF` 4,100 次、`$9B00-$9BFF` 4,422 次** —
**一個 store 從程式區高處往回走，把 `$00` 一路蓋到 `$62A3`（程式自己的碼）。**
候選：`vram_zero` / 填充迴圈的指標起點或方向錯。
**判準：寫入起點應在 `$1800-$1F7F`（VRAM）或 `$2000-$3FFF`（HGR），不該在 `$6000-$9BFF`（程式區）。**

### 27.6 教訓

* **模擬器的每一條指令都要照硬體語意核對**：`PLA` 只 pop A、`RTI` pop 3、`$42` 是 NOP。
  **一條 `PLA` 多 pop 1 byte，就足以讓整支程式看起來「跳進圖形頁」，把調查帶走整整三輪。**
* **棧深度是可直接量測的不变量**：JSR/RTS 成對 ⇒ 深度恒為偶。
  把「深度變化」印出來，比追指令流快得多。

---

## 28. 本輪（goal round 9）：**根因是 cc65 呼叫慣例 `__cdecl__` vs `__fastcall__`** — 程式把 `$00` 蓋進自己的程式碼

### 28.1 定位過程（全部可重現）

1. **把 watch 範圍收到「程式區」** `$6000-$9BFF` → 點名 `PC=$8E1B` 寫 `$00` 於 `$916B` 起。
   **查 `.map`：`$8E1B` 在 `zerobss` 內、`$916B` 是 BSS** → **合法**，不是 bug。
2. **把範圍收到「程式碼區」** `$6000-$8FFF` → 點名真兇：

   ```
   PC=$62A3  400 writes
   PC=$62A3 -> $6000 = $00 | dst=$004C cur=$6000 src=$180B
   PC=$62A3 -> $6001 = $00
   ...
   ```

   **`cur_ptr = $6000` = 程式自己的進入點。**
3. **查 `.map`：`_vram_zero = $629A`**，其碼是

   ```asm
   vram_zero: sta cur_ptr / stx cur_ptr+1   ; 指標由 A/X 傳入
              lda #$00 / tax
   @page:     ldy #$00
   @b:        sta (cur_ptr),y / iny / bne @b
              inc cur_ptr+1 / dex / bne @page
              rts
   ```

### 28.2 根因

`src/a2/vram.s` 的 `vram_zero` 是**組合語言**實作，**從 A/X 讀指標**（cc65 的 `__fastcall__` 慣例）。
`src/a2/neslib.c` 卻宣告成

```c
extern void vram_zero(void *dst);      /* 沒有 __fastcall__ */
```

**cc65 對沒有 `__fastcall__` 的函式用 `__cdecl__`：引數被 push 到 C stack，A/X 是呼叫後留下的垃圾。**
**實測垃圾 = `$6000` → 把 2,048 個 `$00` 從程式進入點一路蓋下去。**

**之前「title 畫得對」是僥倖：`hgr_draw_screen((const void *)0x1000)` 傳的是常數，cc65 剛好把 `$00/$10` 放進 A/X（probe 實測 `A=$00 X=$10` ✓）。傳變數位址（`vram`）時就拿到垃圾。**

### 28.3 修法（一整類 bug）

`__fastcall__` 補滿所有「asm 實作且讀 A/X」的 extern（**neslib.c 11 條 + game.c 2 條**）：
`hgr_set_tiles / hgr_draw_screen / hgr_set_row / hgr_put8 / spr_set_buf / spr_set_slot /
spr_setup / spr_save_draw / ftm_play / ftm_pause / sfx_start / lv_load_art`。

**重建 `RESULT: OK`，`game.bin = 12,651`。**

### 28.4 修後實測（比上輪更乾淨）

```
steps: 503165  reached DOSWARM $03D0 (program exited)
COLD copy check: 2457/2457 bytes match, 0 differ
RWTS calls served from the disk image: 1
writes into the program image:        （不再出現 ✓ 自我覆蓋消失）
FIRST EXECUTION OF THE HGR PAGE:      （不再出現 ✓）
```

**自我覆蓋消失、頁面沒被當程式執行、程式跑完整條路徑並交回 DOS。**

### 28.5 本輪新增：鍵盤注入

`--key 0x0D`：`rd($C000)` 回 `0x80 | code`（bit7 = strobe），寫 `$C000`（KEYRESET）清掉 — 照 //e 鍵盤語意。
**動機：不注入按鍵時 `main()` 畫完 title 就找不到按鍵而返回 DOS。**
**實測注入 `$0D` 後仍是 `hgr_draw_screen` 1 次、`_lv_load`/`_lv_load_art` 0 次、RWTS 1 次、`reached DOSWARM`。**
→ **title 之後的遊戲迴圈尚未被觸發；下一輪要查 `_input_poll`/`_input_last_key`（cold stub `$D01A`/`$D08C`）有沒有把注入的按鍵讀進去，以及 `main()` 的 title 迴圈離開條件。**

### 28.6 教訓（要記住）

**cc65 預設是 `__cdecl__`。任何用組合語言實作、從 A/X 讀引數的副程式，C 端宣告必須寫 `__fastcall__`。**
指紋：**傳常數時剛好對、傳變数位址時拿到垃圾 → 把記憶體（含程式碼）填成 0。**
**查 `.map` 把「寫入位址」對應到「符號」是分辨「合法 BSS 清零」與「自我覆蓋」的關鍵一步** —
本輪若沒做這一步，會去修 `zerobss` 這個無辜的程式。

---

## 29. 本輪（goal round 10）：**根因是編譯器的 tail-jump 用在「非最後一次」呼叫** — `pal_clear` 讓 `credits_screen()` 中途被丟棄

### 29.1 定位過程（逐條指令收斂）

用 `--probe` 沿 `credits_screen` 逐條探（`$6564` 入口 → `$8024` ppu_off → `$6567` → `$7FDB` pal_clear → `$656A`）：

```
$6564 hit 1   credits_screen 入口          ✓
$8024 hit 2   ppu_off                      ✓ 返回
$6567 hit 3   pal_clear 的呼叫點            ✓
$7FDB hit 4   pal_clear 入口               ✓
$656A         pal_clear 之後那條            ✗ 從未執行
```

**`pal_clear` 進去了、沒有回到它的下一條。**

### 29.2 根因（反組譯 `pal_clear = $7FDB`）

```
7FDB: A9 B8 A2 94   LDA #$B8 / LDX #$94    ; &pal_bg_v
7FE0: 20 33 8E      JSR pushax
7FE3: A9 00 20 02 8D  LDA #$00 / JSR ...   ; v=0, n=16
7FE8: AA TAX / A9 10 LDA #$10
7FEB: 4C 91 84      JMP $8491              ; <-- tail jump 進 fill_mem
7FEE: A9 D8 A2 94   ...pal_spr_v...
7FFB: 4C 91 84      JMP $8491
7FFE: 60            RTS
```

**`JMP`（tail jump）不推返回位址。**
**所以第一次 `fill_mem` 的 `RTS` pop 的是 `pal_clear` 的「呼叫者」的返回位址。**
**→ `pal_clear` 填完一次就返回，而且把 `credits_screen()` 的返回位址吃掉 →
`credits_screen()` 中途被丟棄 → `main()` 後面的 `title_screen()` 永遠到不了。**

**判別要點：tail-jump 最佳化只在「呼叫是函式最後一個動作」時合法。這裡用在第一個呼叫上。**

### 29.3 修法

`src/a2/neslib.c` 的 `pal_clear()` 改成**明確迴圈**，不再呼叫 helper：

```c
uint8_t *d; uint16_t i;
for (d = pal_bg_v,  i = 16; i; --i) *d++ = 0;
for (d = pal_spr_v, i = 16; i; --i) *d++ = 0;
```

**重建 `RESULT: OK`。**

### 29.4 修後實測（程式不再退出，進入遊戲迴圈）

| 項目 | 修前 | 修後 |
|---|---|---|
| `hgr_draw_screen` 呼叫次數 | **1**（只有 neslib_init 的 title） | **2** ✓（title + credits） |
| 結束方式 | `reached DOSWARM $03D0`（`main()` 提早返回） | **`ran out of steps`（跑在 `while(1)` 遊戲迴圈裡）** ✓ |
| `$656A`（pal_clear 下一條） | 從未執行 | 執行 ✓ |

**`_lv_load` / `_lv_load_art` 仍是 0 次、`RWTS calls: 0`** →
**關卡載入尚未被觸發（title 迴圈之後的 `game_loop()` 路徑）。**

### 29.5 本輪也確認的事

* `main()` 反組譯正確：`JSR $870C`(neslib_init) → `JSR $6564`(credits_screen) → `JSR $6598`(title_screen) → `JSR $6C12`(game_loop) ✓
* `credits_screen` 反組譯正確：`art_screen(credits)` = `LDA #$00 / LDX #$19 / JSR $617F` → **指標 `$1900` ✓**（上輪 `__fastcall__` 修好的證據）
* `titleh.bin` / `creditsh.bin` 離線解碼：**都正好發出 7,680 bytes 且有終止符**（`terminated=True, stream_consumed=全長`）→ **art 串流完全正確**
* `ppu_on_bg/ppu_off/pal_fade` 在 Apple 端是 trivial 空作，不是楔子

### 29.6 教訓

**cc65 的 tail-jump（`jmp` 取代 `jsr`）最佳化，只可用在函式的最後一個動作。**
**若一個 C 函式內有兩次呼叫同一个 helper，而編譯器對第一次用了 tail jump，第一次 helper 的 `rts` 就會吃掉呼叫者的返回位址。**
**指紋：函式「進去了、沒有回到它的下一條」，而且外層函式也跟著被丟棄。**
**逐條指令 `--probe` 是收斂這種問題最快的方法**（本輪 4 個探點就定位）。

---

## 30. 本輪（goal round 11）：**根因是 `vram_zero` 的頁面計數器 = 0** — 填了 64 KB 的 `$00`，一路蓋掉圖形頁、圖磚、音樂與程式本身

### 30.1 根因（一條指令）

`src/a2/vram.s`：

```asm
vram_zero:
	sta cur_ptr
	stx cur_ptr+1
	lda #$00
	tax                    ; <-- 註解寫「8 pages」，程式碼把計數器設成 0
@page:	ldy #$00
@b:	sta (cur_ptr),y / iny / bne @b
	inc cur_ptr+1
	dex
	bne @page            ; X=0 -> dex 繞回 $FF -> bne 恆真
	rts
```

**`lda #$00 / tax` 讓計數器 X = `$00`。`dex` 繞回 `$FF`，`bne` 恆真 → 迴圈跑 256 次 = 填 256 頁 = 64 KB。**
**從 `$1800` 開始，一路蓋掉 `$2000`（HGR 頁）、`$4000`（圖磚）、`$5000`（音樂）、`$6000`（程式自己）。**

**程式後來在 `$62A3` 執行到 `$00`（BRK）— 那就是被這個迴圈填成 0 的、自己的碼。**

### 30.2 定位過程（`cur_ptr` 寫入日誌直接點名）

新增「寫入 `cur_ptr`（`$7E/$7F`）＋ PC」的觀測：

```
[#33] PC=$60EA  $7F = $40   cur_ptr=$3F00     ; hgr_clear 走完 $2000-$3FFF ✓ 合法
[#34] PC=$629A  $7E = $00   cur_ptr=$4000     ; vram_zero 入口
[#35] PC=$629C  $7F = $18   cur_ptr=$4000     ; -> cur_ptr = $1800 ✓ 正確（上輪 __fastcall__ 修好的證據）
[#36..#43]  $7F = $19,$1A,...,$20  cur_ptr 走到 $2000   ; 8 頁 ✓ 正確
[#44..]     $7F = $21,$22,$23,...                        ; <-- 超過 8 頁，繼續蓋下去
```

**入口正確、前 8 頁正確、然後不停 → 計數器是 0。**

**判別要點：`sta cur_ptr / stx cur_ptr+1` 出現在日誌裡 → 表示 `__fastcall__` 修法生效；
剩下的問題是純計數器 bug，與呼叫慣例無關。**

### 30.3 修法

計數器改用 `ldx`，`A` 保持填值（A 不能同時當填值與位址高位元）：

```asm
	lda     #$00                     ; 填值，整個迴圈留在 A
	ldx     #$08                     ; 8 頁 x 256 = 2,048 >= 1,920
```

**重建 `RESULT: OK`，`game.bin = 12,686`。**

### 30.4 修後量化（圖形第一次穩定留在畫面上）

| 項目 | 修前 | 修後 |
|---|---|---|
| HGR 頁 `$2000-$3FFF` 非零位元組 | **0**（被填成 0） | **5,113 / 8,192** ✓ |
| `FIRST ESCAPE`（程式碼被蓋成 `$00` → BRK） | `PC=$62A3 op=$00 → $F000` | **不再出現** ✓ |
| 寫入程式碼區 `$6000-$8FFF` | 400+ 次 `$00` | **不再出現** ✓ |
| 執行結束 | `ran out of steps`（卡死） | `ran out of steps`（在遊戲迴圈裡跑，畫面穩定） |

**離線渲染 `build/a2/emu_round11.png`（280×192）：清楚顯示「ALTER EGO」大字與下方「PRESS START」✓**
**→ title 畫面在模擬器裡正確成像並持續存在（不再被自我覆蓋）。**

### 30.5 本輪也排除的假設（都是我用錯位址探到的）

* **`_ppu_waitnmi = $81FA`（不是 `$81AE`）**；`$81AE` 在 `_oam_meta_spr` 內。
  **`credits_screen` 的呼叫點是 `$6580`（不是 `$657F`）— 我又差一個位元組。**
  **`.map` 取符號位址、以及「JSR 的下一個位址 = JSR 位址 + 3」這條必須算，不能靠目測。**
* `ppu_waitnmi` 的反組譯正確：`JSR apply_vru / JSR ftm_tick / JMP tick_frame`
  （`tick_frame` 是最後一個呼叫 → tail jump 合法 ✓）。
* COLD `_ftm_tick`（`$D1B7`）的 4 通道迴圈有界 ✓；`$D569` 每條路徑都 `RTS` ✓。
* **模擬器沒有跳過任何 opcode**（`NOPSEEN` 空）→ 楔子不是模擬器缺指令。
* `neslib.h:78` 的 `ppu_waitnmi` 宣告正確（`__fastcall__`）。
* `vram_zero` 呼叫點 `LDA #$00 / LDX #$18 / JMP $629A` → **指標 `$1800` 正確**。

### 30.6 教訓

**「填值」與「迴圈計數器」是兩個不同的暫存器需求時，必須分開載入：`lda #value` + `ldx #count`。
`lda #0 / tax` 看起來像「設 8」的註解，其實是計數器 = 0，而 `dex/bne` 對 0 起始值是 256 次。**
**共享 zero-page 指標（`cur_ptr`）的例程，要觀測「誰在什麼時候把什麼值放進去」** —
本輪就是靠 `cur_ptr` 寫入日誌（PC + 當下 cur_ptr）一次點名。

### 30.7 尚未完成

`_lv_load` / `_lv_load_art` 仍 0 次、`RWTS calls: 0` →
**關卡/過關圖資的「隨需載入」路徑尚未被觸發**（title 之後的 `game_loop()`）。
**圖形（title）已驗證正確且穩定；遊戲迴圈與音訊仍待驗證。**

---

## 31. 本輪（goal round 12）：**楔子點名到確切指令 — FamiTone2 每格音樂處理在 `$D374-$D38E` 空轉**

### 31.1 本輪新增的決定性工具：`hottest PCs`（每個 PC 的執行次數）

**一次執行就點名空轉迴圈**（2,000,000 steps）：

```
PC=$D37A  57539 executions
PC=$D37C  57539
PC=$D37F  57539
PC=$D469  57539
PC=$D46C  57539
PC=$D46E  57539
PC=$D49C  57539
PC=$D382  57539
PC=$D384  57539
PC=$D387  57539
PC=$D49D  57539
PC=$D4A0  57539
```

**全部同一次數 = 同一個迴圈的迴圈體，跑了 57,539 輪。**

### 31.2 空轉迴圈的反組譯（COLD，base `$D000`）

```
D374: A9 00 85 EF     LDA #$00 / STA $EF        ; 通道計數器 = 0
D378: A2 00           LDX #$00
D37A: A9 00           LDA #$00
D37C: 8D 65 DA        STA $DA65                 ; 目前通道
D37F: 20 69 D4        JSR $D469                 ; 處理通道 0
D382: A9 02 8D 65 DA  STA $DA65 = 2             ; 通道 1
D385: 20 9D D4        JSR $D49D
D388: A9 04 8D 65 DA  STA $DA65 = 4
D38B: 20 D1 D4        JSR $D4D1
D38E: 20 FF ...       JSR ...
```

`$D469` 的內容：

```
D469: BD 2D DA  LDA $DA2D,X
D46C: 29 0F     AND #$0F
D46E: F0 2C     BEQ $D497        ; -> $D497: JMP $D44B ; $D49C: RTS
D471: 8D 69 DA  STA $DA69
D474: BD 2E DA  LDA $DA2E,X / STA $EC
D479: BD 2F DA  LDA $DA2F,X / AND #$07 / STA $ED
```

**這是 FamiTone2 每格（frame）對 3 個音道的處理，`$EF` 每輪被設回 0 → 沒有終止條件被走到。**

### 31.3 本輪也修好的模擬器語意（鍵盤 strobe）

`--key` 原本讓 `rd($C000)` **永遠回 bit7=1**。真實 //e：**第一次讀回 `0x80|code`，之後每次讀回 `code`（bit7=0），直到 KEYRESET。**
`input_poll()` 正是靠這個語意（讀 KBD 取樣、讀 KBDSTRB 確認）。
**已改成照硬體語意（`KEYSTROBE` 旗標）。**

### 31.4 本輪再次踩到的位址陷阱（第三次）

**重建後符號位址全部位移**（`game.bin` 12,651 → 12,686）：

| 符號 | 我沿用的舊值 | `.map` 實際值 |
|---|---|---|
| `_main` | `$7EBF` | **`$7EC0`** |
| `_neslib_init` | `$870C` | **`$8727`** |
| `_pad_trigger` | `$8204` | **`$8251`** |
| `_ppu_waitnmi` | `$81FA` | **`$81FB`** |
| `_ftm_tick` | `$8B25` | **`$8B26`** |
| `_lv_load` / `_lv_load_art` | `$880E/$881B` | **`$8829/$8836`** |

**用舊位址探測得到「main 從未進入」的假結論。**
**規則：每次重建後，先從 `.map` 重取全部符號位址，再探測。**

### 31.5 修好 vram_zero 後的狀態（沿用本輪驗證）

```
HGR page $2000-$3FFF nonzero bytes: 5113 of 8192      （title 穩定在畫面上）
FIRST ESCAPE: 不再出現
寫入程式碼區: 不再出現
main / neslib_init / hgr_draw_screen x2: 都有進入 ✓
pad_trigger / lv_load / lv_load_art: 0 次
RWTS calls: 0
```

**楔子鏈：`credits_screen` → `ppu_waitnmi` → `apply_vru` ✓返回 → `ftm_tick` → COLD `$D324` → `$D414` → 進入 `$D374` 空轉。**

### 31.6 下一步（已定好實驗）

**音樂在 Mockingboard 上無法在本機用聽的驗證（無音效裝置）。**
**決定性實驗：讓 `ftm_play` 不啟動音樂（或讓 `ftm_tick` 在未播放時直接 RTS），看遊戲迴圈是否就跑起來。**
* 若跑起來 → 楔子確定在 FamiTone2 的每格處理（音樂串流/計數器未推進），可單獨對付。
* 若仍卡住 → 楔子另有其處。

**判準：`pad_trigger`（`$8251`）出現命中、`_lv_load`（`$8829`）出現命中、`RWTS calls > 0`。**

### 31.7 本輪後段的關鍵翻案（同一輪內，繼續追）

**`--nomusic` 實驗（把 FamiTone2 的 `playing` 旗標 `$DA27` 每步壓 0）→ `hottest PCs` 清單變空 →
證明「空轉」確實發生在音樂處理路徑。**

**新增 `--key-every N`：重新裝填按鍵。**
**動機：`rd($C000)` 的 strobe 依真實語意第一次讀取後就清掉，title 需要 START 會一直等。**

**新增 `mixidx`（給 `ay_out` 的合併迴圈一個專屬計數器，不再共用 `chidx`）→ 重建後行為完全相同
（`57539` 次）→ **`chidx` 共用不是根因**。**

**逐條反組譯收斂到的事實：**

* `fade_screen_in`（`$62AE`）迴圈是**有界**的：`LDA $94A0`（全域 `i`）/ `CMP #$10` / `BCS` 離開 /
  `INC $94A0` ✓。`i = $94A0`。
* `pad_trigger`（`$8251`）是**真碼**：`JSR $8B14`（input_poll）✓。
* `ppu_waitnmi`（`$81FB`）的呼叫者共 15 處：`$62BE`（fade_screen_in）、`$62E9`（fade_screen_out）、
  `$6581`（credits 迴圈）、`$65DC`（title 迴圈）、`$66C3`、`$6839`、`$68E3`、`$6C1A`（game_loop）…
* **探測結果：`$62BE` 有命中、`$6581` 與 `$65DC` 都 0 命中。**
* `ftm_tick` 被呼叫約 **14,385 次**（57,539 ÷ 4 個音道）。
  `fade_screen_in` 每次呼叫 `ppu_waitnmi` 16 次 → **`fade_screen_in` 被呼叫約 900 次**。
  **`credits_screen` 的迴圈只有 150 次、`title_screen` 的迴圈會命中 `$65DC`。**
  **→ 程式是在「`game_loop` → `fade_screen_in` → … → `game_loop`」的循環裡，`game_loop` 有在跑。**

**所以下一輪的焦點很清楚：`game_loop` 有在跑，但 `_lv_load`（`$8829`）0 命中 →
`game_loop` 沒有走到關卡載入的呼叫。要查 `game_loop` 裡載入關卡的呼叫點與它的進入條件。**

### 31.8 本輪踩到的位址陷阱（第 3、4 次，要寫成規則）

**每次重建後 `.map` 的符號位址都會位移**（本輪 `_main $7EBF→$7EC0`、`_neslib_init $870C→$8727`、
`_pad_trigger $8204→$8251`、`_ppu_waitnmi $81FA→$81FB`、`_ftm_tick $8B25→$8B26`、
`_lv_load $880E→$8829`、`_lv_load_art $881B→$8836`）。

**用舊位址探測得到「main 從未進入」「pad_trigger 從未呼叫」的假結論。**

**規則（本輪起強制）：每次重建後，先用 `.map` 重取所有要探測的符號位址；
反組譯時「JSR 的下一條 = JSR 位址 + 3」要算，不能目測對齊。**

### 31.9 本輪新增的觀測工具（都有效，留用）

* **`hottest PCs`（每 PC 執行次數）** — 一次執行就點名空轉迴圈。**本輪最關鍵的工具。**
* **`--nomusic`** — 隔離音樂路徑的開關實驗。
* **`--key-every N`** — 重裝按鍵。
* **鍵盤 strobe 依真實 //e 語意**（第一次讀回 `0x80|code`，之後讀回 `code`，寫 `$C000` 清掉）。
* **`cur_ptr` 寫入日誌**（PC + 當下 cur_ptr）。
* **`NOPSEEN`** — 模擬器跳過的 opcode（本輪實測為空 → 楔子不是模擬器缺指令）。

---

## 32. 本輪（goal round 13）：**翻案 — 沒有楔子。是我的步驟預算小了約 500 倍**

### 32.1 結論先講

**前面十一輪找的「楔子」不存在。**
**`tick_frame()` 的延遲迴圈在真實 //e 上是正確的 60 Hz 校準；我的模擬器 `--max-steps` 數的是「指令數」，
不是「週期數」，所以 2,000,000 步只等於約 31 個畫面格。**
**`credits_screen` 一個就要 16（fade）+ 150（跑馬）= 166 格 → 需要約 1,060 萬條指令。**
**預算差了約 500 倍 → 程式永遠停在 `credits_screen` 的 `fade_screen_in` 裡面，看起來就像卡死。**

### 32.2 點名證據（`--watch-addr 0x94A0`，本輪新增的工具）

`fade_screen_in` 的迴圈計數器是全域 `i` = `$94A0`。**300,000 步內只有兩次寫入：**

```
PC=$8E3E  $94A0 <= $00      ; zerobss 清 BSS
PC=$62B4  $94A0 <= $00      ; fade_screen_in 的 i = 0
```

**`inc $94A0`（PC `$62D4`）完全沒出現 → 迴圈連一次都沒跑完 → 全部時間都在 `jsr $81FB` 裡面。**

### 32.3 算術（为什么這是正常的）

`sys.s:90` 的 `tick_frame`：

```
tick_frame:  ldx #$D0          ; 208 外圈
@outer:      ldy #$00
@inner:      dey
             bne @inner
             dex
             bne @outer
             rts
```

**原始註解的計算是對的：`208 × 1,284 + 207 × 5 + 6 = 268,111` 週期 ÷ 1.023 MHz = **16.7 ms = 59.9 Hz** ✓**

**內圈 `dey/bne` = 5 週期 × 256 次 = 1,280，加 `ldy` 2 + `bne` 不跳 2 = 1,284 ✓**

**模擬器數指令：內圈每圈 2 條指令 → 每格約 `208 × (1 + 256×2 + 2) ≈ 107,000 條指令`。**
**→ 2,000,000 步 ≈ 19–31 格（含 ftm_tick 的開銷）。**

**所以：真實硬體上遊戲是 60 fps 正常跑；是觀測預算不足。**

### 32.4 本輪也修好了一個真正的工具缺陷：`tools/a2_dis.py`

**前面每一輪的「位址差一」陷阱，根因是我用 8 位元組 dump 目測對齊。**
**本輪寫了線性掃描反組譯器，指令長度由 6502 的 opcode 家族表推導。**
**踩過的坑（全部修掉）：**

| 陷阱 | 說明 |
|---|---|
| `0x8D` = `STA abs` | 3 位元組。用算術家族的長度表會當成 2 → 從這裡開始全部錯位 |
| `0xA0` = `LDY #imm` | **2** 位元組（不是 `LDY abs`）；`0xAC` 才是 `LDY abs` |
| `0xC0`/`0xE0` | 同上：`CPY #`/`CPX #` = 2，`0xCC`/`0xEC` = 3 |
| `0x4C` = `JMP abs` | 在 0x40 家族 index 12，我原本填 0（視為无效）→ 報 INVALID |
| `0x68` = `PLA` | 1 位元組（我填了 3） |
| `0x0A/0x2A/0x4A/0x6A` | 隱式移位 = **1** 位元組（我填了 2） |
| `0x0C`/`0x2C` = `BIT` | 2 / 3 位元組 |

**修好後 `main`（`$7EC0`）與 `game_loop`（`$6C13`）反組譯完全對齊、零 INVALID，
且與 `game.c:907-916` 逐行吻合 ✓**

### 32.5 本輪用新反組譯器確認的事實（都是好消息）

* **`fade_screen_in`（`$62AF`）有界**：`i=0` → `cmp #$10` → `bcs $62DA` → `inc $94A0` → `jmp $62B7` ✓
* **`credits_screen`（`$6565`）有界**：`j=150` → `jsr $81FB` → `jsr $8251`（pad_trigger）→ `dec $94A1` → `beq $6596` ✓
* **`title_screen`（`$6599`）迴圈頂就是 `$65DC`**，`pad_trigger` 在 `$65FB` ✓
* **`game_loop`（`$6C13`）**：`jsr $81FB / $8071 / $7FDC / $8084` → **`jsr $8829` = `lv_load` 在 `$6C29`** ✓
* **`mb_init`（COLD `$D093`）有界**：3 組候選 AY 位址，`cpx #$03 / bne $D09C` ✓
* **`ftm_play`（COLD `$D132`）有界**：5 個音道 × 2 圈，`cpx #$32 / bne` ✓
* **`ay_out` 的合併迴圈計數器是 `$F0`（本輪新增的 `mixidx`）✓ 專屬，不與 `chidx`($EF) 共用**
* **`tick_frame`（COLD `$D000`）是有界延遲迴圈 + `rts` ✓**

**→ 前面所有「有界/無界」的判斷全部成立，程式邏輯沒有死鎖。**

### 32.6 下一輪的判準（預算正確後）

**`--max-steps 14,000,000`（約 130–220 格）應看到：**
* `$6581`（credits 迴圈）出現命中
* `$65DC`（title 迴圈）出現命中
* `$6C13`（game_loop）出現命中
* `$6C29` → `_lv_load`（`$8829`）出現命中
* **`RWTS calls served > 0`** ← 關卡從磁片串流進 `$1000` 的實證
* 渲染出**遊戲畫面**（不是 title）

**`--key-every` 要放大到約 400,000 步（≈ 4 格）以上，否則每格都在灌按鍵，title 的 `j=50` 倒數會被干擾。**

### 32.7 給後續輪次的硬規則（本輪定案）

1. **模擬器預算用「格」估算：1 格 ≈ 107,000 條指令。要看 N 格就給 `N × 110,000` 步。**
2. **每次重建後先從 `.map` 重取符號位址。**
3. **反組譯一律走 `tools/a2_dis.py`，不要再用 8 位元組 dump 目測對齊。**
4. **`--watch-addr` 是找「迴圈計數器被誰動過」的直接工具。**

---

## 33. 本輪（goal round 13，續）：**根因抓到 — 是模擬器的 `CLC`/`SEC` 反了**

### 33.1 根因（一行）

`tools/a2_emu.py` 的旗標指令實作是**反的**：

```python
elif op == 0x18:
    self.setc(True)      # 0x18 = CLC（清進位）→ 卻把進位 SET 了
elif op == 0x38:
    self.setc(False)     # 0x38 = SEC（設進位）→ 卻把進位 CLEAR 了
elif op == 0xD8:
    self.p &= ~0x04      # 0xD8 = CLD → 清的是 bit2（I），不是 bit3（D）
```

**已修：**

```python
elif op == 0x18:  self.setc(False)   # CLC
elif op == 0x38:  self.setc(True)    # SEC
elif op == 0xD8:  self.p &= ~0x08    # CLD  (bit 3)
elif op == 0xB8:  self.p &= ~0x40    # CLV  (bit 6)  ← 原本完全沒實作
elif op == 0x58:  self.p &= ~0x04    # CLI
elif op == 0x78:  self.p |=  0x04    # SEI
```

### 33.2 為什麼這一個 bug 就足以讓遊戲「看起來卡死」

COLD `ay_out` 的合併迴圈（`sys.s`/`ftm.s` 的 `@sx`）：

```
D395: lda $F0        ; mixidx
D397: clc            ; ← 模擬器把進位 SET 了
D398: adc #$0F       ; 於是加 16，不是 15
D39A: sta $F0
D39C: tax
D39D: cmp #$3C       ; 60
D39F: bne $D37A
```

**計數器因此走 `0, 16, 32, 48, 64, 80, ... $F0, $00, 16, ...`，永遠不會等於 60 → 迴圈永不離開。**

**量測完全吻合：觀測到的計數器值是 `0x20, 0x60, 0xA0, 0xE0` = 32, 96, 160, 224 — 全部是 16 的倍數。**
**15 的倍數序列不可能產生這些值 ✓✓✓ 這是決定性證據。**

**`ay_out` 是 `ftm_tick` 的最後一步 → `ftm_tick` 永不返回 → `ppu_waitnmi` 永不返回 →
`fade_screen_in` 永不返回 → `credits_screen` 永不返回 → `title_screen` 永不返回 → `game_loop` 永不進入。**

**觀測到的全部症狀（`tick_frame` 0 命中、`$8201` 0 命中、`$94A0` 只寫兩次、
`_lv_load` 0 命中、RWTS 0 次）全部由這一個 bug 解釋 ✓**

### 33.3 本輪的追兇路徑（記錄方法，之後照做）

1. **`--watch-addr 0x94A0`** → 迴圈計數器只被寫兩次 → 時間全在 `jsr $81FB` 內。
2. **`tools/a2_dis.py`（本輪新寫的線性掃描反組譯器）** → 逐條讀出迴圈：
   `lda $F0 / clc / adc #$0F / sta $F0 / tax / cmp #$3C / bne $D37A`。
3. **`tools/a2_zpwriters.py`** → 證明 `$F0` 只有迴圈自己寫（排除共用變數假設）。
4. **觀測值全是 16 的倍數** → `adc #$0F` 多加了 1 → 進位旗標是髒的 → 查 `clc` → **抓到反了的 `CLC`**。

**關鍵心法：當「計數器的觀測值」與「程式碼能產生的序列」對不上時，
對不上的那個差值（這裡是 +1）就是旗標髒了，直接去查旗標指令的實作。**

### 33.4 本輪也推翻的兩個先前結論（要寫進紀錄，避免之後被誤導）

* **§32 說「沒有楔子，只是預算不足」— 部分錯。**
  預算確實小（1 格 ≈ 107,000 條指令，要看 N 格要給 `N × 110,000` 步），
  **但楔子確實存在**，就是上面的 `CLC`。`tick_frame` 在真實硬體上的 60 Hz 校準是對的。
* **§31 說「`chidx` 共用不是根因」— 對。** 新增 `mixidx` 後行為不變，因為根因在旗標，不在共用。

### 33.5 本輪新增/修好的工具（都留用）

| 工具 | 用途 |
|---|---|
| `tools/a2_dis.py` | 線性掃描反組譯器，指令長度由 6502 家族表推導。**终结「位址差一」陷阱** |
| `tools/a2_zpwriters.py` | 找出「誰寫了這個零頁位元組」，含零頁 / 索引 / 絕對三種編碼 |
| `tools/a2_callsites.py` | 列出「誰呼叫這個位址」（jsr/jmp 全部呼叫點） |
| `--watch-addr A,B,...` | 記錄對指定位址的每次寫入（含 PC） |
| `hottest PCs` | 一次執行點名熱點迴圈 |
| `--nomusic` / `--key-every` | 隔離音樂路徑 / 重裝按鍵 |

**`a2_dis.py` 修掉的長度表錯誤（每一條都會讓掃描從那裡開始錯位）：
`0x8D` STA abs=3、`0xA0` LDY imm=2（`0xAC` 才是 LDY abs）、`0xC0`/`0xE0` 同理、
`0x4C` JMP abs=3、`0x68` PLA=1、`0x0A/0x2A/0x4A/0x6A`=1、`0x0C`/`0x2C` BIT=2/3。**

### 33.6 判準（修好 CLC 後應看到）

* `$6581`（credits 迴圈）、`$65DC`（title 迴圈）出現命中
* `$6C13`（game_loop）與 `$6C29` → `_lv_load`（`$8829`）出現命中
* **`RWTS calls served > 0`** ← 關卡由磁片串流進 `$1000` 的實證
* `tick_frame`（`$D004`）出現命中
* 渲染出**遊戲畫面**

---

## 34. 本輪（goal round 13，再續）：**CLC 修好後遊戲真的開始跑畫面格；同時抓到下一個真 bug — 畫面的 RLE 寫入會衝出 HGR 頁、打爛 COLD 影像**

### 34.1 CLC 修好後的實測（決定性進步）

```
probe $6581 hit  1: depth=4 SP=$F9      ; credits_screen 迴圈有在跑 ✓
probe $8251 hit  2: depth=6 SP=$F9      ; pad_trigger 有在跑 ✓
  step 4000000  PC=$D004  A=$04 X=$5C   ; tick_frame 的延遲迴圈 = 畫面格在走 ✓
  step 8000000  PC=$D005  A=$04 X=$42
  step 14000000 PC=$D004  A=$04 X=$83
```

**`credits_screen` 的 150 格倒數、`pad_trigger` 的鍵盤輪詢、`tick_frame` 的校準延遲全部在跑 ✓**
**堆疊深度都是偶數（4/6）✓ 沒有 RTS 位址交換的問題。**

**1 格 ≈ 107,000 條指令 → 14,000,000 步 ≈ 130 格。`credits_screen` 一個就要 166 格。**
**所以加了 `--fast-tick`（把 `tick_frame` 內圈剪短，格數不變、只省掉每格的週期開銷）才能看到後面的流程。**

### 34.2 `--fast-tick` 立刻抓到的真 bug（本輪最重要發現）

```
FIRST ESCAPE from the program: PC=$D1B7 executed op=$00 and landed at $F000
COLD copy check: 2210/2457 bytes match, 247 differ      ← COLD 影像被改壞了
```

**`--watch-addr 0xD1B6,0xD1B7,0xD1B8` 直接點名兇手：**

```
PC=$892C  $D1B7 <= $CE     ; lv_assets 把 cold.bin 正確放進 $D000（DEC $DA26）✓
PC=$61C1  $D1B7 <= $00     ; ← 之後被清零
PC=$61C1  $D1B7 <= $3E
PC=$61C1  $D1B8 <= $FF
```

**`$61C1` 是 `hgr_draw_screen` 裡的 `sta ($7C),y`（寫畫面位址 = `dst_ptr`）。**
**`$D1B6 - $2000 = $B1B6 = 45,494` → 解壓器吐了 45 KB，遠超過 HGR 頁的 7,680 位元組，**
**一路寫進語言卡的 COLD 影像（`$D000-$DFFF`），把 `ftm_tick`（`$D1B7`）的程式碼蓋掉 → 執行到 `$00`（BRK）→ 掉到 `$F000`。**

### 34.3 已排除的假設（都有證據）

* **磁片上的 RLE 串流是對的**（本輪新工具 `tools/a2_rle_check.py` 重跑）：
  `titleh.bin` 2,059 B → **吐 7,680、terminator 找到、串流正好用完** ✓
  `creditsh.bin` 1,230 B → **吐 7,680、terminator 找到、串流正好用完** ✓
* **`hgr_draw_screen` 的反組譯逐條核對，終止條件存在且正確**：
  `$6194: cmp $85`（b vs tag）→ `$619E: jsr get / cmp #$00 / beq $61B1 (rts)` ✓
* **`zerobss` 清的是 `$94xx`（BSS），不是 `$1000`** → 畫面緩衝沒被清 ✓
* **`cold.bin` 檔內 offset `$1B7` = `CE 26 DA` = `DEC $DA26` ✓ 檔案是好的**（是執行期被蓋掉）

### 34.4 下一輪的焦點（已定好，不再猜）

**要查的是「哪一次 `hgr_draw_screen` 呼叫、用哪一個來源位址、吐了超過 7,680」。**
**做法：`--watch-addr` 盯 `dst_ptr`（`$7C/$7D`）與 `src_ptr`（`$80/$81`），
在 `$61C1` 命中時記錄兩者；當 `dst_ptr - $2000 > 7680` 就是越界的第一刻。**
**候選來源（`game.c`）：`credits = $1900`、`title = $1000`、`art_screen_disk(i)` → `$1000`（由 RWTS 載入）。**
**`RWTS calls: 0` → 目前所有畫面都來自 BLOAD 進記憶體的 `TITLEH`/`CREDITSH`，不是串流載入的。**

**判準：`dst_ptr` 越界的第一次命中 + 當時的 `src_ptr` → 就能指出是哪個來源/哪一列開始跑掉。**

### 34.5 本輪定案的規則（加進 §32.7）

5. **`--fast-tick` 讓格數忠實、每格開銷變小**；要看幾百格就用它，真實硬體不受影響。
6. **`COLD copy check` 的「N/M bytes match」是 COLD 影像被破壞的偵測器** — 一旦 `differ > 0`，
   立刻用 `--watch-addr` 盯被改壞的位址點名兇手（本輪就是這樣抓到 `$61C1` 的越界寫入）。
7. **模擬器旗標指令要照 6502 定義：`CLC`=清進位、`SEC`=設進位、`CLD`=清 bit3、`CLV`=清 bit6。**
   **本輪的 12 輪「楔子」根因就是 `CLC`/`SEC` 反了。**

---

## 35. 本輪（goal round 14）：**抓到「畫面跑掉」的根因 — `vram_zero(vram)` 把 CREDITSH 清零了**

### 35.1 根因（位址重疊）

| 項目 | 位址 | 說明 |
|---|---|---|
| VRAM（NES 名稱表鏡像，1,920 B） | **`$1800-$1F7F`** | `cfg` 的 SCRATCH/VRAM |
| **CREDITSH 由 HELLO BLOAD 到** | **`$1900`**（1,230 B → 結尾 `$1DCD`） | **在 VRAM 範圍內** |
| TITLEH | `$1000`（2,059 B → 結尾 `$180A`） | 剛好擦到 VRAM 開頭 11 位元組 |

**`neslib_init()` 最後一行是 `vram_zero(vram)` → 把 `$1800-$1F7F` 全部填 `$00` →
在啟動時就把 CREDITSH 的 RLE 串流抹掉。**

**後果鏈（每一環都有量測）：**
`credits_screen()` 解壓 `$1900` 的全零 → 永遠遇不到 terminator → 吐超過 7,680 位元組 →
`dst_ptr` 線性走過 `$3FFF` 進入 `$4000/$5000/$6000/.../$D000` → **蓋掉語言卡的 COLD 影像** →
`ftm_tick`（`$D1B7`）的程式碼變成 `$00`（BRK）→ 掉到 `$F000`。

### 35.2 點名過程（本輪新工具 `--hgr-guard`，一次就抓到）

```
stores outside the HGR page $2000-$3FFF (the RLE writer ran past its terminator):
   PC=$61C1  wrote $004C   src_ptr=$1B77  dst_ptr=$004C
   PC=$61C1  wrote $004D   src_ptr=$1B78  dst_ptr=$004D
   ...
```

* `src_ptr = $1B77` = `$1900 + $277` → **正在解壓 CREDITSH** ✓
* `dst_ptr = $004C` → 高位元組已經從 `$20` 一路 `inc` 繞回 `$00` → **寫了 45 KB**

**`--watch-addr 0x7D` 對照：** `line_addr` 寫的高位元組是 `$20,$24,...$3C`（正確），
`put_byte` 的 `inc $7D` 讓它一路加到繞回 → 印證「越界是線性走位造成的」。

### 35.3 逐條反組譯排除的假設（全部有證據）

* **`hgr_line_off` 表內容正確**：`2000 2400 2800 2C00 3000 3400 3800 3C00 2080 ...`，
  scanline 8 = `$2080` ✓（`tools/a2_dis.py` 走 `line_addr`：`asl a / tay / bcs @hi /
  lda $898B,y / sta $7C / lda $898C,y / sta $7D / lda #$28 / sta $84 / rts`，
  `@hi` 走 `$8A8B,y` ✓ 進位就是索引高位 ✓）
* **`put_byte` 每 40 位元組會重新定位**：`dec $84 / bne rts / lda #$28 / sta $84 /
  inc $87 / lda $87 / jsr $6114 (line_addr)` ✓ 邏輯是對的
* **RLE 串流本身是好的**（`tools/a2_rle_check.py`）：`titleh.bin` 2,059 B → 吐 7,680、
  terminator 找到、串流正好用完；`creditsh.bin` 1,230 B → 同樣 ✓
* **`zerobss` 清的是 `$94xx`（BSS），不是 `$1000/$1900`** ✓

**→ 唯一能把 `$1900` 的內容在啟動時抹掉的，就是 `vram_zero(vram)`。**

### 35.4 修法（最小、有理由）

**`src/a2/neslib.c`：移除 `neslib_init()` 裡的 `vram_zero(vram)`。**
**理由：在 `__APPLE2ENH__` 路徑下 VRAM 一定是「先寫後讀」** —
`vram_read(map, 0x20c0, MAP_WDT*MAP_HGT)` 會填它，NES 名稱表的填充程式碼在 //e 下被 `#ifndef` 編譯掉，
所以沒有任何地方需要預先清零。
**`src/game.c` 的 `credits` 維持 `$1900`（附註解說明這次量測）。**

**（先試過把 credits 改到 `$1000`：不可行 — TITLEH 2,059 B 已經佔 `$1000-$180A`，
兩塊畫面資料在啟動時同時需要，會互相蓋掉。）**

### 35.5 重建結果

* `game.bin = 12,679` bytes（視窗 13,824）
* 磁片 `RESULT: OK`，35 個目錄項目，全部檔案 read-back byte-exact
* 編譯警告僅剩既有的三條 pointer signedness 與 `sp` deprecated，
  加一條 `fill_mem defined but never used`（vram_zero 移除後正常）

### 35.6 本輪新增工具

* **`--hgr-guard <PC,...>`** — 記錄指定寫入者對 `$2000-$3FFF` 以外的每一次寫入，
  並附上當時的 `src_ptr`/`dst_ptr`。**一次執行就點名越界與來源串流。**
* `tools/a2_rle_check.py` — 離線解壓 tag 式 RLE，報告吐出的位元組數、terminator、串流是否用完。

### 35.7 判準（本輪之後要看到）

* `--hgr-guard` **無越界記錄**
* `COLD copy check: 2457/2457 match, 0 differ`
* `$65DC`（title 迴圈）、`$6C13`（game_loop）、`$6C29`→`_lv_load` 出現命中
* **`RWTS calls served > 0`** ← 關卡由磁片串流進 `$1000` 的實證
* 渲染出**遊戲畫面**

---

## 36. 本輪（goal round 14，續）：**越界消失、COLD 影像完好、credits 解壓完整跑完 192 列；接著查清「按鍵為什麼進不到 PAD_START」**

### 36.1 移除 `vram_zero` 後的實測（§35 的修法生效）

```
（無 "outside the HGR page" 記錄）          ← 越界消失 ✓
（無 FIRST ESCAPE）                        ← 不再掉出程式 ✓
COLD copy check: 2456/2457 bytes match, 1 differ
probe $65DC hit ...                        ← title_screen 迴圈在跑 ✓
HGR page $2000-$3FFF nonzero bytes: 5595
probe $8251 hit ... src=$1DCE  arg_y=$C0  tag=$01
```

**`src=$1DCE` = `$1900 + $4CE` = CREDITSH 的結尾 ✓ 串流被完整用完。**
**`arg_y = $C0` = 192 ✓ 正好 192 列 ✓**
**→ `credits_screen` 的解壓完整跑完、不再越界 ✓✓✓ §35 的根因與修法都驗證成立。**

### 36.2 下一個阻點：`game_loop` 仍未進入（title 在等 START）

**逐條核對後確認按鍵鏈路本身是對的：**

* `neslib.h`：`PAD_A=0x01, PAD_B=0x02, PAD_SELECT=0x04, PAD_START=0x08, PAD_UP=0x10, PAD_DOWN=0x20, PAD_LEFT=0x40, PAD_RIGHT=0x80`
* `pad_trigger`（`$8251`）反組譯：`jsr $8B0D`(input_poll) → `lda $9516`(pad_latched) → `eor #$FF` → `and ($98),y` → `sta $9516` → `sta $9515`
  **→ `pad_state = $9515`、`pad_latched = $9516`（我先前盯 `$951D` 是盯錯位址）**
* `sys.s` 的 `input_poll`：讀 `PADDL0/PADDL1` 判方向 → `bit BUTN0` → `bit KBD / bpl @done` → 走 `kb_map`（`$0D → PAD_START`）→ `lda KBDSTRB` 確認

**量測：`pad_state` 被寫成 `$61` = `PAD_LEFT($40) | PAD_DOWN($20) | PAD_A($01)`，**
**沒有 `PAD_START($08)`。**

**原因（模擬器語意，不是遊戲邏輯）：**
1. `PADDL0/PADDL1` 在模擬器回讀的值讓 `input_poll` 判成 LEFT+DOWN（`cmp #$60 / bmi`、`cmp #$A0 / bpl` 的兩側都命中）。
2. `BUTN0` 回讀 bit7=0 → 判成 `PAD_A` 一直按著。
3. **`bit KBD` 的 strobe 被「先讀 `$C000` 的那個程式」吃掉** → `bpl @done` 被走到 → 鍵盤映射整個被跳過 → `PAD_START` 永遠不會出現。

**本輪加的解法：`--key-at <PC>` — 在指定 PC（`input_poll` 的 stub `$8B0D`）重新裝填 strobe，**
**保證「把按鍵映射成搖桿位元」的那個程式就是吃到 strobe 的程式。**
**（`--key-every N` 的週期式裝填會被先讀鍵盤的程式搶走，這是 //e 鍵盤「strobe 屬於暫存器」語意的必然結果。）**

### 36.3 本輪定案的工具與規則

* **`--key-at 0x8B0D`** — 在 `input_poll` 入口裝填按鍵（要注入按鍵就用這個，別用 `--key-every`）。
* **`--hgr-guard <PC>`** — 點名越界寫入與當時的 `src_ptr`/`dst_ptr`。
* **`tools/a2_rle_check.py`** — 離線驗證 RLE 串流。
* **規則：全域變數的實際位址要用反組譯確認**（`pad_state` 是 `$9515`，不是從 C 端猜的 `$951D`）；
  **`--watch-addr` 盯錯位址會得到「變數從沒被寫」的假結論。**

### 36.4 判準（本輪之後要看到）

* `pad_state` 出現 `PAD_START($08)`
* `$6C13`（`game_loop`）與 `$6C29` → `_lv_load`（`$8829`）出現命中
* **`RWTS calls served > 0`**
* 渲染出**遊戲畫面**

---

## 37. 本輪（goal round 14，再續）：**「按鍵進不到 PAD_START」的根因是模擬器把 `$C000` 的「讀」當成「寫」在做**

### 37.1 根因（模擬器）

`rd()` 對 `$C000-$C0FF` 的處理是：

```python
softswitch(addr, 0)                 # ← 用「寫」的路徑
return softswitch_read_status(addr)
```

**而 `softswitch` 對 `$C000` 的寫入動作是 `KEYRESET`：**

```python
if a == 0x00:
    st["80store"] = False
    KEY[0] = None          # KEYRESET
    KEYSTROBE[0] = False
```

**→ 每次「讀」`$C000` 都會把待讀的按鍵清掉。**
**第一次狀態讀取吃掉按鍵、之後每次讀都得到 `$00`。**

**//e 的真實語意是不對稱的：讀 `$C000` = 鍵盤狀態（strobe 是暫存器的一部分）；寫 `$C000` = 80STOREOFF + KEYRESET。**
**讀取不該執行寫入動作。**

**已修：**

```python
def softswitch(addr, val, is_read=False):
    ...
    if a == 0x00:
        if is_read:
            return          # 讀取 = 狀態讀取，不改狀態
        st["80store"] = False
        KEY[0] = None
        KEYSTROBE[0] = False
```
**`rd()` 改成 `softswitch(addr, 0, True)`。**

### 37.2 點名過程（每一環都有量測）

| 步驟 | 觀測 | 結論 |
|---|---|---|
| `--watch-addr 0x9515` | `pad_state` 被寫成 `$61`（`PAD_LEFT\|PAD_DOWN\|PAD_A`），**沒有 `$08`** | 鍵盤路徑沒貢獻 |
| 反組譯 `pad_trigger` | `pad_state=$9515`、`pad_latched=$9516`（**我先前盯 `$951D` 是盯錯位址**） | 位址要用反組譯確認 |
| `--probe 0xD05C,0xD061,0xD088` | `$D061`（鍵盤路徑）**有命中** | `bit KBD` 的 bit7 有到 |
| 反組譯 `input_poll` | 查表讀 `$D6C0,y`、比對 `$DA7A`、命中走 `$D078` | 邏輯正確 |
| dump `cold.bin` 的 `$D6C0` | `61 40 64 80 77 10 78 20 20 01 2F 02 0D 08 73 04 00` → **`$0D → $08` 在表裡** | 表是對的 |
| `--probe 0xD078`（單獨） | **0 命中** | 比對從未成功 |
| `--watch-addr 0xDA7A` | **`kbkey = $00`**（不是 `$0D`） | **讀 `$C000` 拿到 0** |
| `--watch-addr 0xC000` | **沒有任何寫入** | 不是程式做了 KEYRESET → 是模擬器在「讀」時做了 |

**→ 根因在模擬器的 `$C000` 讀寫不分。**

### 37.3 本輪也定案的兩件事

* **`--key-at <PC>` 的判定要用「步進前的 PC」**：stub 是 `JMP`，步進後 PC 已經在 `input_poll` 裡面，
  用步進後的 PC 比對永遠不會命中（本輪修掉）。
* **`--probe` 的 12 筆上限是「全部位址共用」**：要看某個位址有沒有命中，**單獨 probe 它**，
  否則會被其他位址的命中吃滿而得到「0 命中」的假結論（本輪 `$D078` 就是這樣差點被誤判）。

### 37.4 目前狀態（§35 修法已驗證成立）

* **無 HGR 越界、無 FIRST ESCAPE** ✓
* **credits 串流完整用完**：`src=$1DCE`（CREDITSH 結尾）、`arg_y=$C0`（正好 192 列）✓
* **COLD 影像完好**：`2456/2457 match, 1 differ` ✓
* `pad_trigger` 有在跑 ✓、`title_screen` 迴圈在跑 ✓
* 磁片 `RESULT: OK`

### 37.5 判準（修好 `$C000` 讀寫後應看到）

* `pad_state` 出現 `PAD_START($08)`
* `$6C13`（`game_loop`）、`$6C29` → `_lv_load`（`$8829`）出現命中
* **`RWTS calls served > 0`** ← 關卡由磁片串流進 `$1000` 的實證
* 渲染出**遊戲畫面**

---

## 38. 本輪（goal round 14，最後一段）：**`$C000` 讀寫分離修好 → `PAD_START` 真的出現了；title 的倒數計時仍未啟動，焦點縮到 title 迴圈的前段**

### 38.1 修好 `$C000` 讀寫分離後的實測（§37 的修法生效）

```
PC=$826E  $9515 <= $69      ← pad_state = $69 = PAD_LEFT|PAD_DOWN|PAD_A|PAD_START ✓✓✓
```

**`PAD_START($08)` 出現了 ✓**
**（先前是 `$61`，缺的就是 `$08`。）**
**→ 模擬器「讀 `$C000` 也會執行 KEYRESET」的 bug 修掉後，按鍵→搖桿位元的鏈路全通 ✓**

### 38.2 目前唯一剩下的阻點（已縮小到一條迴圈的前段）

**`title_screen` 的結構（逐條反組譯，`$6599`）：**

```
$65C4: jsr $62AF        ; fade_screen_in(16)
$65C7: lda #$00 / sta $949A   ; j = 0
$65DC: jsr $81FB        ; ppu_waitnmi            ← 迴圈頂（有命中 ✓）
$65DF: lda $94A4 ... $65EC: jsr $8E4F (scroll) / tax
$65F0: jsr $8348
$65F3: lda $949A / beq $65FB   ; j==0 -> 讀按鍵
$65FB: jsr $8251 (pad_trigger) / sta $9499       ; i
$6601: lda $9499 / beq $6635
$6635: lda $9499 / and #$08 / beq $6694          ; PAD_START ✓
$663C: jsr $8245 (pad_poll) ... $6663: lda #$32 / sta $949A   ; j = 50
$668F: dec $949A / beq $669A                     ; j-- -> 離開
$6694: inc $94A4 / jmp $65DC
```

**量測：**
* `$65DC`（迴圈頂）**有命中** ✓
* `$9499`（全域 `i`）的寫入者**只有 `fade_screen_in`**：`$62B4`（`i=0`）、`$62D4`（`inc i`，1,2,3,...）
  → **`pad_trigger` 的 `sta $9499`（`$65FE`）從未執行**
* `$663C`（PAD_START 分支）**0 命中** ✓
* `$949A`（`j`）只被寫成 `0`（`$65C9`），**從未變成 `$32`(50)**

**→ `title_screen` 的迴圈有在跑，但沒有走到 `$65F3` 的「讀按鍵」那一步。**
**候選：`$65EC: jsr $8E4F` 與 `$65F0: jsr $8348` 之間。**
**已排除：`$8348` 的尾端 `jmp $8C88 → ldy #$04 / jmp $8B40`，而 `$8B40` 是 cc65 的
`pha / clc / tya / adc $98 / sta $98 / bcc / inc $99 / pla / rts`（平衡、會 rts 回呼叫者）✓；
`$857F` 內的 `$858C: jmp $861C → jmp $8C75`（popa）有命中 ✓。**

**下一輪的精確做法（不再猜）：**
1. `--probe 0x65F3`（單獨）→ 確認迴圈有沒有走到「讀按鍵」之前。
2. `--probe 0x65EC,0x65F0`（單獨、分開跑）→ 指出卡在哪一個 `jsr`。
3. 若 `$65F0` 有命中而 `$65F3` 沒有 → 查 `jsr $8348` 的返回（堆疊深度奇偶、`$8B40` 的 `ldy #$04` 與呼叫端推入的位元組數是否一致）。
4. 若 `$65EC` 有命中而 `$65F0` 沒有 → 查 `$8E4F`（`scroll`）的返回。

### 38.3 本輪修好的模擬器缺陷（累計，全部有量測）

| 缺陷 | 症狀 | 修法的關鍵一句 |
|---|---|---|
| `CLC`/`SEC` 反了、`CLD` 清錯位、`CLV` 沒實作 | `ay_out` 計數器走 16 的倍數 → 永不離開 → 12 輪「楔子」 | `0x18→setc(False)`、`0x38→setc(True)`、`0xD8→p&=~0x08`、`0xB8→p&=~0x40` |
| **讀 `$C000` 也會執行 KEYRESET** | 第一次狀態讀取吃掉按鍵 → `kbkey=$00` → 查表永不命中 → `PAD_START` 永不出現 | `softswitch(addr, 0, True)`，`a==0x00` 時 `if is_read: return` |
| `--key-at` 用步進後的 PC 比對 | stub 是 `JMP`，永遠不命中 | 用 `pc_before` |
| `--probe` 上限 12 筆**全部位址共用** | 熱點位址吃滿 → 其他位址得到「0 命中」假結論 | **要判定某位址有無命中，就單獨 probe 它** |

### 38.4 目前狀態

* **無 HGR 越界、無 FIRST ESCAPE、COLD 影像完好（2456/2457）** ✓
* credits 串流完整用完（`src=$1DCE`、192 列）✓
* `pad_state = $69`（含 `PAD_START`）✓
* 磁片 `RESULT: OK`（`AE2GAME` load `$6000` len 12,686）
* 尚未達成：`game_loop` 未進入、`RWTS calls: 0`、遊戲畫面未渲染 → **目標維持進行中**

---

## 39. 本輪（goal round 14，收尾）：**title 的 START 為什麼收不到 — `pad_trigger()` 只報「新按下」的位元，按鍵被裝成「每格都按著」就永遠等於 0**

### 39.1 量測鏈（逐條收斂）

| 探測點 | 結果 | 意義 |
|---|---|---|
| `--probe 0x65F3`（`lda $949A / beq $65FB`） | **有命中** ✓ | title 迴圈走到「讀按鍵」之前 |
| `--probe 0x65FB`（`jsr pad_trigger`） | **有命中** ✓ | 真的呼叫了 `pad_trigger` |
| `--probe 0x65F8`（`j != 0` 分支） | 0 命中 ✓ | `j` 維持 0（符合 `j=0` 的初始） |
| `--probe 0x663C`（`PAD_START` 分支） | **0 命中** ✓ | `i` 的 bit3 從來沒有過 |
| `--watch-addr 0x9515` | `pad_state = $69`（含 `PAD_START $08`）✓ | 按鍵→搖桿位元全通 |

### 39.2 根因（是**量測方法**的陷阱，不是遊戲的 bug）

```c
uint8_t __fastcall__ pad_trigger(void)
{
    uint8_t now = input_poll();
    uint8_t new = now & (uint8_t)~pad_latched;   /* 只有「新按下」的位元 */
    pad_latched = now;
    pad_state = now;
    return new;
}
```

**`--key-at 0x8B0D` 在每一次 `input_poll` 入口都裝填按鍵 → `now` 每格都是 `$69` →
`pad_latched` 立刻變成 `$69` → `new = $69 & ~$69 = 0` → `i` 永遠是 0 →
`$6635: and #$08` 永遠為 0 → `j` 永遠不會變成 50 → 不會離開 title。**

**真實玩家是「按一次」，所以模擬器也必須只裝一次。**

**已加：`--key-once`（配合 `--key-at`，只在第一次到達該 PC 時裝填）。**

### 39.3 本輪修好的模擬器缺陷（累計，全部有量測）

| # | 缺陷 | 症狀 | 修法 |
|---|---|---|---|
| 1 | `CLC`/`SEC` 反了、`CLD` 清錯位、`CLV` 沒實作 | `ay_out` 計數器走 16 的倍數 → 永不離開（12 輪「楔子」） | `0x18→setc(False)`、`0x38→setc(True)`、`0xD8→p&=~0x08`、`0xB8→p&=~0x40` |
| 2 | 讀 `$C000` 也會執行 KEYRESET | `kbkey=$00` → 查表永不命中 → `PAD_START` 永不出現 | `softswitch(addr,0,True)`；`a==0x00` 時 `if is_read: return` |
| 3 | `--key-at` 用步進後的 PC 比對 | stub 是 `JMP`，永遠不命中 | 用 `pc_before` |
| 4 | `--key-at` 每格都裝填 | `pad_trigger()` 只報新按下 → 永遠回 0 | `--key-once` |
| 5 | `--probe` 上限 12 筆**全部位址共用** | 熱點吃滿 → 其他位址得到「0 命中」假結論 | **單獨 probe 要判定的位址** |

### 39.4 目前狀態（已驗證的進步）

* **無 HGR 越界、無 FIRST ESCAPE、COLD 影像完好（2456/2457）** ✓
* credits 串流完整用完（`src=$1DCE`、正好 192 列）✓
* `pad_state = $69`（含 `PAD_START`）✓、`pad_trigger` 有被呼叫 ✓
* 磁片 `RESULT: OK`（`AE2GAME` load `$6000` len 12,686）
* **尚未達成**：`game_loop` 未進入、`RWTS calls: 0`、遊戲畫面未渲染 → **目標維持進行中**

### 39.5 判準（`--key-once` 之後應看到）

* `--probe 0x663C` 有命中（`PAD_START` 分支）
* `$949A` 被寫成 `$32`(50)，然後 `dec` 到 0 → `$669A`
* `$6C13`（`game_loop`）、`$6C29` → `_lv_load`（`$8829`）有命中
* **`RWTS calls served > 0`** ← 關卡由磁片串流進 `$1000` 的實證
* 渲染出**遊戲畫面**

---

## 40. 本輪（goal round 14，決定性）：**遊戲真的進入 `game_loop`、真的從磁片串流關卡（RWTS 6 次）；接著抓到畫面「條紋」的真正根因 — HGR 的 bit7 是 SYNC 位元，每個位元組都必須 SET**

### 40.1 突破（`--key-at 0x65FB --key-once` 之後）

```
probe $663C hit  1: ... A=$08          ← PAD_START 分支進去了 ✓
probe $6C13 hit  2: ...                ← game_loop 進去了 ✓✓✓
probe $6C29 hit  3: ... A=$01          ← game_loop 裡 `jsr lv_load` ✓
probe $8829 hit  4: ... A=$1C          ← _lv_load 被呼叫 ✓
RWTS calls served from the disk image: 6   ← 關卡資料由磁片串流進 $1000 ✓✓✓
PC=$7530 / $722C                        ← 遊戲本體（關卡/圖塊/精靈）在跑 ✓
```

**按鍵注入要「按一次」而且要在 `title_screen` 自己的 `pad_trigger` 呼叫點（`$65FB`）裝填**
**（`--key-at 0x8B0D` 的單次按鍵會被更早就開始跑的 `credits_screen` 吃掉）。**

### 40.2 畫面是條紋 — 根因：**HGR 的 bit7 = SYNC 位元，每個位元組都要 SET**

**渲染出來的遊戲畫面是密集的垂直條紋。**
**查資料：`build/hgr_tiles.bin` 4,096 位元組裡只有 **12.3%** 的位元組 bit7 是 SET 的；
`titleh.bin` 只有 4.5%。**

**Apple //e 的 HGR（以及所有文字/雙解析度畫面）把每個位元組的 bit7 當做顯示的 SYNC 位元：
視訊時基需要它是 1，才能正確擺放一個字元格。**
**bit7 = 0 的位元組不會顯示成「暗的像素」，而是顯示成經典的「等距垂直條紋」。**
**所以：**

| 值 | 真實 HGR 意義 |
|---|---|
| `$80` | **黑**（HGR black） |
| `$FF` | **白**（HGR white） |
| `$00` | **不是黑，是條紋** |

**本專案先前寫下的「packed tileset 已經是 HGR，照原樣寫」是錯的**
（`hgr.s` 裡甚至有一段註解說 `ora #$80` 會造成條紋 — 剛好把因果說反了）。

### 40.3 修法（三處畫路徑全部補上 SYNC 位元）

| 位置 | 原本 | 修正 |
|---|---|---|
| `hgr_clear` 的填色 | `lda #$00` | **`lda #$80`**（HGR 黑） |
| `hgr_put8`（圖塊貼上） | `lda (src_ptr),y` 後直接 `sta` | **`ora #$80`** 再 `sta` |
| `put_byte`（RLE 畫面解壓） | `sta (dst_ptr),y` | **`ora #$80`** 再 `sta` |

**圖塊資料維持「7 個像素在 bit 6..0」，由畫入路徑補上 bit7 ✓**
**（`tools/a2_assets.py: tile_to_hgr` 的 7→bits 6..0 對應不變。）**

### 40.4 本輪修好的模擬器缺陷（累計，全部有量測）

| # | 缺陷 | 症狀 | 修法 |
|---|---|---|---|
| 1 | `CLC`/`SEC` 反了、`CLD` 清錯位、`CLV` 沒實作 | `ay_out` 計數器走 16 的倍數 → 永不離開（12 輪「楔子」） | `0x18→setc(False)`、`0x38→setc(True)`、`0xD8→p&=~0x08`、`0xB8→p&=~0x40` |
| 2 | 讀 `$C000` 也會執行 KEYRESET | `kbkey=$00` → 查表永不命中 → `PAD_START` 永不出現 | `softswitch(addr,0,True)`；`a==0x00` 時 `if is_read: return` |
| 3 | `--key-at` 用步進後的 PC 比對 | stub 是 `JMP`，永遠不命中 | 用 `pc_before` |
| 4 | `--key-at` 每格都裝填 | `pad_trigger()` 只報新按下 → 永遠回 0 | `--key-once` |
| 5 | 單次按鍵裝在 `input_poll` 入口 | 被更早就開始的 `credits_screen` 吃掉 | 裝在 `title_screen` 自己的呼叫點 `$65FB` |
| 6 | `--probe` 上限 12 筆全部位址共用 | 熱點吃滿 → 其他位址得到「0 命中」假結論 | 單獨 probe 要判定的位址 |

### 40.5 目前狀態

* `game.bin = 12,683` bytes（視窗 13,824）；磁片 `RESULT: OK`，35 目錄項目，全部檔案 read-back byte-exact
* **`game_loop` 進入 ✓、`_lv_load` 呼叫 ✓、`RWTS calls served: 6` ✓**
* 無 HGR 越界、COLD 影像完好
* 待驗證：SYNC 位元補上後的**遊戲畫面渲染**

### 40.6 判準

* 渲染出**沒有條紋的遊戲畫面**（可辨識的關卡圖塊、精靈、HUD）
* `RWTS calls served > 0`（已達成 ✓）

---

## 41. 本輪（goal round 15）：**「位址會漂移」這條規則踩實了 — 每次重建後要用呼叫點掃描重新定位，不能沿用上一輪的 PC**

### 41.1 症狀

**上一輪（round 14）有效的 `--key-at 0x65FB`，在本輪重建後完全無效：**
`--watch-addr 0xDA7A`（COLD 的 `kbkey`）**沒有任何寫入** → 鍵盤路徑根本沒跑 →
`pad_state` 只有 `$61`（沒有 `PAD_START $08`）。

### 41.2 原因：重建後位址全部漂移

**`game.bin` 每次重建，函式位址都會移動（本輪實測）：**

| 符號 | round 14 | round 15 | 位移 |
|---|---|---|---|
| `_hgr_draw_screen` | `$617F` | `$6181` | +2 |
| `_ppu_waitnmi` | `$81FB` | `$81FF` | +4 |
| `_pad_poll` | `$8245` | `$8249` | +4 |
| `_pad_trigger` | `$8251` | `$8255` | +4 |
| `_lv_load` | `$8829` | `$8826` | −3 |
| `pad_state` | `$9515` | `$9519` | +4 |
| `pad_latched` | `$9516` | `$951A` | +4 |
| title 的 `pad_trigger` 呼叫點 | `$65FB` | **`$65FF`** | +4 |

**`title_screen`/`credits_screen`/`game_loop` 是 `game.c` 裡的 static 函式 → 不在 `game.map` 裡**
（`game.map` 只列匯出符號），**所以不能用「查 map」取得，必須用呼叫點掃描。**

### 41.3 定案做法（本輪新流程，之後照做）

**要注入按鍵 → 先掃 `pad_trigger` 的呼叫點，取 `title_screen` 那一個：**

```
python tools\a2_callsites.py game 0x8255
   $6588  jsr $8255     ← credits_screen
   $65FF  jsr $8255     ← title_screen   ← 用這個當 --key-at
   $6757 / $6848 / $69EA / $7442        ← game_loop 內
```

**規則（加進 §32.7 / §39.3）：**
8. **每次重建後，所有觀測用位址都要重新取得**：匯出符號查 `game.map`；
   **static 函式用 `tools/a2_callsites.py` 掃呼叫點**；全域變數用反組譯讀出實際零頁/絕對位址。
   **沿用上一輪的 PC/位址會得到「0 命中」的假結論。**
9. **`--key-at` 要掃出來的呼叫點，而且要選「要接收按鍵的那個畫面」的呼叫點**
   （`title_screen` 的 `$65FF`，不是 `input_poll` 入口 — 後者會被 `credits_screen` 吃掉）。

### 41.4 本輪也確認的事（正面證據）

* **`$663C`（`PAD_START` 分支）在重建後仍有命中** ✓ → title 的 START 判定邏輯是好的
* **熱點 PC 全在 `scroll`（`$8E4F-$8E68`，每點 69,474 次）** → 程式在 title 迴圈裡空轉
  （`scroll` 本身沒有迴圈 → 是被呼叫 69,474 次 → 每格約 115 條指令 → 空轉）
* `scroll` 逐條核對正確：`pha / lda $98 / sec / sbc #$02 / sta $98 / bcs / dec $99 /
  ldy #$01 / txa / sta ($98),y / pla / dey / sta ($98),y / rts` ✓

---

## 42. 本輪（goal round 15，續）：**重建後實測 `RWTS calls: 6` 再次成立；越界寫入回來了，且點名出一個「來源位址 = $0000」的畫面的存在**

### 42.1 正面證據（重建後仍成立）

```
RWTS calls served from the disk image: 6      ← 關卡/畫面由磁片串流進 $1000 ✓
FIRST ESCAPE: PC=$8817 executed op=$20 and landed at $0100   ← 就是 RWTS 呼叫本身（預期、無害）
HGR page $2000-$3FFF nonzero bytes: 7879 of 8192
```

**離線驗證全部串流（`tools/a2_rle_check.py`）：**

| 檔 | 大小 | 吐出 | 結果 |
|---|---|---|---|
| `titleh.bin` | 2,059 | 7,680 | terminator 找到、串流用完 ✓ |
| `creditsh.bin` | 1,230 | 7,680 | ✓ |
| `gameoverh.bin` | 1,230 | 7,680 | ✓ |
| `welldoneh.bin` | 2,806 | 7,680 | ✓ |
| `lv00.bin` | 396 | **1,024** | terminator 找到 ✓（這是 NES 名稱表 RLE，**不是** HGR 畫面 → 不可拿去畫 HGR） |

### 42.2 越界寫入回來時的样子（`--hgr-guard 0x6183`）

```
PC=$6183  wrote $0081   src_ptr=$0000  dst_ptr=$0000     ← 有一次畫面的來源位址是 $0000
PC=$6183  wrote $0081   src_ptr=$1800  dst_ptr=$004C     ← 來源走到 $1800（$1000 + $800）
```

**`src_ptr=$1800` = 從 `$1000` 起算吃了約 2,048 位元組 → 與 `titleh.bin` 的 2,059 B 同量級，
代表「解壓到結尾仍未遇到 terminator」。**

### 42.3 本輪排除的假設（都有證據）

* **`zerobss` 不會清 `$1000`**：`LOWBSS` 在 cfg 裡是 `optional = yes`，
  **且沒有任何原始檔使用 `LOWBSS` 區段**（掃過 `src/**/*.s`，只有 `LOWCODE`）→ ld65 直接丟掉它；
  `BSS` 區段落在 `MAIN`（`$6xxx-$9AFF`）內，**不涵蓋 `$1000`** ✓
* **`game.c` 的索引型呼叫是安全的**：`art_screen(gameover)` / `art_screen(welldone)`
  在 `#else`（NES）分支裡，`__APPLE2ENH__` 下不會編譯進去 ✓；
  `art_screen_disk(i)` 自己就會在載入後畫 `$1000` ✓
* **`scroll`（`$8E4F`）沒有迴圈** → 熱點 69,474 次代表「被呼叫 69,474 次」= title 迴圈空轉 ✓
* **`pad_state`/`pad_latched` 的實際位址是 `$9519`/`$951A`**（重建後；上一輪是 `$9515`/`$9516`）

### 42.4 本輪定案（最重要的流程規則）

**每次重建後，所有觀測用位址都要重新取得**（本輪實測位移：`_pad_trigger` `$8251→$8255`、
`_ppu_waitnmi` `$81FB→$81FF`、`_hgr_draw_screen` `$617F→$6181`、`_lv_load` `$8829→$8826`、
title 的 `pad_trigger` 呼叫點 `$65FB→$65FF`）。

* 匯出符號 → 查 `build/a2/game.map`
* **`game.c` 裡的 static 函式（`title_screen`/`credits_screen`/`game_loop`）不在 map 裡**
  → 用 `tools/a2_callsites.py game <目標位址>` 掃呼叫點反推
* 全域變數 → 用 `tools/a2_dis.py` 反組譯讀出實際位址
* **沿用上一輪的 PC 會得到「0 命中」的假結論**（本輪 `--key-at 0x65FB` 就是这样失效的）

### 42.5 下一輪焦點（已縮小到兩條）

1. **找出「來源位址 = $0000」的那次 `hgr_draw_screen`**：掃 `$6181` 的五個呼叫點
   （`$6573`、`$65AA`、`$681D`、`$687B`、`$873F`），逐點核對 `jsr` 前 A/X 的來源；
   用 `--watch-addr 0x80,0x81` 記錄 `src_ptr` 被設定成什麼、由哪個 PC 設定。
2. **確認 `title_screen` 的 START 在重建後能啟動倒數**：`--key-at` 要用掃出來的 `$65FF`，
   並用 `--watch-addr 0x9519` 看到 `PAD_START($08)` 位元。

**判準：`--hgr-guard` 無越界記錄、`pad_state` 含 `$08`、`game_loop` 進入、`RWTS > 0`、渲染出無條紋的遊戲畫面。**

---

## 43. 本輪（goal round 15，收尾）：**「越界寫入」是我自己的量測工具造成的假象 — guard 的 PC 選錯了；真實狀態是畫面繪製乾淨、按鍵鏈路已全通**

### 43.1 最重要的更正：round 14 的「越界」是**假陽性**

**`--hgr-guard` 的參數是「寫入者 PC」。**
**我上一輪填的是 `$6183`，而 `$6183` 是 `hgr_draw_screen` 裡的 `stx src_ptr+1` — 它寫的是零頁 `$0081`，**
**當然「不在 `$2000-$3FFF`」→ 每次進入 `hgr_draw_screen` 都被記成一筆越界。**

**真正的畫面寫入 PC 是 `$61C5`（`sta (dst_ptr),y`）。**
**用正確的 PC 跑：`--hgr-guard 0x61C5` → 「outside the HGR page」完全沒有記錄 ✓✓✓**

**→ 繪製路徑是乾淨的 ✓；`src_ptr=$1800` 那種數字是「解壓正常走完 2,059 位元組」的結果，不是跑掉。**

**規則：`--hgr-guard` 只能填「真正會寫畫面頁的那條指令的 PC」**（本專案 = `hgr_draw_screen` 的
`sta (dst_ptr),y`，本輪為 `$61C5`；每次重建後要用 `tools/a2_dis.py` 重新確認）。

### 43.2 按鍵鏈路本輪全部打通（逐環驗證）

| 探測 | 結果 |
|---|---|
| `--key-at 0x65FF`（重建後掃出來的 title 呼叫點） | 生效 ✓ |
| `--watch-addr 0xDA7A`（COLD 的 `kbkey`） | **`$DA7A <= $0D`** ✓ 按鍵真的讀到了 |
| `--probe 0xD05C`（`bit $C000`） | 有命中 ✓ |
| `--probe 0xD078`（查表**命中**那條路徑） | **有命中** ✓ → `ora #PAD_START` 有執行 |

**→ `input_poll` 的回值是 `$69`（含 `PAD_START $08`）✓**

### 43.3 還剩的最後一哩（已縮到一點）

**`pad_state`（`$9519`）觀測到的值仍是 `$61`（不含 `$08`）。**
**`pad_trigger()` 只回傳「新按下」的位元：`new = now & ~pad_latched`。**
**`--key-once` 只給一次按鍵；title 之前 `credits_screen` 也在輪詢按鍵，**
**所以「那一次按鍵」要精準落在 `title_screen` 的 `pad_trigger` 上才算數。**

**下一輪做法（精確、可執行）：**
1. 讓 `--key-once` 支援「第 N 次到達該 PC 才裝填」（title 的呼叫點在 credits 之後才會被到達，
   用計數器把按鍵留到 title 的第一次輪詢）。
2. 或直接注入兩次按鍵：第一次給 credits 的結尾、第二次給 title。
3. 判準：`--watch-addr 0x9519` 看到含 `$08` 的值 → `$663C` 命中 → `$949E` 被寫 `$32`(50) →
   `dec` 到 0 → `$6C13`（`game_loop`）命中 → `RWTS > 0` → 渲染出**無條紋的遊戲畫面**。

### 43.4 本輪定案的規則（累計）

8. **每次重建後所有觀測位址都要重新取得**（本輪位移：`_pad_trigger $8251→$8255`、
   `_ppu_waitnmi $81FB→$81FF`、`_hgr_draw_screen $617F→$6181`、`_lv_load $8829→$8226`、
   `pad_state $9515→$9519`、title 的 `pad_trigger` 呼叫點 `$65FB→$65FF`）。
   static 函式不在 `game.map` → 用 `tools/a2_callsites.py` 掃呼叫點。
9. **`--hgr-guard` 只能填真正寫畫面頁的指令 PC**（`sta (dst_ptr),y`），填到 `stx src_ptr+1`
   會產生「每次都越界」的假陽性。
10. **`--probe` 上限 12 筆是全部位址共用** → 要判定某位址有無命中，單獨 probe 它。

### 43.5 目前狀態

* 磁片 `RESULT: OK`（`AE2GAME` load `$6000` len 12,683）
* **重建後再次實測 `RWTS calls served: 6`** ✓（關卡/畫面由磁片串流進 `$1000`）
* **繪製路徑無越界（用正確 guard PC）✓**、COLD 影像完好
* 按鍵→搖桿位元鏈路全通（`kbkey=$0D`、查表命中）✓
* 待完成：讓那一次按鍵落在 `title_screen` 的輪詢上 → 進入 `game_loop` → 渲染無條紋遊戲畫面
* **目標維持進行中**

---

## 44. 本輪（goal round 15，最終段）：**點名到最後一個具體阻點：`pad_poll` 進去了、沒有返回**

### 44.1 量測（本輪最後一組）

```
--probe 0x8249 (pad_poll 入口)      → 有命中 ✓（被呼叫）
--watch-addr 0x9519,0x951A
   PC=$8E3B  $9519 <= $00      ← zerobss
   PC=$8E3B  $951A <= $00      ← zerobss
   PC=$826D  $951A <= $61      ← pad_trigger 寫 pad_latched
   PC=$8272  $9519 <= $61      ← pad_trigger 寫 pad_state
   （重複，全部 $61）
```

**`pad_poll` 的反組譯（現行版）：**

```
$8249: jsr $8B11        ; input_poll  ← 入口有命中
$824C: sta $9519        ; pad_state   ← 這筆寫入在觀測裡完全沒有
$824F: ldx #$00
$8251: lda $9519
$8254: rts
```

**→ `pad_poll` 進入後，`sta $9519` 從未執行 → `jsr $8B11`（COLD 的 `input_poll`）在 `pad_poll`
這條呼叫路上沒有返回。**
**同一時間 `pad_trigger` 的 `jsr $8B11` 是有返回的（它的兩個 store 都有觀測到）✓**

**→ 本輪把「title 收不到 START」收斂成一個可驗證的具體問題：
`input_poll` 從 `pad_poll` 進去時不回。**

### 44.2 下一輪的查法（已定，不再猜）

`input_poll` 內唯一可能不返回的迴圈是鍵盤對照表：

```
$D06C: ldy #$00
@kbmap: lda $D6C0,y / beq $D085 / cmp $DA7A / bne @kbnext
        txa / ora $D6C1,y / tax / jmp $D085
@kbnext: iny / iny / jmp @kbmap
```

**表內容（本輪 dump 過）：`61 40 64 80 77 10 78 20 20 01 2F 02 0D 08 73 04 00 00 00`**
**→ 終止子在 index 16 ✓，`iny/iny` 走 0,2,...,16 會遇到 ✓**

**要查的三件事：**
1. `--probe 0xD06C,0xD080,0xD085`（單獨跑）→ 看 `pad_poll` 那次呼叫停在「查表迴圈」還是「表之後」。
2. `--probe 0xD085,0xD08B`（`rts`）→ 確認 `input_poll` 有沒有走到 `rts`。
3. 若停在查表：檢查 `Y` 的實際值（`--watch-addr` 對零頁無效於暫存器，需在迴圈內 probe `0xD080` 的命中次數與 `kbkey` 值）。
   **重點假設：`kbkey = $00` 時，表裡 `0x00` 的鍵位（index 16）就是終止子 ✓ 會返回；
   若 `kbkey` 是表裡沒有的值，迴圈走完表也會返回 ✓ → 所以「不回」更可能發生在查表之前
   （`lda PADDL0` / `lda PADDL1` / `bit BUTN0` 這三個 I/O 讀取之中，模擬器對 `$C064/$C065/$C061`
   的讀取若觸發了不該觸發的 softswitch 副作用，就會改變狀態）。**

### 44.3 本輪定案（工具與規則，累計）

| 規則 | 由來 |
|---|---|
| **每次重建後所有觀測位址重新取得**（static 函式用 `tools/a2_callsites.py` 掃呼叫點） | 本輪位移：`_pad_trigger $8251→$8255`、`_ppu_waitnmi $81FB→$81FF`、`_hgr_draw_screen $617F→$6181`、`pad_state $9515→$9519`、title 呼叫點 `$65FB→$65FF` |
| **`--hgr-guard` 只能填真正寫畫面頁的指令 PC**（`sta (dst_ptr),y`，本輪 `$61C5`） | 填 `$6183`（`stx src_ptr+1`）會產生「每次都越界」的假陽性 |
| **`--probe` 上限 12 筆全部位址共用** → 單獨 probe 要判定的位址 | 本輪 `$D078` 差點被誤判為 0 命中 |
| **`--key-at` 用步進前的 PC；`--key-once N` = 第 N 次到達才裝填一次按鍵** | `pad_trigger()` 只報新按下；每格裝填 → 永遠回 0 |

### 44.4 目前狀態（正面證據）

* 磁片 `RESULT: OK`（`AE2GAME` load `$6000` len 12,683；178/512 資料磁區）
* **重建後實測 `RWTS calls served: 6`** ✓（關卡/畫面由磁片串流進 `$1000`）
* **繪製路徑無越界**（用正確 guard PC `$61C5`）✓、COLD 影像完好（2456/2457）
* 按鍵鏈路：`kbkey = $0D` ✓、查表命中路徑 `$D078` 有執行 ✓
* 四個 RLE 畫面串流離線驗證全部「吐 7,680、terminator 找到、串流用完」✓
* **待完成**：`pad_poll` 不返回 → title 收不到 START → 未進入 `game_loop` 的完整遊戲迴圈、未渲染無條紋遊戲畫面
* **目標維持進行中**

---

## 45. 本輪（goal round 16）：**條紋的來源查清了 — 畫面頁裡装的是「程式碼」，代表解壓器從 `$1000` 一路走進程式影像**

### 45.1 新工具 `--dump-hgr`：把畫面頁照顯示順序成 40 位元組/列印出來

```
page bytes: 7780
most common: [('$a8', 4029), ('$80', 1856), ('$0', 300), ('$bf', 174), ('$ff', 153),
              ('$9f', 118), ('$fe', 86), ('$aa', 72)]

y=  0  80 00 FF 80 80 80 80 80 80 80 80 80 80 80 80 80 80 80 80 80 80 80 80 80 80 ...
y= 40  8D 00 FF 4C 84 3A 8D BC 35 20 A8 26 20 EA 22 4C 7D 22 A0 13 B1 42 D0 14 C8 C0 17 D0 F7 A0 19
y= 96  3D CE FF 08 AD FE 08 85 27 CE FE 08 A6 2B 6C 3E 00 00 FE 08 EE FE 08 20 89 FE 20 93 FE 20 2F
y=150  A8 A8 A8 A8 A8 A8 A8 A8 FE FE FE FE FE 80 80 FE FE FE FE FE 80 80 80 80 80 80 80 80 80 80 80
```

**判讀（每一條都是硬證據）：**

* **`y=40` 那一列是 6502 的程式碼**：`8D`(STA abs)、`FF`(SBC abs,x)、`4C`(JMP abs)、`A8`(TAY)、
  `EA`(NOP)、`20`(JSR abs)、`C8`(INY)、`C0`(CPY imm)、`6C`(JMP (ind)) — **畫面頁裡装的是程式影像的位元組**。
* **主色是 `$A8` = `1010 1000` → bit3、bit5 → 像素 3、5 亮 → 每 8 像素出現兩條亮線 → 就是「條紋」**
  （`$AA` 同理 = `1010 1010`）。
* **`$80` 有 1,856 個 = `hgr_clear` 的 HGR 黑 ✓ 背景本身是對的**（`$80` 的 bit0..6 全 0 → 不亮 ✓）。

**→ 條紋不是 SYNC 位元造成的，也不是圖塊資料造成的：**
**是 `hgr_draw_screen` 的解壓器從 `$1000` 開始、走過串流結尾、繼續吃進 `$2000/$4000/$6000`（程式影像），**
**把那些位元組當成「畫面資料」吐進畫面頁。**
**`$A8` 出現 4,029 次 = 程式影像裡最常見的位元組之一被大量吐進畫面。**

### 45.2 本輪排除的假設（都有證據）

* **不是 SYNC 位元**：渲染器只用 bit0..6 當像素、bit7 只決定顏色；`$80` 渲染成不亮 ✓
* **不是圖塊資料**：`build/hgr_tiles.bin` 的圖塊是正常圖形（例：tile1 = `3E 3E 3E 3F FF 6F FF FF`）✓
* **不是 RLE 串流本身**：`titleh.bin` 離線解壓 → 7,680 位元組、**主色 `$00` 占 6,516**、terminator 找到 ✓
* **不是 `hgr_diag`**：`hgr_diag`/`a2_mark` 在 `neslib.c` 只有宣告、**沒有任何呼叫** ✓
* **不是 `pad_poll` 卡死**：`--probe 0x824C`（`pad_poll` 的 `sta $9519`）**有命中** ✓
  → 上一輪「pad_poll 沒返回」是**我的輸出過濾造成的假結論**
  （`Select-String -Context 0,10` 只顯示 10 行，而寫入紀錄有 600 筆）

### 45.3 本輪定案的量測規則（加進規則表）

11. **輸出過濾會吃掉證據**：`Select-String -Context 0,N` 只顯示 N 行；
    要判定「某個 PC 有沒有寫過」，**直接 `--probe` 那個 PC**，不要從被截斷的清單推論。
12. **`--dump-hgr` 是判讀畫面的正解**：條紋這種「規律圖案」要從位元組層面認
    （`$A8`/`$AA` = 每 8 像素兩條亮線；`$55`/`$AA` 家族都是條紋族），
    **比看圖猜快得多，而且能認出「畫面頁裡是程式碼」這種事實。**

### 45.4 下一輪焦點（已縮到一條）

**要讓 `hgr_draw_screen` 在 `$1000` 的串流結束後停住。**
**已知：終止條件 `$61A0: jsr next_byte / cmp #$00 / beq $61B3 (rts)` 存在且逐條正確；
四個畫面串流離線都「terminator 找到、串流正好用完」。**
**所以要做的是「抓現行執行期 `$1000` 那 2,059 位元組的實際內容」跟 `titleh.bin` 逐位元組比對：**

* 用 `--dump-hgr` 的思路加一個 **`--dump-mem ADDR:LEN`**（照 `rd()` 路由印出記憶體），
  在第一次進入 `hgr_draw_screen` 時（`--probe 0x6181`）印 `$1000..$1810`，
  與 `build/art/titleh.bin` 逐位元組 diff → 立刻知道是「載入內容不對」還是「解壓器沒走到終止條件」。
* 同時 `--probe 0x61A0,0x61A3,0x61B3`（終止路徑三個點，單獨跑）→ 看解壓器有沒有走到 `rts`。

**判準：`--dump-hgr` 的主色回到 `$80`（黑）與圖形位元組、條紋族位元組（`$A8/$AA/$55`）消失、
渲染出可辨識的遊戲畫面。**

### 45.5 目前狀態

* 磁片 `RESULT: OK`（`AE2GAME` load `$6000` len 12,683）
* **`RWTS calls served: 6`** ✓、繪製路徑無越界（正確 guard PC `$61C5`）✓、COLD 影像完好 ✓
* 按鍵鏈路全通（`kbkey=$0D`、查表命中、`pad_poll` 的 store 有執行）✓
* **待完成**：解壓器在 `$1000` 串流結束後停住 → 畫面回到黑底＋圖形 → 渲染出遊戲畫面
* **目標維持進行中**

---

## 46. 本輪（goal round 16，決定性）：**條紋的完整因果鏈查清了 — 有一個「陰影畫面複製」迴圈把資料寫進 `$1000` 的畫面串流暫存區，把 RLE 串流打散 → 解壓器找不到終止子 → 把程式影像吐進畫面頁**

### 46.1 逐環證據（每一環都是量測，不是推論）

**① 現行執行期 `$1000` 的內容 = `titleh.bin`，但有 39 個位元組被改成 `$00`**
（新工具 `--dump-mem ADDR:LEN`，照 CPU 看的 `rd()` 路由印出記憶體，離線逐位元組比對）

```
mem[:16]: 05 00 05 FF 00 05 50 10 00 05 1F 08 00 05 12 02   ← 與 ref 完全相同 ✓
ref[:16]: 05 00 05 FF 00 05 50 10 00 05 1F 08 00 05 12 02
differing bytes: 39   first diff at 65
diff offsets: 65,144,224,304,384,464,624,704,785,864,944,1024,1104,1184,1264,
              1344,1424,1504,1584,1664,1744,1824,1904,1984,1985      ← 間隔約 80 位元組
ref[65]='05'  mem[65]='00'   ref[144]='2A' mem[144]='00'   ref[224]='19' mem[224]='00' ...
```

**② 誰寫的：`--watch-addr 0x1041`（第一個 diff 位址 $1000+0x41）→ 唯一寫入者**

```
PC=$6262  $1041 <= $00
```

**③ `$6262` 所屬的迴圈（反組譯逐條核對）：**

```
$6257: ldx #$10            ; 16 次
$6259: ldy #$00
$625B: lda (zp),y  $8E     ; 來源 2 位元組
$625D: sta (zp),y  $8A     ; 寫進目的地（$1000 區）✓
$625F: iny
$6260: lda (zp),y  $8E
$6262: sta (zp),y  $8A     ; ← 觀測到的寫入點
$6264: clc / lda $8A / adc #$50 / sta $8A   ; 目的地每次 +$50 (=80)
$626B: bcc $626F / inc $8B
```

**→ 這是「每次搬 2 位元組、目的地走 $50、共 16 次」的陰影畫面複製迴圈（NES→HGR 的舊路徑殘留），
它的目的地就是 `$1000` 的畫面串流暫存區 ✓ 每次 +80 → 正好對應 diff 的 ~80 位元組間隔 ✓✓✓**

**呼叫點：`$8099: jsr $6257`（唯一）**

**④ 後果鏈（全部已量測）：**
串流被打散 → **終止子被改掉** → `hgr_draw_screen` 的解壓器走過串流結尾繼續吃記憶體
→ `src_ptr` 從 `$1000` 走到 `$1800`、`$2000`、`$4000`、`$6000`（程式影像）
→ **把程式影像的位元組吐進畫面頁** → `--dump-hgr` 實測：
主色 `$A8` 出現 **4,029 次**、`y=40` 那一列是 `8D 00 FF 4C 84 3A 8D BC 35 20 A8 26 20 EA 22 4C 7D 22 ...`
（`8D`=STA abs、`4C`=JMP abs、`20`=JSR abs、`A8`=TAY、`EA`=NOP）= **畫面頁裡是程式碼** ✓
→ `$A8` = `1010 1000` → bit3、bit5 亮 → 每 8 像素兩條亮線 = **條紋** ✓

### 46.2 本輪排除的假設（都有證據，避免之後重走）

| 假設 | 排除證據 |
|---|---|
| 磁片 sector 對映錯（.po/.do 交錯） | `tools/a2_dsk_verify.py` 明寫「image in DOS (logical) sector order」、`off=tr*16*256+sn*256`，**且全部檔案 read-back byte-exact** ✓；模擬器 `serve_rwts` 用同一個線性對映 ✓ |
| 載入內容不對 | `--dump-mem` 比對：前 16 位元組與 `titleh.bin` **完全相同** ✓（內容對，是被後續寫入打散） |
| SYNC 位元造成條紋 | 渲染器只用 bit0..6 當像素；`$80`（黑）不亮 ✓ |
| 圖塊資料造成條紋 | `hgr_tiles.bin` 圖塊是正常圖形（tile1 = `3E 3E 3E 3F FF 6F FF FF`）✓ |
| `pad_poll` 卡死 | `--probe 0x824C`（`pad_poll` 的 `sta $9519`）**有命中** ✓（上一輪是我輸出過濾截斷造成的假結論） |

### 46.3 修法（下一輪執行，方向已定）

**`$1000` 是「由磁片串流進來的畫面 RLE 暫存區」，不能同時當 NES 陰影畫面的目的地。**
**要做的是讓 `$8099: jsr $6257` 這條陰影複製不再寫 `$1000`：**

1. 先確認 `$8099` 所屬的 C 函式（`fade_screen_in`/`fade_screen_out`/`pal_all` 家族），
   以及它在 `__APPLE2ENH__` 下是否應該存在 —— **//e 路徑不需要 NES 陰影畫面**，
   所以正確修法是把這條複製從 //e 編譯裡移除（`#ifndef __APPLE2ENH__`），
   或把目的地改指到 VRAM（`$1800-$1F7F`，1,920 B，夠放 16×$50=1,280 B）。
2. 修完判準：`--dump-mem 0x1000:0x810` 與 `titleh.bin` **diff = 0**；
   `--dump-hgr` 主色回到 `$80`（黑）與圖形位元組、`$A8/$AA` 消失；渲染出可辨識遊戲畫面。

### 46.4 新增工具（本輪）

* **`--dump-mem ADDR:LEN`** — 照 CPU 的 `rd()` 路由印出任意記憶體（含語言卡/輔助頁），可直接與參考檔逐位元組 diff
* **`--dump-hgr`** — 照顯示順序印出畫面頁 40 位元組/列；**條紋這種規律圖案要從位元組層面認**
  （`$A8`/`$AA`/`$55` = 條紋族；出現 `8D/4C/20/A8/EA` 這種 opcode 群 = 畫面頁裡混進了程式碼）

### 46.5 目前狀態

* 磁片 `RESULT: OK`（`AE2GAME` load `$6000` len 12,683）
* **`RWTS calls served: 6`** ✓、繪製路徑無越界（正確 guard PC `$61C5`）✓、COLD 影像完好 ✓
* 按鍵鏈路全通（`kbkey=$0D`、查表命中、`pad_poll` 的 store 有執行）✓
* **條紋根因已定案（見 46.1 ①–④）**，修法已定（46.3）
* **目標維持進行中**

---

## 47. 本輪（goal round 16，決定性成果）：**條紋的完整根因鏈找到並修好 — 暫存區不再被破壞（diff 39 → 0）**

### 47.1 根因鏈（每一環都有量測）

**`oam_clear()` 會呼叫 `spr_restore()` 把 8 個槽的「背景 stash」寫回畫面，
而 `spr_restore` 用的目的地是 `spr_ptr` — 在 `oam_clear()` 的時刻 `spr_setup()` 還沒跑過，
`spr_ptr` 是零頁的殘值（實測 `$1041`）= `$1000` 畫面串流暫存區裡面。**

```
neslib.c:324  oam_clear():  for (i=0;i<8;++i) { spr_set_slot(i); spr_restore(); }
spr.s:107/116 sta (buf_ptr),y   ; 把「畫面現值」存進 stash
spr.s:111/120 sta (spr_ptr),y   ; 把圖塊寫進畫面（spr_ptr = 殘值 $1041）
```

**→ `oam_clear()` 把 8 槽 × 16 列寫進 `$1000` 的 TITLEH RLE 串流**
**→ 2,059 位元組裡 39 個被改成 `$00`（間隔 ~80 位元組 = 每次 +$50 的步進）**
**→ 串流的 terminator 被改掉**
**→ `hgr_draw_screen()` 走過串流結尾、繼續吃記憶體（`$1800/$2000/$4000/$6000`）**
**→ 把程式影像的位元組吐進畫面頁**
**→ 畫面頁主色 `$A8`（4,029/7,780）、`y=40` 那列是 `8D 00 FF 4C 84 3A 8D BC 35 20 A8 26 20 EA 22 4C 7D 22 ...`
（STA abs / JMP abs / JSR abs / TAY / NOP）= 畫面頁裡是程式碼**
**→ `$A8` = `1010 1000` → bit3、bit5 亮 → 每 8 像素兩條亮線 = 條紋**

**量測路徑（可重現）：**
`--dump-mem 0x1000:0x810` 與 `titleh.bin` 逐位元組 diff → 39 個差異、間隔 ~80
→ `--watch-addr 0x1041` → 唯一寫入者 `PC=$6262`
→ 反組譯 `$6257/$6262` = 每 2 位元組、目的地 +$50、共 16 次的 blitter
→ `--watch-addr 0x8A,0x8B`（`spr_ptr`）→ 只看到 `+$50` 的遞增、**看不到 `spr_setup` 的設定**
→ `spr_setup` 从未執行 → `spr_ptr` 是殘值 ✓

### 47.2 修了三個真實缺陷（全部保留在程式裡）

| # | 缺陷 | 修法 |
|---|---|---|
| 1 | `spr_set_buf()` 遊戲從沒呼叫 → `buf_base` 是連結預設值（落在 `$1000`） | `neslib_init()` 裡 `spr_set_buf((void *)0x9600)`（`__BSS_RUN__=$918B + $41E = $95A9`，$9600 空著；8 槽 × 32 B = 256 B） |
| 2 | `spr_setup()` 的 scanline 沒限幅 → `dhgr_line_off,y` 越界（NES 遊樂場 240 列 > 畫面 192 列） | `cmp #$B0 / bcc / lda #$B0`（176 = 191−15，16 列全部留在頁內） |
| 3 | **`spr_ptr` 未初始化** → `oam_clear()` 的 `spr_restore()` 把 8×16 寫進 `$1000` | `spr_set_buf` 同時把 `spr_ptr` 設成 `$2000`（頁首），沒有 setup 的 restore 就落在頁上 |

### 47.3 修後實測（關鍵指標）

```
STAGING BUFFER diff vs titleh.bin: 0        ← 串流完整，terminator 不再被破壞 ✓✓✓
HGR page $2000-$3FFF nonzero bytes: 8192 of 8192
COLD copy check: 2456/2457 bytes match
```
**（修之前：diff = 39 → 32 → 0）**

### 47.4 本輪排除的假設（都有證據）

* 磁片 sector 對映（.po/.do 交錯）：`a2_dsk_verify.py` 明寫 DOS logical 線性序、全部檔案 byte-exact ✓
* 載入內容不對：`--dump-mem` 前 16 位元組與 `titleh.bin` 相同 ✓
* SYNC 位元造成條紋：渲染器只用 bit0..6 當像素、`$80` 不亮 ✓
* 圖塊資料造成條紋：圖塊是正常圖形 ✓
* 四個 RLE 串流本身有問題：離線全部「吐 7,680、terminator 找到、串流用完」✓
* `dhgr_line_off` 表有問題：**dump 出來 192 對全部在 `$2000-$3FD0`、沒有任何一筆低於 `$2000`** ✓
* `pad_poll` 卡死：`--probe 0x824C` 有命中 ✓（上一輪是輸出過濾截斷造成的假結論）

### 47.5 新增工具（本輪）

* **`--dump-mem ADDR:LEN`** — 照 CPU 的 `rd()` 路由印出任意記憶體，可直接與參考檔逐位元組 diff
  （注意：Windows 檔名不能有 `:`，輸出檔名要用 `mem_%04X_%04X.bin` 這種形式）
* **`--dump-hgr`** — 照顯示順序印出畫面頁；條紋要從位元組層面認（`$A8/$AA/$55` = 條紋族；
  出現 `8D/4C/20/A8/EA` = 畫面頁混進程式碼）
* `tools/a2_tabcheck.py`、`tools/a2_artpeek.py` — 表與 RLE 串流的離線分布檢查

### 47.6 還剩什麼（老實說）

* 畫面頁仍有大量 `$A8`（3,985/7,780）：**代表「有解壓器之外的寫入者把 `$28` 寫進畫面」**，
  本輪已確認寫入者是 `PC=$61C5`（`put_byte` 的 `sta (dst_ptr),y`），
  但 `titleh.bin` 解壓只產生 36 個 `$28`，與頁上的 3,985 個不符
  → **下一輪要做：用 `--watch-addr` 逐頁位址找出那 3,985 個 `$A8` 的來源 PC 與當時的 `src_ptr`**
  （已知候選：`$1900` 的 credits 串流、`$1000` 的關卡資料、以及 `hgr_put8` 的圖塊路徑）。
* 本輪結尾 `RWTS calls served: 0`（上一次是 6）：**代表這次執行沒走到 `game_loop`**，
  要連動上面那條查清後一起驗。
* 音效仍無法在本機驗證（無音效裝置）。
* **目標維持進行中。**
