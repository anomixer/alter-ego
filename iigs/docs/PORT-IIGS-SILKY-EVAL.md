# Alter Ego NES → Apple IIgs / silky-gs 可行性評估

> **路徑說明（2026-11-01）**：本文件寫於上游工作樹 `C:\dev\alter-ego` 內，其中 `C:\dev\alter-ego\Alter_Ego.nes`、`build/…`、`src/…`、`tools/…` 都是那棵樹的路徑，該樹已於 2026-11-01 移除。對應的 IIgs port 文件在 [iigs/AGENTS.md](../iigs/AGENTS.md) 與 [iigs/README.md](../iigs/README.md)，//e 工具在 [docs/archive/apple2e](archive/apple2e/)。


**評估對象**：`C:\dev\alter-ego\Alter_Ego.nes`（NROM 版）→ `C:\dev\silky-gs` runtime  
**參考文件**：[AGENTS.md](AGENTS.md)、[README.md](README.md)、[Alter_Ego.nes](Alter_Ego.nes)  
**日期**：2026-10-26

---

## 0. 結論（先說重點）

**可行，但絕對不是「把 ROM 丟進 silky-gs 就會跑」。**

- silky-gs 的 README 開宗明義說：**它不是 NES emulator**，每個遊戲都要把原始 6502 程式碼「移植成原生 65816 程式」，PPU/APU 暫存器寫入由 runtime 攔截、改畫成 SHR、改播 DOC。 ([silky README L5-L16](file:///C:/dev/silky-gs/README.md#L5-L16))
- 因此 `Alter_Ego.nes` **不能被 runtime 直接載入執行**；沒有「通用 NES ROM loader」這種東西。
- 但 Alter Ego 的條件對 silky-gs 相當友善：**NROM、32KB PRG、8KB 靜態 CHR、vertical mirroring、靜態房間、無 sprite-0 hit、無 mid-frame raster、無 CHR-RAM、無 DMC**。
- 更大的優勢是：**它是 cc65 C 遊戲，原始 NES 原始碼還在 git HEAD**，而且硬體相依幾乎都集中在 `neslib.s` / `crt0.s` / `famitone.s`；`game.c` 本身有 **187 個 HAL 呼叫、沒有直接 PPU/APU 暫存器存取**。
- 真正的工程缺口不是「把 32KB 6502 反組譯」，而是：**把 cc65 C runtime 放進 silky 的 64KB NES bank 與 65816 context**，以及 **16 色 SHR 的 palette 壓縮**。

**建議：Conditional Go。** 先做 1–2 週的 PoC，證明「原版 C 編譯出的 PRG + silky runtime 可以把 title screen 畫出來」；PoC 過了再投入完整移植。以熟悉 65816/cc65 與 silky 的開發者估計，完整移植約 **4–7 週**；第一次做這條 C 整合路徑建議再加 30–50% 緩衝。

---

## 1. silky-gs 的定位：它是 HAL/runtime，不是 emulator

關鍵事實：

1. silky 把 NES 的 6502 遊戲碼**原生**跑在 IIgs 65816 上；PPU/APU 寫入被記錄、排隊，再由 GS task 畫成 Super Hi-Res、播成 Ensoniq DOC。 ([silky README L5-L16](file:///C:/dev/silky-gs/README.md#L5-L16))
2. 執行模型是兩個 task 共用 CPU：NES task 跑遊戲碼、GS task 渲染；60Hz VBL 是排程器；遊戲把「等 VBL」改成 `yield`。 ([silky README L18-L26](file:///C:/dev/silky-gs/README.md#L18-L26))
3. 它不是 cycle-accurate emulator；完整 render 約 12–15fps，dirty renderer 可到 60fps。 ([silky CLAUDE.md L38-L44](file:///C:/dev/silky-gs/CLAUDE.md#L38-L44))
4. 每個 port 都是「反組譯 → Merlin32 → 手工修改」；沒有自動通用 converter。 ([silky README L9-L16](file:///C:/dev/silky-gs/README.md#L9-L16))

**對本專案的意義**：既然 Alter Ego 有 C 原始碼，我們不需要走「反組譯 32KB」那條最痛苦的路；可以走**原始碼層級的 NES binary 重建 + silky shim**。但這條路 silky 沒有現成教學/模板，等於要為它新增一個「C 遊戲」建置模式，這是主要風險與工作量所在。

---

## 2. ROM 與原始碼現況

### 2.1 ROM 規格

`Alter_Ego.nes` 大小 **40,976 bytes**，iNES header：

| 欄位 | 值 | 意義 |
|---|---|---|
| Header | `4E 45 53 1A 02 01 01 00` | iNES |
| PRG | `02` × 16KB = **32KB** | `$8000-$FFFF` |
| CHR | `01` × 8KB = **8KB** | 512 個 8×8 tile（兩個 pattern table） |
| Mapper | **0 = NROM** | 無 PRG/CHR bank switching |
| Mirroring | `flags6` bit0 = 1 | **Vertical mirroring** |
| Battery/Trainer | 無 | — |
| SHA-256 | `2744282b530b410f7ca842459343bfcbc3cbffb65dc4a9e44118b8a4dc93d536` | — |

### 2.2 原始碼：用 HEAD，不要用目前工作區

- NES 原始碼在 **git HEAD `bf9e7ab`** 的 `src/game.c`：**1,606 行**。
- 目前工作區的 `src/game.c` 是 **Apple //e 改版**：**1,709 行**，多了 `lv_load` / `lv_load_art` / `lv_fail_halt` 等磁碟 streaming 鉤子；`git diff --stat` 顯示 `game.c` 有 **3,315 行變動**。
- 因此若要重建 NES 版，請用：

```text
git show HEAD:src/game.c > build/ae_nes/game.c
```

（本次評估已放到 [build/feas/orig/game_head.c](build/feas/orig/game_head.c) 供比對。）

### 2.3 原始碼與 ROM 的對應：高度可信，但不是 byte-identical

我用 cc65 2.19 + 自訂 `nes.cfg` 重建了 HEAD 原始碼：

- 輸出大小：**40,976 bytes**（與 `Alter_Ego.nes` 相同）。
- iNES header：**完全相同**。
- CHR：**8,192 bytes byte-identical**（SHA-256 `8773f354…`，也等於 [src/tileset.chr](src/tileset.chr)）。
- PRG：有 **28,747 bytes 差異**；合理原因是 cc65 2.19 與當年出 ROM 的 cc65 版本、runtime library、最佳化差異。
- 重建 map 顯示：`STARTUP 0x1A7`、`CODE 0x84D + 0x1DBC`、`RODATA 0x2F7C`、`BSS 0x349`，遊戲程式碼約 9.5KB、資料/地圖/音樂約 19KB，符合 32KB NROM。

**判斷**：HEAD 原始碼幾乎確定就是這顆 ROM 的來源；但既然不是 byte-identical，**PoC 時仍要用 NES 參考畫面/模擬器比對 title、第一關、palette**，不要假設「原始碼一定 100% 對應 release ROM」。若真的要求 byte-exact，才需要另外處理 ROM 反組譯或找出當年 cc65 版本。

### 2.4 遊戲對 HAL 的依賴程度（關鍵數據）

`game.c` 內累計 **187 個 neslib HAL 呼叫**，其中：

| HAL | 次數 | 用途 |
|---|---:|---|
| `oam_spr` | 28 | 8×8 sprite |
| `oam_meta_spr` | 9 | meta sprite |
| `ppu_waitnmi` | 15 | 等 VBL／frame sync |
| `sfx_play` | 23 | 音效 |
| `vram_put` / `vram_adr` / `vram_fill` / `vram_inc` | 17 / 9 / 4 / 3 | nametable 上傳 |
| `music_play` / `music_stop` / `music_pause` | 5 / 6 / 2 | FamiTone 音樂 |
| `pal_*` | 18 | palette 設定/淡入淡出 |
| `ppu_off` / `ppu_on_*` | 10 | rendering 開關 |
| `scroll` | 6 | 只有 title/menu 的 0/256 水平切換 |
| `bank_bg` | 1 | 切 background pattern table |
| `vram_read` / `unrle_vram` / `set_vram_update` | 1 / 7 / 4 | 地圖與更新清單 |
| `pad_poll` / `pad_trigger` | 2 / 6 | 輸入 |
| `rand` / `setrand` | 4 / 1 | 隨機 |

**`game.c` 沒有直接 `$2000-$4017` 硬體暫存器存取**；掃到的 `0x2000`/`0x20c0` 等只是 VRAM 位址常數。所有硬體相依都集中在：

- [src/crt0.s](src/crt0.s)：reset、NMI、PPU/APU 初始化、FamiTone 啟動
- [src/neslib.s](src/neslib.s)：PPU/APU-ish HAL、palette、OAM、vram、pad、wait
- [src/famitone.s](src/famitone.s)：FamiTone2 的 APU 寫入

這是本專案最大的有利點：**不需要 patch 32KB 的遊戲邏輯，只需要換掉這層 HAL**。

---

## 3. 與 silky-gs 的能力對照

| 需求 | Alter Ego | silky-gs 支援 | 判定 |
|---|---|---|---|
| Mapper | NROM 0 | NROM（SMB、BF 等 NROM port） | ✅ |
| PRG | 32KB | NROM port 可容納 32KB PRG | ✅ |
| CHR | 8KB 靜態 CHR-ROM、512 tiles | `nromBuild` 轉成 64KB `tiledata.bin` | ✅ |
| Mirroring | Vertical | horizontal/vertical 都支援 | ✅ |
| 遊戲捲動 | 遊戲中固定畫面；title/menu 只做 0/256 水平切換 | 支援 horizontal/vertical scrolling | ✅ |
| Sprite | 8×8、約 30 個、flip/priority/palette | 8×8/8×16、flip、mask、priority | ✅ |
| Sprite-0 hit | **不使用** | 未實作，但本遊戲不需要 | ✅ |
| Mid-frame raster / split | **無** | 不支援 arbitrary raster，但本遊戲不需要 | ✅ |
| CHR-RAM | 無 | 支援，但本遊戲不需要 | ✅ |
| Mapper bank switch | 無 | NROM 不需 | ✅ |
| CHR pattern table switch | `bank_bg()` 只有 1 次 | 支援，但切換會使 background tile 全部重畫 | ⚠️ 效能注意 |
| 音效/音樂 | pulse ×2 + triangle + noise；`FT_DPCM_ENABLE=0` | pulse/triangle/noise；DMC 非必需 | ✅ |
| 輸入 | `pad_poll` 自己 bit-bang `$4016` | `NES_ReadJoy1` 可直接回傳 NES 格式 | ⚠️ 需 patch |
| 解析度 | 256×240 | SHR 320×200 | ⚠️ 需裁切/置中 |
| 色彩 | NES 4 BG + 4 SP groups；實測 unique 14–19 色 | IIgs SHR 同時 16 色 | ⚠️ 需 palette 壓縮/近似 |
| C runtime | cc65 C | silky 沒有現成 C/cc65 路徑 | ❌ **主要缺口** |
| 建置工具 | — | Node + Merlin32 + Cadius/GSPort | ⚠️ 本機缺 Cadius 等 |

**整理**：除了「C runtime 整合」與「16 色 palette」之外，遊戲層面的硬體需求幾乎都落在 silky 已支援的範圍內；NROM、vertical mirroring、靜態 CHR、無 raster/sprite-0，是這個 port 最有利的地方。

---

## 4. 真正的工程缺口

### 4.1 C/cc65 整合（最高風險）

silky 現有 port 都是「ROM 反組譯 → Merlin32 手工改」；Alter Ego 是 cc65 C 編譯出來的 6502 binary。**好處**是 C 原始碼可重用、HAL 集中；**壞處**是 silky 沒有現成的 C 建置流程。

可行的整合方式（建議）：

1. 用 cc65 把 HEAD 的 `game.c` + 自訂 `crt0` + `neslib` + `famitone` 編譯成 **32KB PRG binary**，放在 NES 位址 `$8000-$FFFF`。
2. 把 PRG 從 `.nes` 檔中 **抽出**（offset 16..32784），用 `putbin` 放進 silky 的 `ROMBase` bank 的 `$8000`。
3. 在 `$0800-$7FFF` 放 shim/support code（silky 的 `rom_inject.s` 同級區域）；NES RAM `$0000-$07FF` 仍可寫。
4. 用 `nromBuild` 把 `tileset.chr` 轉成 `tiledata.bin`，放進 `CHRDATA` bank。
5. 在 `Main.s` / `NES_StartUp` 中指定 `VERTICAL_MIRRORING`、`NES_ColdBoot`、`NES_EvtLoop`。

這條路的優點是**不需要重寫 `game.c`**；缺點是 cc65 2.19 的 linker config 要調整（例如 `ONCE` segment、`__STACKSIZE__` 語法；本次重建就遇到），而且要把 shim 位址和 engine 入口接起來。**建議把這視為一個新的「C 遊戲建置模式」，而不是 silky 既有 NROM 流程的自然延伸。** silky 目前唯一的 binary rewriter 範例（`tg-tetris/tools/convert.js`）是針對那個純組語 ROM 的特例，不是通用 C binary 工具。

### 4.2 Reset / NMI / stack / direct page（第二高風險）

`crt0.s` 是為「真實 NES」寫的，直接套到 silky 會壞。必改：

- **`txs`**（[src/crt0.s L65-L67](src/crt0.s#L65-L67)）：silky 已經配置 NES stack page（`DP_NES+$0100`），不能再把 S 設成 `$00FF`，否則會踩到 direct page。**移除。**
- **reset 的 PPU vblank 等待**（[src/crt0.s L73-L76](src/crt0.s#L73-L76)、[L107-L110](src/crt0.s#L107-L110)）：第一個 NMI 還沒發生，會死等。**改成不等待，或改成 `yield`（但要確認 NMI 已開）。**
- **清 RAM 迴圈**（[src/crt0.s L79-L89](src/crt0.s#L79-L89)）：目前只清 `$000-$7FF` 的 **ROMBase** 位址；NES zero page 是另一個 direct page（`DP_NES`），要**額外清 `sta $00,x`**，否則 C 變數/指標初始值不乾淨。
- **NMI 結尾 `rti`**（[src/crt0.s L292-L293](src/crt0.s#L292-L293)）：silky 用 `JSL` 呼叫 NMI，必須回 **`RTL`**；`irq` 的 `rti` 可保留。([silky rom_exec.s L167-L225](file:///C:/dev/silky-gs/src/rom/rom_exec.s#L167-L225))
- **`ppu_waitnmi` busy-wait**（[src/neslib.s L312-L328](src/neslib.s#L312-L328)）：改成：
  - `VRAMUPDATE=1`
  - `JSL yield`
  - `VRAMUPDATE=0`
  - `RTS`
  這樣才符合 silky 的 dual-task 模型。([silky README L18-L26](file:///C:/dev/silky-gs/README.md#L18-L26))
- **`nesWaitFrame` 只會在 PPUCTRL bit 7=1 時返回**（[silky rom_exec.s L178-L192](file:///C:/dev/silky-gs/src/rom/rom_exec.s#L178-L192)）。要確認 `ppu_on_*` 有設 NMI；本遊戲的 `ppu_waitnmi` 都出現在 `ppu_on_*` 之後（已檢查 title/credits/gameover/game_loop 的 context），所以不至於在 `ppu_off` 狀態下死鎖。
- **C 軟體堆疊**：`crt0` 把 `sp` 設成 `__RAM_START__+__RAM_SIZE__ = $0800`（[src/crt0.s L115-L118](src/crt0.s#L115-L118)）；這在 ROMBase 的 `$07FF` 往下成長，和 `$0800` 之後的 support code 不衝突；但要注意 BSS/stack 的 linker 配置。硬體 stack 則在 `DP_NES+$0100`，和 ROMBase 的 `FT_BASE_ADR=$0100`（FamiTone 資料）是**不同 bank**，不會互相覆蓋。

### 4.3 PPU / palette / CHR pattern table

所有 PPU 暫存器存取都在 `crt0.s` 與 `neslib.s`，所以可以用 shim 取代，**不需要 patch `game.c` 或整個 PRG**：

- `$2000` PPUCTRL、`$2001` PPUMASK、`$2002` PPUSTATUS、`$2003` OAMADDR、`$2004` OAMDATA、`$2005` SCROLL、`$2006` ADDR、`$2007` DATA、`$4014` OAM DMA。
- `$2002` 的 reset wait 直接跳過即可；若其他地方用 `BIT $2002`，需要 `BIT_2002` shim（silky 的 `rom_inject.s` 目前只有 `LDA_2002`，沒有 `BIT_2002`）。
- NMI 每 frame 會寫 32 bytes palette（[src/crt0.s L177-L245](src/crt0.s#L177-L245)），silky 的 palette dispatch 要能處理；`pal_fade`/`pal_fade_to_*` 會逐格改 palette，建議使用 **`CUSTOM_PPU_PALETTE_DISPATCH`**（[silky smb/Hooks.s L56-L60](file:///C:/dev/silky-gs/src/games/smb/Hooks.s#L56-L60)、[ppu_palette.s L87-L121](file:///C:/dev/silky-gs/src/ppu/ppu_palette.s#L87-L121)）直接在 NES task 把需要的格子寫到對應 SHR slot，或讓 generated palette 在 `PRE_RENDER` 時 reload CLUT。
- `bank_bg((frame_cnt>>4)&1)` 在 [build/feas/orig/game_head.c L964](build/feas/orig/game_head.c#L964) 只呼叫一次，推測是 title/credits 的動畫；silky 支援切 pattern table，但切換會使 background tiles 全部重畫，**要用 dirty renderer 實測是否造成 16 frame 一次的卡頓**；必要時可固定 table（若視覺可接受）或預先編譯兩份。
- CHR 是靜態 8KB；`nromBuild` 已支援 512 tiles → `tiledata.bin`。([silky nromBuild.js L118-L132](file:///C:/dev/silky-gs/scripts/lib/nromBuild.js#L118-L132))

**Palette 是第二個實質風險**：silky/IIgs SHR 同時只有 16 色，但 NES 每畫面可有 4 BG×4 + 4 SP×4 = 32 個 palette cell。以 [src/palettes.h](src/palettes.h#L1-L13) 的 palette 陣列 union 計算（upper bound）：

| 畫面 | BG + Sprite 的 unique NES 色數 | 16 色可行性 |
|---|---:|---|
| Title | 17 | 需近似 1 色 |
| GameBG1 | 14 | ✅ |
| GameBG2 | 14 | ✅ |
| GameBG3 | 16 | ✅ |
| GameBG4 | 16 | ✅ |
| GameBG5 | 17 | 需近似 1 色 |
| WellDone | **19** | 需近似 3 色 |

多數關卡可完整放入 16 色；title/well-done 需要 **近似色或 per-screen slot layout**。如果要求 pixel-perfect NES palette，就必須用 SHR 的 per-scanline palette（SCB）或更複雜的 renderer；以這個 homebrew 的視覺尺度，**近似 1–3 色通常可接受**，但要在 PoC 時先確認 title 與 well-done。

### 4.4 APU / FamiTone / 輸入

- FamiTone2 的 APU 寫入集中在 `famitone.s` 的 `$4000-$4015`（[src/famitone.s L11-L29](src/famitone.s#L11-L29)）；改成呼叫 silky 的 `APU_*_WRITE` shim 即可。
- `FT_DPCM_ENABLE` 是 **0**（[src/memmap.inc L56](src/memmap.inc#L56)），DMC 樣本初始化也被註解；Alter Ego 不需要 DMC。silky 的 pulse/triangle/noise 已足夠；即使新版 `apu.s` 有 DMC 支援，也不是必要條件。
- **輸入要小心**：`neslib` 的 `_pad_poll` 是 bit-bang `$4016`（[src/neslib.s L509-L553](src/neslib.s#L509-L553)）；silky 的 `rom_inject.s` 的 `LDA_4016` 目前直接回 0（[silky rom_inject.s L633-L640](file:///C:/dev/silky-gs/src/rom/rom_inject.s#L633-L640)），不能直接用。正確做法是改寫 `_pad_poll`，呼叫 **`NES_ReadJoy1`**（[silky rom_input.s L17-L46](file:///C:/dev/silky-gs/src/rom/rom_input.s#L17-L46)），回傳 NES 格式的 byte，再維持原本的 `PAD_STATE`/`PAD_STATET`/`PAD_STATEP` 邏輯。這是 silky 對所有 port 的標準輸入替換方式，不是 Alter Ego 特有問題。

### 4.5 畫面裁切與效能

- NES 256×240 → SHR 320×200：建議水平置中（左右各 32px）、垂直取 `y=8..207`（`y_offset_rows=1`，或 2）。遊戲 HUD 在 `y=15`，仍會落在可見範圍；`y=240` 的隱藏 sprite 本來就不顯示。
- 遊戲進行中是**靜態房間 + 30 個左右 sprite**，最適合 silky 的 dirty renderer；預期可到 30–60fps，遠優於全畫面捲動遊戲。
- title 的 0/256 水平切換是「整頁切換」，不是每 frame 捲動；代價可接受。
- 真正要 benchmark 的是：**palette fade 每 4 frame 一次**、**level clear 的 150 frame 更新**、以及 **CHR table 切換**；這三處可能造成短暫掉 frame。
- NES 邏輯是 60Hz；IIgs 2.8MHz 65816 跑同樣的 C 編譯碼，加上 shim 與 task switch，理論上可行，但**不能只憑 NES 能跑就假設 IIgs 一定 60Hz**；PoC 要量 NES task 的 frame budget。

### 4.6 工具鏈與本機環境

本機已安裝：

- Node.js v24、npm 11；`C:\dev\Merlin32.exe` 存在。
- `C:\dev\emu\GSplus\gsplus.exe` 存在。

但 `C:\dev\silky-gs` 的 `package.json` 指到不存在的位置：

- `C:\Programs\IIgsXDev\bin\Merlin32-BD-1.1.0.exe`（改用 `C:\dev\Merlin32.exe`）
- `C:\Programs\IIgsXDev\bin\Cadius.exe`（**缺**）
- `C:\Programs\gsport\gsport_0.31\GSPort.exe`（**缺**）
- `C:\Programs\IIgsXDev\bin\Crossrunner.exe`（**缺**）
- `C:\Programs\MAME\MAME-0.288\mame.exe`（**缺**）
- `C:\dev\silky-gs\node_modules`（**缺**；但一般 build script 主要用內建模組，`npm install` 主要是 unit test 需要）
- `emu/` 只有 `Classics`/`Finder.Data`，**沒有 GS/OS 開機磁碟**；`make-boot-disk.js` 可做最小 5.25" boot stub，但完整遊戲還是需要 ProDOS/GS/OS 磁碟影像與 Cadius（或同級工具）。

這些是**安裝/設定工作，不是 port 的技術 blocker**；但在 PoC 前要先解決，否則無法看到畫面。

---

## 5. 三條可行路線

| 路線 | 做法 | 優點 | 缺點 | 估計 |
|---|---|---|---|---|
| **A. 原始碼層級 NES binary + silky（推薦）** | 用 HEAD `game.c`/`crt0`/`neslib`/`famitone` 編譯成 PRG；PPU/APU/input/wait 換 shim；PRG 放 `$8000`，support 放 `$0800-$7FFF`；tiledata 由 `tileset.chr` 產生 | 重用全部遊戲邏輯；HAL 集中；不須反組譯 32KB；silky 負責 render/audio | 要新增 C/cc65 建置模式；C runtime/stack/DP 整合；palette 16 色 | **4–7 週** |
| **B. 原生 IIgs C backend（不用 silky 的 NES task）** | 保留 `game.c`，自己寫 SHR tile/sprite renderer、DOC audio、input、frame loop；可借用 silky 的 blitter/compile tile 概念 | 不受 NES 64KB bank / zero page / NMI context 限制；架構較乾淨 | 要重寫 renderer/audio；工作量大；失去 silky 現成 PPU 管線 | **6–10 週** |
| **C. 直接 binary rewriter（tg-tetris 風格）** | 從 `Alter_Ego.nes` 抽出 32KB PRG，掃描/改寫所有 PPU/APU 存取、`abs,Y`、reset/NMI、input；不重編 C | 不需 cc65；保留 ROM 二進位 | C runtime/data 交錯，難以安全 patch；沒有 symbol/map 時風險最高；難驗證 | **4–6 週，風險高** |

**建議選 A。** 如果 M1 PoC 發現 C runtime/zero-page 整合在 silky 下不可行（例如 linker/stack 無法穩定），再退回 **B**（把 `game.c` 當純 C 遊戲，接自訂 SHR backend）；**C 只作為最後手段**，因為這個 binary 是 C 編譯的，不像純組語 ROM 那麼容易逐指令 patch。

> 不建議走「IIgs 上跑 NES emulator」：silky 本身就是效能取捨後的 native port；IIgs 2.8MHz 不可能跑 cycle-accurate NES emulator，這也不是 silky 的設計。 ([silky CLAUDE.md L42-L44](file:///C:/dev/silky-gs/CLAUDE.md#L42-L44))

---

## 6. 建議里程碑與估計

假設：一位熟悉 65816、cc65、silky 的開發者；已有可用的 NES 參考畫面與 GS 模擬器。

| 階段 | 目標 | 估計 |
|---|---|---:|
| **M0：基礎驗證** | 用 HEAD 重建 NES ROM；確認 header/CHR/PRG 與 `Alter_Ego.nes` 的對應；跑 NES 參考畫面；silky 能 build 一個現有 NROM game | **1–2 天** |
| **M1：PoC（最重要）** | 建 `src/games/alterego`；C PRG 放 `$8000`；patch reset/NMI/wait/stack/DP；title screen 在 GSplus 畫出來；palette 與 input 可動 | **5–10 天** |
| **M2：垂直切片** | 第一關完整可玩：地圖、30 sprites、玩家移動、碰撞、HUD、音樂/音效、fade、level clear | **5–10 天** |
| **M3：完整遊戲** | 26 關、title/credits/game over/well done、暫停、設定、按鍵、存檔/prefs、磁碟包裝 | **10–15 天** |
| **M4：優化與驗證** | dirty render 效能、CHR table 切換、palette 近似、全關卡 regression、封裝 | **3–5 天** |
| **合計** |  | **約 4–7 週** |

**Go/No-Go gate**：

- **M1 必須在看到 title screen 後才繼續。** 如果 2 週內仍無法讓 C runtime 穩定跑進 silky，停止加碼，改走 B 或 C。
- **M2 必須量到可接受的 fps**（至少遊戲中 30fps；title/menu 可接受 12–15fps）。如果連靜態房間都不到 30fps，先檢查 dirty renderer 設定與 palette refresh，不要直接進入全關卡美術。

---

## 7. 風險表

| 風險 | 可能性 | 影響 | 緩解 |
|---|---|---|---|
| **C runtime / zero page / stack / NMI context 整合** | 中高 | 高（做不起來就沒有 A 路線） | 先做 M1；用 source-level patch；保留 B 路線 |
| **16 色 palette 不足以重現 title/well-done** | 高 | 中（視覺差異） | 近似 1–3 色；per-screen slot layout；必要時 per-scanline palette |
| **C 編譯碼/shims 讓 NES frame 超時** | 中 | 中 | 量 frame budget；把非必要工作移到 GS task；dirty render |
| **CHR pattern table 切換造成 16 frame 一次卡頓** | 中 | 中 | 預編譯兩份；或固定 table；benchmark |
| **FamiTone/APU 時序或音量差異** | 低中 | 低中 | 先只跑 pulse/triangle/noise；DMC 關閉；用 silky APU 的 frame 更新 |
| **pad_poll 替換錯誤（尤其 `LDA_4016` 回 0）** | 中 | 中 | 直接用 `NES_ReadJoy1` 改寫 `_pad_poll`，不要走通用 shim |
| **原始碼與 release ROM 不完全一致** | 低中 | 低中 | M0 用 NES 畫面比對；必要時以 ROM 反組譯補差異 |
| **工具鏈缺失（Cadius/GSPort/開機磁碟）** | 中 | 低 | 安裝 Cadius；用 GSplus + 自製 ProDOS 影像；`make-boot-disk.js` 可先做 bench |
| **`abs,Y` / 65816 定址差異** | 低 | 低中 | 本遊戲 C/ZP 使用少；用 map/scan 檢查；有問題再加 helper |
| **License** | 低 | 低 | alter-ego 與 silky 都是 Apache-2.0；FamiTone2 來源需確認，但不影響技術可行性 |

---

## 8. 建議的第一個具體工作包

1. **建一個乾淨的 NES build 目錄**（不要改工作區的 Apple //e 版）：
   - `build/ae_nes/game.c` ← `git show HEAD:src/game.c`
   - 複製 `crt0.s`、`neslib.s`、`famitone.s`、`music*.s`、`sounds.s`、`tileset.chr`、`nes.cfg`。
2. **重建 40,976-byte NROM**，確認 header/CHR；用 NES 模擬器截 title/第一關做 reference。
3. **建 `src/games/alterego/`**：
   - `Config.s`：NROM、`VERTICAL_MIRRORING`、`DIRECT_OAM_READ`、`ENABLE_DIRTY_RENDERING=1`、playfield y offset/height、`SPR_PIXEL_SHIFT`。
   - `Main.s`：`NES_StartUp` → `SetDefaultPalette` → `NES_ColdBoot` → `NES_EvtLoop` 的 wrapper。
   - `PPU.s`：`CHR_ROM` 段用 `putbin ../../../../alter-ego/src/tileset.chr`（或複製到 game dir）。
   - `rom.s`/`PRG.bin`：從重建的 `.nes` 抽出的 32KB PRG。
   - `Hooks.s` + `EngineExt.s`：`CUSTOM_PPU_PALETTE_DISPATCH` 與 palette 對映。
4. **改 build copy 的 `crt0.s`/`neslib.s`/`famitone.s`**：
   - 移除 `txs`、reset vblank wait；加 DP clear；NMI `rtl`；`ppu_waitnmi`→`yield`；PPU/APU 寫入→shim；`pad_poll`→`NES_ReadJoy1`。
5. **先編譯、先跑 title**：不要先做 26 關美術或完整音樂轉檔；M1 只看 title + palette + input。
6. **跑 GSplus**：先用 `make-boot-disk.js` 或現有 ProDOS 影像載入；確認畫面後再安裝 Cadius 做正式 `.2mg`。

---

## 9. 和目前 Apple //e / VERA 工作的關係

**2026-10-26 使用者決定：//e DHGR 不再作為主要移植目標。** 原因是 DHGR 的固定色盤／色塊與 fringing 會讓 NES 原色明顯「demake」；IIgs SHR 可從 4096 色 CLUT 選 16 色，對 NES palette 準確得多。因此 [docs/PORT-APPLE2-EVAL.md](docs/PORT-APPLE2-EVAL.md) 已降為 **archived / game-logic reference**，不再投入 //e DHGR 實作；本報告是現行主線。

若你手上另有 VERA 版（別的 repo、別人的作品或後續 branch），它的經驗仍可參考，但請注意：

- 它證明 **`game.c` 的遊戲邏輯與關卡資料可以跨平台重用**。
- 但 **DHGR/VERA 的 video/audio backend 不能直接搬來 IIgs/silky**；//e 的 DHGR renderer、`hgr_*`、Apple II 記憶體配置與 IIgs SHR/silky 的 PPU 管線是不同東西。
- 目前 `src/game.c` 工作區版本已被 //e port 改成 disk-streaming 版；**IIgs/silky 請用 HEAD 的 NES 版**，不要用這份。
- 若 VERA 版有乾淨的 C HAL abstraction，可以參考它的輸入/遊戲邏輯；但 IIgs 這端仍需要 silky 的 PPU/APU 整合。

---

## 10. 附錄：本次評估使用的證據

- `Alter_Ego.nes`：40,976 bytes；header `4E 45 53 1A 02 01 01 00`；SHA-256 `2744282b…d536`。
- HEAD `src/game.c`：1,606 行；目前工作區 `src/game.c`：1,709 行（Apple //e 版）。
- 重建 ROM：40,976 bytes；header 相同；CHR 與 [src/tileset.chr](src/tileset.chr) byte-identical；PRG 28,747 bytes 差異（cc65 version drift）。
- `game.c` HAL 統計：187 次呼叫；`oam_spr` 28、`oam_meta_spr` 9、`ppu_waitnmi` 15、`sfx_play` 23；無直接 PPU/APU 暫存器。
- Palette unique 色數（BG+SP union, upper bound）：Title 17、GameBG1 14、GameBG2 14、GameBG3 16、GameBG4 16、GameBG5 17、WellDone 19。
- silky 能力/限制：NROM、CHR-ROM、vertical mirroring、8×8/8×16 sprites、pulse/triangle/noise；sprite-0/raster 未實作但本遊戲不用。 ([silky README L28-L54](file:///C:/dev/silky-gs/README.md#L28-L54))

---

**最後一句**：這個 port 的**技術可行性高於一般 NES 遊戲**，因為它是 NROM + 靜態 CHR + 靜態房間 + 有 C 原始碼 + HAL 集中；但「高可行性」不等於「低工作量」。**請把第一個目標設為 M1 title screen，而不是直接排 26 關遷移。**
