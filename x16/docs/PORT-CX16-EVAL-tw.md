# Alter Ego：從 Apple II VERA 版移植回 Commander X16 的可行性評估

> 英文版：[`PORT-CX16-EVAL.md`](PORT-CX16-EVAL.md)。本檔是 2026-11-06 翻譯前的繁體中文原文，
> 內容與英文版相同；改動請兩邊一起改（PORT-CX16-EVAL.md 是英文主檔，本檔是中文存檔）。

- 評估日期：2026-11-05
- 評估對象：本 repo 的 `vera/`（Apple II + VERA 卡的 Alter Ego 移植）
- 目標平台：Commander X16（65C02S 8 MHz、512 KB banked RAM、VERA）
- 工具鏈：cc65 2.19 的 `-t cx16`（`cx16.lib` / `cx16.cfg`）
- 實機驗證環境：`C:\dev\emu\x16emu`（x16emu r49 "Pyrite"）
- 產物目錄：`x16/`（本文、`probe/`、`spike/`、`tools/`）

> 本文從可行性評估長成了實作記錄：到 2026-11-06 為止，`x16/spike/dist/` 已經是
> 可以開機、實際操作、有標題音樂與 SFX 的完整移植（26 個關卡檔 LV00–LV25、標題
> 選單、關卡內暫停選單、credits、結局），同一份建置也已在瀏覽器上跑起來（官方
> WebAssembly 模擬器＋GitHub Pages，見 §9）。§13 逐項列出留下的證據；尚未驗證的只有
> §10 與 §13 末尾那幾項（實機、SD/DOS 打包、長時間真人試玩），不作「實機發行已
> 完成」的宣稱。

---

## 1. 結論摘要

| 項目 | 判定 | 依據 |
| --- | --- | --- |
| VERA 影像層能否 1:1 沿用 | **可以** | 兩邊 VERA 暫存器位移完全相同，只有基底位址不同（`$C200/$C400` → `$9F20`）；`L0_CFG/L0_MAP/L0_TIL/HSC/VSC/DC_VIDEO/OAM/PSG` 全部照用 |
| C 原始碼能否直接編譯 | **可以** | `vera/src/a2vera/main.c`（1760 行）以 `-t cx16 -DVERA_BASE=0x9F20` 編譯零錯誤 |
| 組譯原始碼能否沿用 | **大致可以** | `title.s`、`oam.s`、`music_api_ftm.s`、`music_imports_ftm.s`、`ftm_sfx_simple.s` 在 `-D VERA_BASE=$9F20` 下都可組譯 |
| 記憶體佈局是否放得下 | **可以** | Apple II 版 `$2000-$91FF` 主體 + BSS 到 `$94B4` + C stack `$94C0-$9600`，全部落在 X16 的 `$0000-$9EFF` 固定 RAM 內 |
| 能否連結、產生 PRG、開機 | **已驗證** | `GAME`（29,698 B）、`MUSIC` overlay（4,097 B）、`LOADER.PRG`（1,026 B）都成功產生並在 x16emu 開機到 loader |
| 標題畫面能否顯示 | **可以，已驗證** | 標題、選單、星空、sprites 都正確（`x16/spike/shot-title-final.png`） |
| 關卡能否載入並遊玩 | **可以，已可實際操作** | 關卡檔經 VRAM staging 串流解壓寫入地圖，`HELLO WORLD`、HUD、磚台、敵人、水全部正確；`Enter` 進關卡、方向鍵移動、`Z` 交換、`Enter` 暫停/恢復、標題選單可選 Level 03（`x16/spike/play-*.png`、`menu-*.png`） |
| 26 個關卡是否都在出貨目錄 | **是（LV00–LV25）** | 實際操作驗證過 LV01、LV03（選單選關）、LV24（垂直鏡像關卡）；其餘關卡走同一支 `load_level_file()`，沒有逐關實玩 |
| 遊戲手感 bug 是否修完 | **是，三項都在 X16 修掉** | 掉落中每 frame 檢查交換（§7.10）、交換後落點對齊格子（§7.11）、垂直鏡像關卡的鏡像點要有地板（§7.11）；穿地板模擬 756→0 |
| 瀏覽器可玩嗎 | **是** | 官方 X16Community r49 WebAssembly 模擬器＋GitHub Pages（`/x16/index.html`，見 §9）；headless Edge 送 `Enter` 後截到標題畫面與 Level 1（`x16/spike/web-title.png`、`x16/spike/web-level1.png`） |
| 整體可行性 | **可行，重用率高，屬中等工作量** | 影像/音效/輸入三大塊幾乎不用重寫，真正的工作在「檔案 I/O + 開機鏈 + 節奏校正」 |

一句話：**VERA 這一層幾乎是免費的；X16 的載入路徑是唯一實質門檻，而它的根因只是
HostFS 要求小寫檔名（見 §7.5）。** 目前 `GAME` + `MUSIC` + `LOADER.PRG` 已在
x16emu 跑出標題畫面與可玩的 Level 1（§7.6、§7.7）。

---

## 2. 兩個平台的對照

| 項目 | Apple II (+ VERA) | Commander X16 |
| --- | --- | --- |
| CPU | 6502 / 65C02（1 MHz ~ 1.02 MHz） | 65C02S @ 8 MHz |
| 主 RAM | 48–64 KB 線性 | `$0000-$9EFF` 固定 + `$A000-$BFFF` banked（512 KB，bank 選在 `$00`） |
| I/O | `$C000-$CFFF` slot 空間 | `$9F00-$9FFF`（VERA 佔 `$9F20-$9F3F`） |
| VERA 基底 | Slot 2 `$C200` / Slot 4 `$C400` | `$9F20` |
| 影像記憶體 | 128 KB VRAM（兩 bank） | 相同，128 KB |
| 文字/BIOS | Applesoft / Monitor ROM | KERNAL + BASIC ROM（含 DOS 支援） |
| 檔案系統 | ProDOS（MLI，`open/read/close`） | DOS（cmdr-dos）/ HostFS，走 KERNAL `$FFxx` |
| 中斷 | VERA VSYNC 可 poll 或 IRQ | VERA VSYNC + KERNAL IRQ 向量（`$0314/$0315`） |
| 聲音 | VERA PSG 16 聲道 | 相同（PSG 在 `$1F9C0`） |

重點：**X16 的 VERA 與 a2vera 用的 VERA 是同一顆（同一份暫存器定義）**，所以「畫圖、調色盤、
精靈、捲動、PSG」整層不需要重新設計，只需要換 base address。

---

## 3. VERA 暫存器對應表（實際使用到的）

| 用途 | a2vera 巨集 | Apple II 位址 | X16 位址 | 是否相同 |
| --- | --- | --- | --- | --- |
| 位址低/中 | `VERA_ADDR_L/M` | base+$00/$01 | `$9F20/$9F21` | 位移相同 |
| 位址高（A16 + increment） | `VERA_ADDR_H` | base+$02 | `$9F22` | 相同 |
| 資料埠 0/1 | `VERA_DATA0/1` | base+$03/$04 | `$9F23/$9F24` | 相同 |
| 控制（DCSEL/ADDRSEL） | `VERA_CTRL` | base+$05 | `$9F25` | 相同 |
| 中斷致能/狀態 | `VERA_IEN/ISR` | base+$06/$07 | `$9F26/$9F27` | 相同 |
| 顯示模式 | `VERA_DC_VID` | base+$29 | `$9F29` | 相同（`0x51`＝VGA+Layer0+sprites） |
| Layer0 設定 | `VERA_L0_CFG/MAP/TIL` | base+$2C/$2D/$2E | `$9F2C/$9F2D/$9F2E` | 相同（4bpp `$12`、tile base `$80/$90`） |
| Layer0 捲動 | `VERA_HSCROLL/VSCROLL` | base+$2F/$30 | `$9F2F/$9F30` | 相同 |
| 精靈 | OAM `$1FC00`、attr | 相同 | 相同 | 相同 |
| PSG | 16 聲道 `$1F9C0` | 相同 | 相同 | 相同 |
| 調色盤 | `$1FA00`（256×2 B） | 相同 | 相同 | 相同 |

踩過的坑（本輪實測）：

1. `cx16.h` 的 `VERA.address` 只有 16 bit，寫 `VERA.address = 0x10000` 會被截斷成 0。
   A16 在 `address_hi` 的 bit 0，increment 在 bit 6-4。正確寫法是
   `VERA.address = a & 0xFFFF; VERA.address_hi = 0x10 | ((a >> 16) & 1);`
2. `struct __vera`（cc65 `cx16.h`）**沒有 `video` 欄位**，`VERA_DC_VIDEO` 必須用
   `*(volatile unsigned char *)0x9F29`。
3. `VERA_DC_VIDEO` 的 `0x01` 只是 output mode（VGA），不是 layer0；要 `0x51` 才會開 layer0。

---

## 4. 原始碼重用清單

### 4.1 直接可編譯（只換 base address）

| 檔案 | 行數/大小 | 備註 |
| --- | --- | --- |
| `vera/src/a2vera/main.c` | ~1,760 行 | 全部遊戲邏輯、VERA 繪圖、關卡/碰撞、選單；以 `-DVERA_BASE=0x9F20` 編譯零錯誤 |
| `vera/src/a2vera/oam.c` | — | 精靈 shadow table |
| `vera/src/a2vera/music.c` + `ftm_player.c` + `ftm_sfx.c` | — | FamiTone→VERA PSG 播放器 |

### 4.2 需小改（`#ifdef VERA_X16` 掛勾）

| 位置 | 原因 | 本輪做法 |
| --- | --- | --- |
| `main.c` 的 `load_raw_asset()` | Apple II 用 `open/read`（ProDOS MLI），X16 要改成 KERNAL LOAD | 已加 `#ifdef VERA_X16` 分支，轉呼叫 `ae_load_raw_asset()` |
| `main.c` 的 `wait_frame()` / `vera_sync_init()` | Apple II 用 VERA VSYNC 狀態位；X16 的 IRQ 由 KERNAL 接管 | `vera_sync_init()` 在 X16 只清 ISR、不開 `IEN=0x01`；`wait_frame()` 仍需改寫（見 §8） |
| `ftm_envelopes.s` 的 ZP `$9A-$9F` | X16 的 `$9D-$A8` 是保留區 | 需搬到 `$22-$7F` 內，並在 linker cfg 保留 |
| `iobuf.s`（Apple II 專用 1 KB 對齊緩衝） | X16 不需要 | 直接不連結 |

### 4.3 組譯後可直接用

| 檔案 | 說明 |
| --- | --- |
| `title.s` | 開機初始化（`c_sp`、`initlib/zerobss/copydata`、VERA 初值）＋ `.incbin` 內嵌標題資源 |
| `oam.s` | OAM 上傳 |
| `music_api_ftm.s` / `music_imports_ftm.s` | overlay 進入點 |
| `ftm_sfx_simple.s` | 精簡 SFX 解譯器 |

### 4.4 必須重寫

| 項目 | 說明 |
| --- | --- |
| `input.s`（Apple II 鍵盤/PB0/PB1/PDL） | 換成 X16 KERNAL：`jsr $FF56`（`joystick_get`）＋ `$FFE4`/`$FFD2` 鍵盤；本輪已寫了 `input_cx16.s`（16 B/按鍵位元映射見 §6） |
| 檔案 I/O | Apple II `open/read/close`（ProDOS）→ X16 KERNAL `SETNAM/SETLFS/LOAD`；本輪已寫 `asset_cx16.c` / `io_cx16.c` / `kload_cx16.s` |
| 開機鏈 | `STARTUP.BAS`（BLOAD music + BRUN game）→ X16 的 `$0801` PRG loader（本輪 `loader.s`） |

---

## 5. 記憶體／ZP 遷移

Apple II 版目前的實測佈局（`vera/AGENTS.md`）：

```
主影像   $2000-$91FF   遊戲程式 + 資料
BSS      $6347-$674B   FTMDATA $6750 起
額外 BSS $8400-$84FC   相位表 $8500-$92DB
高 BSS   $93A0-$94B4   C stack $94C0 起（下界）
I/O 緩衝 $0C00-$0FFF   （iobuf.s）
music overlay $1000-$1FFF
```

X16 對照：

- 固定 RAM `$0000-$9EFF`：上述全部放得進去（最高 `$94B4`，stack 到 `$9600` 也 OK）。
- `$9F00-$9FFF` 是 I/O，**絕不能碰**：本輪把 `game.cfg` 的 RAM 區間設成 `$2000-$9400`，
  並用 `ld65` 明確配置 BSS segment，避免越界。
- `$A000-$BFFF` 是 banked RAM（512 KB）：可用來做 staging/快取，但**不保證 KERNAL LOAD
  可以寫進去**（見 §7），本輪最後沒有用它。
- Zero page：X16 的 `$02-$21` 是 r0-r15、`$22-$7F` 可用；`$80-$9C` 是 KERNAL/DOS、
  `$9D-$A8` 保留、`$A9-$D3` 數學、`$D4-$FF` BASIC。cc65 的 `cx16.cfg` 把 ZP 放在
  `$22`，大小 `$5E`，因此 `ftm_envelopes.s` 的 `$9A-$9F` 必須搬進 `$22-$7F`。
- 中斷：X16 的 IRQ 由 KERNAL 掌管（`$0314/$0315`），VERA 的 IRQ 若打開而沒有在 handler
  裡寫 `ISR` 清除，會卡死；這也是本輪把 `VERA_IEN` 關掉的原因。

---

## 6. 輸入對照

a2vera 的 `pad` 位元（`main.c` 定義）：

```
PAD_A 0x01  PAD_B 0x02  PAD_SELECT 0x04  PAD_START 0x08
PAD_UP 0x10 PAD_DOWN 0x20 PAD_LEFT 0x40 PAD_RIGHT 0x80
```

X16 端做法（`x16/spike/input_cx16.s`，2026-11-05 實測定案）：

- **`joystick_get`（`$FF56`）device 0 = KERNAL keyboard joystick，是「即時按住狀態」**，
  這一版拿它當方向鍵來源。先前判它「不能拿來當鍵盤」是因為當時 KERNAL IRQ 被關掉
  （見下一點），狀態根本沒更新；IRQ 修好後它會跟著按下/放開變化：
  方向鍵 level-sensitive（按住就一直走），`Enter/Z/X/Shift` 分別對映 START/B/A/SELECT。
- **按鈕**：`A`/`B` 也走 level-sensitive（真實手把就是這樣，NES 也是「按住就算」；
  遊戲自己用 `exchange_input_lock` 去重，不會連發）。`START`/`SELECT` 才是
  rising-edge 單 frame 脈衝，否則 `Enter` 會讓暫停選單每 frame 重新打開。
  若 keyboard joystick 不存在（`Y != 0`）才退回 key 事件 + `KEY_LOCK`。
- **方向鍵的「hold timer」已移除**（只在 keyboard joystick 缺席時使用）。原本放開
  方向鍵後 timer 還會撐 8 frame，等於多走一格——這就是「走到 X 卻跑到 X+1」。
  以 beacon（`AE_EXTRA_DEFINES='AE_DEBUG_XY'`，每 10 frame 印 `player_x`）量測：
  按右 0.25 秒 → x 184→200（16 px，收在 tile 邊界）；修正前是 208。
- **掉落中的交換**：掉落時 `check_tile_actions()` 只在每個 8 px 落點
  （`player_fall_steps==0`）跑一次，單 frame 脈衝要剛好命中那一 frame（命中率 1/8），
  所以「按了都不交換、要狂按」。改成 level-sensitive 後，按住 0.1 秒以上必然涵蓋
  檢查 frame。實測 `right+z:3`（按住右與 Z 走過平台邊緣掉下去）：HUD `x2`→`x1`、
  兩隻 Ego 立刻對調、且 Z 按住 3 秒只花一次交換
  （`x16/spike/shot-input-exchange-fall.png`）。
- 為什麼當年的 key 事件版不夠：KERNAL 只把「按下」的字元丟進佇列，按住方向鍵要靠
  OS/SMC 的自動重複（x16emu 上由 Windows 控制，預設延遲約 0.5 s），所以會出現
  「按一下走一格，停半秒才連續走」。keyboard joystick 沒有這個延遲。
  也因此 `WASD` 在 X16 移除（keyboard joystick 沒有 W 的映射，留著只會不一致）。
- 沒有被 keyboard joystick 映射的鍵仍走 key 事件：`Space`＝START、`1`＝SELECT；
  `J`/`K` 只在 keyboard joystick 缺席時當 A/B 備援。
- 特殊鍵 `T`（SFX/BGM 測試）、`M`/`N`（靜音）、`ESC`（離開測試）同樣走 key 事件，
  細節見 §7.9；兩者都不需要（也不應該）去讀 Apple II 的 `$C000`/`$C010`。
- `game.cfg` 的 BSS 區間只剩約 30–40 bytes 餘裕（`BSS` 現在結束在 `$672F`，
  `FTMDATA` 從 `$6750` 開始）：之後任何在 X16 額外增加的 C 程式碼都可能撐爆 BSS，
  要先在 `#ifndef VERA_X16` 裡砍掉 Apple II 死碼，或調 cfg。
- SNES 手把照文件用 device 1-4（`Y=$FF` 表示沒接）。
- **先前的關鍵錯誤**：X16 KERNAL 的 60 Hz IRQ 來源就是 **VERA VSYNC**（見 §8），
  所以只要把 `VERA_IEN` 歸零（本輪早期為了 poll `VERA_ISR` 而這麼做），KERNAL 的
  IRQ handler 就完全不再執行 → jiffy 時鐘停止、鍵盤掃描停止，`GETIN` 永遠回 0。
  這就是「按鈕都沒作用」的真正原因，跟按鍵注入方式無關。
- 實測（Level 1，`x16/tools/playtest.ps1` 送真實 scan code）：`Enter` 進關卡、
  按住方向鍵右移（1 秒約 58–62 px，一按下就開始走，沒有停頓）、`Z` 交換
  （HUD `x2`→`x1`）、`Enter` 叫出 RESUME/RESTART/EXIT GAME、再次 `Enter` 返回遊戲；
  標題選單 Down/Right/Enter 可選到 Level 03「BROKEN BRIDGE」。
  證據截圖 `x16/spike/play-*.png`、`x16/spike/menu-*.png`、
  `x16/spike/shot-input-right.png`、`x16/spike/shot-input-exchange-fall.png`。

---

## 7. 檔案載入：本輪最大的障礙（重要）


### 7.1 觀察到的事實

在 x16emu r49 上，本輪做了 20 餘支獨立 probe（`x16/probe/io*.c`，結果截圖
`x16/probe/shot-io*.png`），得到以下**可重現**的結論：

| 測試 | 結果 |
| --- | --- |
| cc65 `open()`（`cx16.lib` CBM 層）在 HostFS 上開檔 | **一律回 -1**（`io.c`/`io2.c`） |
| `cbm_k_chrin()` 串流讀檔 | 第一次就回 EOF 狀態 `0x42`（`io6`/`io7`），不可用 |
| `OPEN 2,8,2,"FOO,S,R"` 後 CHRIN | 畫面直接變空白（`io11`），不可用 |
| raw KERNAL `jsr $FFD5`（自寫 `kload.s`） | 會回傳，但 **`A=4`、carry 永遠是 1**（`P=31`），且目標位址沒有出現檔案內容 |
| LOAD 到 VRAM（`A=2` bank0 / `A=3` bank1） | 目標位址的讀回值与檔案不符（`io18`/`io19`） |
| 用 `-dump V`（`Ctrl+S`/`$9FB5` + PC=`$FFFF`）取出 VRAM 全鏡像 | dump.bin 中找不到 `TILES` 的 `0x33` 區塊，也找不到 `CRPAL` 的 `00 00 07 00`，證明資產**沒有**真的進 VRAM |
| 多階段開機鏈（`LOADER.PRG` → `LOAD "MUSIC"` → `LOAD "GAME"`） | `$9FB9` beacon 可看到 loader 依序前進（'B'→'M'→'J'），但 `$2000` 讀到的不是 `GAME` 的第一個 byte（應為 `D8`），代表 LOAD 沒有落點 |
| 只放 7 個檔案的乾淨 HostFS 根目錄 | 行為相同，排除「目錄檔數/HostFS 快取」因素 |

也就是說：**x16emu 自己的 `-prg` 注入可以載入檔案，但機器內部的 KERNAL LOAD 對 HostFS
在這套組態下取不到檔案**（回 `A=4`，逾時/錯誤），於是所有資產載入都是空的。

### 7.2 影響

- 標題畫面、credits、關卡圖資目前都不會出現（畫面是未初始化的 VRAM 雜訊）。
- 這不是 VERA 或遊戲邏輯的問題，而是「X16 的 DOS/HostFS 路徑」問題。

### 7.3 建議的三條路（依序試）

1. **走 DOS 的正式載入路徑**：X16 的 `LOAD` 需要 cmdr-dos 在位。用 `-sdcard` 或先
   `BOOT`/`DOS` 進 DOS 再執行 loader；或改用 BASIC 的 `LOAD`/`BLOAD`（`$FFD5` 由 BASIC
   entry 呼叫，會先確保 DOS channel 15 就緒）。釐清 HostFS 與 `-fsroot` 在這個 ROM 的
   觸發條件（r49 的 IEEE API interception）。
2. **用 `-sdcard` 打包 FAT/`.zip` 映像**：把 `TILES/CREDITS/LVxx/*.PSG` 放進 SD 映像，
   用 DOS 直接讀；這條路最接近實機發行方式，也避開 HostFS 的模擬器差異。
3. **資產全部內嵌**：`TILES`（16 KB）+ 標題/credits（各 4 KB）+ palette（512 B）約
   25 KB，可直接 `.incbin` 進 GAME；只有 26 個關卡檔（每個 ~2.7 KB）留在磁碟即時載入。
   內嵌可讓「開機即顯示標題」不受檔案 I/O 影響，是最快的示範路徑。

### 7.4 已確定的正確用法（不管走哪條路都要注意）

- `LOAD` 回傳的 **carry 不可信**：本輪所有成功的 LOAD 也是 `P=31`（carry=1）。
  不要用 `bcs fail` 判斷成敗（本輪的 loader 一度因此直接跳 fail）。
- `SA=1`（有 2-byte 標頭）用檔案標頭位址；`SA=2`（無標頭）用 X/Y。兩者在本輪的
  HostFS 下都會失敗，但 API 用法本身是對的。
- 目標位址若是 `$0000`（a2vera 的 `GOVER`/`ENDING` 用 `address==0`），KERNAL LOAD 不接受，
  必須先載到暫存區再搬。

---

### 7.5 結論（根因已找到：檔名大小寫）

後續實測推翻了 §7.1 的結論：**問題不在 DOS/HostFS，也不在 LOAD 的呼叫方式，而在
`SETNAM` 送出的檔名字元**。x16emu r49 的 HostFS 只認 **小寫 ASCII 檔名**：

| 送出的檔名 | LOAD 回傳 | 目標位址 |
| --- | --- | --- |
| `"GAME"`（大寫 ASCII） | `A=4`（FILE NOT FOUND） | 未寫入 |
| `"game"`（小寫 ASCII） | `A=0`（成功） | `$2000` = `D8`（正確的第一個 byte） |

驗證（`x16/spike/t3.s`、`t5.s`，beacon 由 `$9FB9` 印出）：

- `LOAD "music"` → `$1000` = `20` ✓、`LOAD "game"` → `$2000`=`D8`、`$2001`=`A2` ✓。
- `LOAD "tiles"`（SA=2, A=3, addr 0）後，VRAM `$10000+$20` 讀回 `02 22 22 20`，
  與 host `vera/build/stage/TILES[32..35]` **完全相同** ✓。
- `LOAD "crpal"`（SA=2, A=3, `$FA00`）後，VRAM `$1FA00` 讀回 `00 00 07 00 5D 00`，
  與 host `CRPAL[0..5]` **完全相同** ✓（先前的「位移 1 byte」是誤判）。
- 因此 §7.1 那些「資產沒落點」的觀察，成因只是檔名大寫；`-dump V` 的 dump.bin
  裡找不到資料也是同一個原因。

**做法**：所有 `SETNAM` 的檔名改成小寫（`loader.s` 用 `"music"`/`"game"`；
`asset_cx16.c`/`io_cx16.c` 需在送名前把 `A-Z` 轉成 `a-z`；關卡檔 `LV00` → `lv00`）。
另外 `LOAD` 回傳的 **carry 仍不可信**（成功時也是 `P=31`），不要用它判斷成敗。

### 7.6 標題畫面與 Level 1 都已渲染（本節已結案）

「隔行黑條紋」後續確認為 §7.5 的檔名大小寫後遺症：資產沒落點時，`title.s` 只能用
殘留 VRAM 畫圖，看起來就像條紋。檔名轉小寫後，標題畫面（`ALTER EGO`、選單、
星空、sprites；`x16/spike/shot-title-final.png`）與 Level 1（`HELLO WORLD`、
HUD `5`/`x2`、磚台、梯子、敵人、水；`x16/spike/shot-level1-plays.png`）都完整正確，
不需要再翻 `DC_*`/`L0_*` 的值。原本懷疑的 `DC_HSCALE/VSCALE=$40`（2 倍放大）
在 X16 上就是正確設定，`t7.s` 當年「填滿實色卻看到雜訊」也是因為資產/地圖寫入
被 `read()` 踩壞（見下節）。

### 7.7 進關卡時發現的兩個真移植 bug（已修）

1. **`read()` 踩壞 VERA 位址**（`x16/spike/io_cx16.c`）。關卡檔從 VRAM staging
   `$A000` 逐 byte 串流，但 `load_level_file()` 同時把地圖寫進 `VERA_DATA0`；
   `read()` 每讀一個 byte 就重設 `VERA.address(_hi)`，於是地圖被寫到 staging 區，
   關卡資料反被自己覆蓋，`load_level_file()` 回 0、畫面停在黑幕（beacon 追蹤可見
   `'L'` 之後沒有 `'o'`/`'O'` 之後的任何進展）。修法：`read()` 進入時存下
   `VERA.address`/`address_hi`，離開前還原（共 3 bytes）。
2. **`keyboard_pad()` 讀 Apple II 的 `$C000`/`$C010`**（`vera/src/a2vera/main.c`）。
   X16 沒有鍵盤鎖存器，`$C000` 是 ROM，會回傳固定 byte，變成「永遠按住某方向」。
   以 `#ifdef VERA_X16` 分支改成直接回傳 `joystick_pad()`（`input_cx16.s` 已把
   KERNAL 鍵盤搖桿與 SNES 手把合併）；Apple II 版路徑完全不變。

另外為了自動化截圖，`main.c` 加了 `#ifdef AE_X16_AUTOSTART` 的測試鉤子，
只有 `-DAE_X16_AUTOSTART=<level>` 建置時才存在，用來跳過選單直接進關卡。
（後來自動化已能直接送按鍵，見 §12；鉤子留著但正常建置不包含。）

### 7.8 開機 credits 的平台行改成 X16

冷開機的 credits 是 NES 原始 nametable（`src/credits.h`）經
`vera/tools/a2vera_art.py` 轉成 VERA tilemap；Apple II 版在 row 24/26 蓋上
`APPLE II VERA CONVERSION BY` / `ANOMIXER 2026`。X16 版要求平台行改成
`COMMANDER X16 CONVERSION BY`，做法是：

- `a2vera_art.py` 新增 `AE2VERA_CREDITS_PLATFORM`（預設 `APPLE II VERA`，所以
  Apple II 產物 byte-identical）與 `AE2VERA_ART_OUT`（輸出目錄），並可用
  `python a2vera_art.py credits` 只重生 credits。
- `x16/spike/build.ps1` 在複製 `vera/build/stage/*` 之後，把 credits 重生到
  `x16/spike/work/art/`，再覆蓋 `dist/CREDITS`、`dist/CRPAL`。
- 驗證：`x16/spike/shot-credits-x16.png` 是 x16emu 實際開機畫面，
  `Nintendo` 以外的五行原始 credits 都完整，最後兩行是
  `COMMANDER X16 CONVERSION BY`（藍）與 `ANOMIXER 2026`（橘）。


### 7.9 特殊按鍵（T/M/N、cow level、跳關密技）

Apple II 版的 `keyboard_pad()` 除了方向/A/B，還有幾個「不是手把」的鍵：`T` 直接
合成 NES 的 START+A+B 開啟 SFX/BGM 測試畫面、`M`/`N` 切音樂/音效靜音、`ESC`
離開測試畫面、`G` 重新偵測手把；另有兩個密技：標題畫面按 SELECT 進 cow level
（`current_level=0`），以及 B、左、A、B、左、A 之後按 SELECT 直接過關。
X16 版把這批鍵都接上，但**不讀** Apple II 的 `$C000`/`$C010`（X16 上那段是 ROM）：

- `x16/spike/input_cx16.s` 的 `mapkey` 認 `T`/`t`（`$54`/`$D4`）、`ESC`（`$1B`）、
  `M`（`$4D`/`$CD`）、`N`（`$4E`/`$CE`），設一個單 frame 旗標
  `_ae_key_t`/`_ae_key_m`/`_ae_key_n`（每次 `_joystick_pad` 開頭清零）；
  `T`/`ESC` 另外透過 `set_btn` 把 START|A|B 打進 `pad`，維持「標題按 T 開測試畫面」
  跟 Apple II 相同的語意。
- `vera/src/a2vera/main.c`：`VERA_X16` 分支的 `keyboard_pad()` 用那三個旗標
  做靜音切換（含 `title_menu_dirty=1`，標題的 MUSIC/SOUND 字才會更新）；
  `sound_test_screen()` 進入時清掉 `ae_key_t`、迴圈中看到 `ae_key_t` 就離開
  （所以按 T 進、再按 T 或 ESC 一定出得來，不會卡在測試畫面）。
- Apple II 專用的 `KEYBOARD`/`KBDSTRB`/`keyboard_model` 區塊現在都在
  `#ifndef VERA_X16` 裡（在 X16 是死碼，留著不但浪費空間也曾讓測試畫面離不開）。

**跳關密技的 X16 專屬調整**：X16 的 A/B 是 level-sensitive（按住就是按住），
若照 Apple II/NES 的 `if (pad == code[i])` 逐 frame 比對，同一次按住的第二個
frame 就會比對失敗並把序號歸零 → 實際上要精確到 1 frame 才輸入得進去。
X16 版改成「**pad 值有變化才算一次**」（`#ifdef VERA_X16`，`static code_last_pad`），
所以用正常速度點按即可；實測 `z,left,x,z,left,x` 後在關卡中按 `1`，
畫面出現 `LEVEL CLEAR`（`x16/spike/shot-level-skip.png`）。

**實測證據**（全部是 x16emu r49 + `x16/tools/playtest.ps1` 真實 scan code）：

| 檔案 | 內容 |
| --- | --- |
| `x16/spike/shot-soundtest.png` | 標題按 `T` 進入 `SFX 00 BGM 1`，右鍵切到 BGM 模式（橘字），下方無殘留字 |
| `x16/spike/shot-mute-keys.png` | 依序按 `M`、`N` 後標題顯示 `MUSIC OFF` + `SOUND OFF` |
| `x16/spike/shot-cow-level.png` | 標題按 `1`（SELECT）→ `Enter` → 載入 `COW LEVEL`（level 0）|
| `x16/spike/shot-level-skip.png` | 密技 `z,left,x,z,left,x` + `Enter` 進關 → `1` → `LEVEL CLEAR` |

音訊另外用 x16emu `-wav` 客觀驗證：`x16/spike/wavstat.py`（先修好被 kill 的 wav
header，再逐段印 RMS/peak）。標題音樂每秒 rms ≈ 0.08–0.11；按 `T` 後標題音樂停止
（rms 0.005）；在 SFX 模式按 `Z` 是短 burst（250 ms 窗 rms 0.09、peak 0.105）；
切到 BGM 模式按 `Z` 又回到持續 rms ≈ 0.10。也就是測試畫面的音效與音樂都真的有
輸出，不只是畫面看起來對。


### 7.10 落下中的交換：從「1/8 frame」改成「每 frame」（2026-11-05 追加）

玩家回報「掉下來過程中狂按 `z` 或 `x`，要掉 3–4 個身高才會交換」。查下去發現不是
輸入層（A/B 早就是 level-sensitive，實測按住 `Z` 一秒＝連續 61 個 frame 都是
`pad=0x02`），而是**交換檢查的時機**：

- NES 原作的交換檢查在 `player_dir==DIR_NONE` 的分支裡（`src/game.c` 1176–1268）。
  一掉格是 `player_move_cnt=8`，掉落期間 `player_dir=DIR_DOWN`，所以**每 8 px 只有
  1 frame** 會進到那段程式碼 → 只有 1 frame 的窗戶。
- X16 版照抄，`check_tile_actions(pad)` 也只在 `player_fall_steps==0` 時呼叫。按住
  按鈕一定吃得到那個窗戶，但「點按」時每次只有 1/8 的機率命中，於是變成狂按也
  常常沒反應，平均要 3–4 格（24–32 px）才成功一次。
- Apple II 不覺得這麼糟，是因為 `$C010` 的 any-key-down 旗標（level-sensitive）
  正好會蓋住那 1 frame；這也解釋了為什麼這個問題只在 X16 被回報。

修正（`vera/src/a2vera/main.c`，`#ifdef VERA_X16`，Apple II 不編）：

```c
if (player_fall_steps && !exchange_active && !player_dead &&
    items_left && (pad&(PAD_A|PAD_B)) && !exchange_input_lock) {
    begin_player_exchange();
    collected=1;
}
```

掉落中的每個 frame 都接受 A/B，按下的第一個 frame 就進入交換動畫（交換的對象是
鏡像的另一個 Ego，所以 `y` 不變、只有 `x` 來回），不必等下一格。Apple II 建後的
`main.c` 完全不變（只有 `#ifdef` 包住的新增碼），Apple II 產物位元組不變。

**量測**：`$env:AE_EXTRA_DEFINES='AE_DEBUG_FALL'` 建置會在遊戲迴圈每 frame 把
`(player_y&$F8)|(pad&$07)` 寫到 `$9FB9`（x16emu 的 `User debug 1`），解析用
`x16/spike/bytrace.py`。每 frame 寫 3 個 byte 的 `AE_DEBUG_XY` 在 x16emu 裡偶爾
會漏印，逐 frame 對齊時要用壓成 1 byte 的 `AE_DEBUG_FALL`。

| 測試（`playtest.ps1`） | 修正後 |
| --- | --- |
| `enter,right:0.7,z:0.3` | `Z` 按下的第一個樣本就是掉落格（`y=144`），之後 `y` 立刻凍結（交換動畫開始）；HUD 由 `x2` → `x1`（`x16/spike/ma-3-z.png`、`fx-3-z.png`）|
| `enter,right:0.7,x:0.3` | `X`（A 鍵，`pad=0x01`）同樣在第一個 frame 觸發（`x16/spike/mb-3-x.png`）|

### 7.11 中途交換後不可「掉穿地板」：落點對齊格子（2026-11-06 追加）

§7.10 上線後玩家回報「有時會掉穿地面」（附圖是 LV24 ALMOST THERE、HUD 顯示
`x5`／`x5` 的掉落瞬間）。根因是交換動畫把掉落**凍結在 8 px 格子中間**：

- 按下 A/B 的那個 frame，`player_y` 是「掉落起始格 + `r`」（`r=1..7`），而
  `player_fall_steps` 還留著 `8-r` 步。交換動畫期間 `y` 不動，動畫結束時
  `update_player_fall()` 看到步數不為 0 就**直接繼續往下掉**，跳過鏡面那一欄的
  地板測試。
- 若鏡面那一欄的下一格是實心方塊，主角就卡進方塊裡；重力只看腳下那一格
  （`y+8` = 方塊的下一格 = 空），判定「腳下沒地板」→ 繼續掉 → 直接穿過平台。
- 站著的交換沒有這個問題（`player_fall_steps==0`、`y` 一定在格子上），只有
  2026-11-05 新加的「掉落中每 frame 都收 A/B」才會踩到。

修正（`main.c`，`#ifdef VERA_X16`，Apple II 不編）：交換在掉落中開始時記錄
`exchange_midair`，動畫到達落點時把 `y` 對回掉落時所在的那一列、並清掉未用完的
步數，讓重力重新測鏡面那一欄（有地板就停住，沒有才繼續掉）。

```c
if (ae_midair_ok()) begin_player_exchange();  /* 觸發處 */
if (exchange_active) exchange_midair=1;

#ifdef VERA_X16                                 /* advance_player_exchange() */
if (exchange_midair) {
    exchange_midair=0;
    player_y=(uint8_t)(player_y&0xF8);
    player_fall_steps=0;
}
#endif
```

另一半原因是**垂直鏡像關卡**（`sync_type!=0`，LV05/08/15/19/24 共 5 關）：另一隻 Ego
在 `y=240-player_y`，中途交換等於把主角「穿過平台」傳送到鏡射高度。使用者附的 LV24
截圖（HUD `x5`/`x5`、主角掛在主平台下方）正是這個：掉落在主平台上方時按下 `z`，
鏡像點落在平台底下，交換動畫就把他送到地板下。幾何統計（`fallswap_sim.py`）：這 5
關修正前「會被接受」的中途交換共 14,616 個情境，其中 **13,538 個（93%）** 落點腳下
沒有地板。

修法：這 5 關的中途交換多一道「鏡像點腳下要有地板」的判斷（`ae_midair_ok()`），
鏡射高度剛好是合法落地點就立刻換，否則等掉到有落點的那一個 frame 才換；總共 1,694
個掉落 frame 會被接受，穿地板 0 件。

C 版判斷約 38 bytes，但主 RAM 只剩 6 bytes，所以寫成手寫組語放在新的 `GATE` 段：

- `x16/spike/gate_cx16.s`：`uint8_t __fastcall__ ae_midair_ok(void)`，`sync_type==0`
  直接回 1，否則用 `collision_map[((feet-48)>>3)*32+(x>>3)]`（`feet = clamp(240-y)+8`，
  `feet>=208` 視為 wall）檢查 `TILE_WALL|TILE_LADDER|TILE_BRIDGE`。
- `x16/spike/game.cfg`：`GATE: load = RAM, type = ro, start = $92DC;`，正好塞在
  `FTMTABLE` 結束 `$92DB` 與 `FTM_HIGH_BSS` 開始 `$93A0` 之間的空隙（196 bytes，
  實測 95 bytes）。`loader.s` 是整份 `GAME` 映像載入（`fill = yes` 的填充也寫進
  檔案），所以這段程式碼照樣會被載入到 `$92DC`。
- `main.c` 只要把 `player_x`／`player_y`／`sync_type`／`collision_map` 從 `static`
  拿掉（大小不變、Apple II 版不受影響），組語才能 import。

**Apple II VERA 版維持原樣**：這一輪的行為修改（每 frame 檢查中途交換、交換後對齊
格子、鏡像點要有地板）全部在 `#ifdef VERA_X16` 裡，`vera/` 的發行映像不動。Apple II
版本來就沒有這兩個 bug：它的交換只在「落地格」成立（`player_fall_steps==0`），起點
一定是格子、交換後不會有未用完的步數在鏡像欄繼續掉，且沒有垂直鏡像關卡的即時傳送。
`static` 拿掉那項已驗證對 Apple II 無影響：cc65 `-t apple2 --cpu 6502 -Oirs` 分別
編「static 版」與現行版，6,166 條指令 0 差異（listing 只多 4 個 `.export`）。

**驗證**：`x16/spike/fallswap_sim.py` 直接讀 `dist/LV00..LV25` 的封包重建碰撞圖，
重播 `check_map()`／`update_player_fall()`／`advance_player_exchange()`：

| 建置 | 掉落中按 A 的情境 | 主角格子變成實心（＝穿地板）|
| --- | --- | --- |
| 修正前 | 65,667 | **756**（例：LV00 `x=104,y0=96` → 鏡面 `x=144`，落點 `(144,104)`）|
| 修正後 | 65,667 | **0**（含 `sync_type!=0` 關卡：落點沒地板時不讓交換）|

x16emu 實測（出貨版）：LV01 `enter,right:0.7,z:0.3` 交換後站在地面、交換數
`x2`→`x1`（`x16/spike/g1-3-z.png`）；LV24（`sync_type=1` 垂直鏡像，選單選關 24
後 `right:1.2,z:0.4`，掉到主平台高度時按 `z`）交換數 `x6`→`x5`、主角**站在主平台
上面**（`x16/spike/g24-27-z.png`），不再被送到平台底下。


## 8. 影格節奏與音樂
| 項目 | Apple II 版 | X16 版實作 |
| --- | --- | --- |
| 每 frame 同步 | `while (!(VERA_ISR & 1)); VERA_ISR = 1;`（VSYNC 狀態位） | 掛 `$0314/$0315` 攔 KERNAL IRQ：handler 只 `inc` 一個計數器，再 `jmp` 回原 handler；`wait_frame()` 等計數器變化（`input_cx16.s` + `main.c` 的 `VERA_X16` 分支） |
| 音樂 tick | 與 frame 同步 | 每 frame 1 個 FamiTone source tick（`VERA_X16` 覆蓋掉 Apple II 的 1.5 tick 排程） |
| PSG 輸出 | VERA PSG 16 聲道 | 完全一樣（`$1F9C0`） |

**關鍵（原本判斷相反，2026-11-05 實測改正）**：X16 KERNAL 的整個 IRQ（jiffy 時鐘 +
鍵盤掃描）就是由 **VERA VSYNC 中斷**驅動的（KERNAL 開機時把 `VERA_IEN` 設成 bit0=1）。
所以：

- 不可以把 `VERA_IEN` 歸零去 poll `VERA_ISR` —— 那會讓 KERNAL IRQ 完全不執行，
  jiffy 停止、鍵盤佇列永遠是空的（實測 `$A2` jiffy 低 byte 在遊戲中始終 `$00`、
  自己掛的 IRQ 計數器 12 秒內始終 0）。本輪最初就是這樣才「按鈕都沒作用」。
- 也不需要在 handler 裡清 `VERA_ISR`：KERNAL 的 handler 自己會處理 VSYNC；
  我們的 handler 只負責計數，然後 tail-call 回原 handler。
- `vera_sync_init()` 在 X16 改成 `VERA_ISR=0x0F; VERA_IEN=0x01;` 再呼叫
  `ae_irq_install()`，Apple II 路徑不變。
- 同理，`asset_cx16.c` 的 KERNAL LOAD 前後會 `sei`/`cli` 並存回 `VERA_IEN`；
  載入完成後再呼叫 `CLRCHN`（`$FFCC`）把輸入通道還給鍵盤，否則 `GETIN` 仍指向檔案。

**速度修正（2026-11-05，使用者回報「音樂快了點、遊戲速度也快了點」）**：
Apple II 的 FTM 版一秒只跑約 40 次迴圈，所以它在 `main.c` 用
`logic_delta=(++ftm_rate_phase&1)?2:1`（平均 1.5 個 NES 步/迴圈）把遊戲拉到 60 Hz，
並在 `ftm_player.c` 的 `music_tick_impl()` 對關卡曲交替 1/2 個 source tick（平均 1.5）。
X16 的迴圈本來就是 VSYNC 鎖定的 60 次/秒（實測沒有任何一次跳過 VSYNC），
直接套用這兩個 1.5 倍補償就變成**全部快 1.5 倍**：角色每秒走 ≈90 px（NES 是 60 px），
關卡音樂也快 50%。修法：兩處都以 `#ifdef VERA_X16` 走單步路徑
（`logic_delta=1`、每 frame 剛好 1 個 source tick），Apple II 版維持原本補償。
修正後實測 2 秒走 235→347 px（≈56 px/s），與 NES 的 60 px/s 相符。

**音樂 tempo 微調（2026-11-05，使用者回報「音樂有稍微慢一點點」）**：
X16 這一版是 NES 原生的 60 source tick/s，但使用者聽感仍偏慢一點。因此加上
`AE_X16_TEMPO_TRIM`（單位 1/256 tick/frame，預設 8 ≈ +3.1%，0 = 精確 60 Hz）：
`music_tick_impl()` 內用 8-bit 累加器，滿 256 就多打一次 tick，長期沒有漂移。
Apple II 路徑不受影響；建置時用 `$env:AE_X16_TEMPO_TRIM` 覆蓋。

**暫停選單音效：EXIT GAME 沒聲音、RESTART 拖尾音（2026-11-08，X16 版與共用同一份
`main.c` 的 Apple II VERA 版同時回報）**。同一條路徑上其實有兩個獨立毛病：

- EXIT GAME 完全沒播提示音：暫停選單的確認分支直接跳去 `leave_game_to_title()`，只有
  RESUME／RESTART 會走到 `sfx_start(0)`（NES 是每次暫停確認都播 `SFX_START`）。修法是在
  分支前先把提示音播出來。
- RESTART 會留下拖著的音。提示音是 `SFX_START`＝83 個 SFX source tick ≈1.38 秒
  （`vera/build/ftm_sfx_data.s`），這裡其實有兩層原因：
  1. `loading_tick()` 在 `active_music==255` 時直接 return——那正是 `stop_music()` 為了重新
     讀取關卡而留下的狀態。整個讀檔期間 music tick 與 SFX tick 都停擺，所以 Apple II 版
     的 PSG 語音就維持在它最後到達的那個音。修法：`loading_tick()` 每個 VSYNC 都 tick
     SFX（music 仍維持 gated，否則 FTM player 會在讀檔途中恢復磁碟 prefetch）。
  2. X16 的資產層還更糟，`loading_tick()` 根本碰不到：`open()` 是用一次 KERNAL LOAD（期間
     `sei`）把整個關卡檔 stage 進 VRAM（`x16/spike/asset_cx16.c` 的 `ae_stage_vram()`），
     整段搬運中沒有任何地方可以 tick。於是提示音停在當下的那個音，撐過整個 stage 讀取
     ——HostFS 上約 0.5～1 秒，實機 SD 卡更久——直到讀檔「之後」才被 `sfx_stop()` 放掉：
     這就是 X16 回報的拖尾音。修法：在 `load_level_file()` 開頭、`#ifdef VERA_X16` 底下先把
     待播的提示音停掉，也就是 tick 停擺的那個位置。現在確認音只播完 16 frame 的淡出
     （≈0.27 秒），stage 讀取期間完全無聲，下一行就接關卡曲。

要把提示音「切掉」需要一個音樂 API 本來沒有的 stop：`sfx_stop()`（清掉 stream 指標與
repeat 計數，再把四個 SFX 語音靜音）。FTM：`vera/src/a2vera/ftm_sfx_simple.s` 的
`_ftm_sfx_stop`，由 `music_imports_ftm.s` 轉接；PSG：`music.c` 的 `sfx_stop_impl()`，
經 overlay 的 `$1027`（`music_api.s`／`music_imports.s` 的 `_sfx_stop`；它是
`_music_prefetch`（`$1024`）之後的第十個入口，既有位址都沒動）。Apple II 版在讀完關卡
之後呼叫（它用 640-byte 分塊讀，`loading_tick()` 有在 tick，提示音真的能播過讀檔），
X16 版則在讀檔之前呼叫；兩者都在 `play_music()` 之前切掉，也就是關卡曲開始的位置。
EXIT GAME 則在轉場前播提示音，到標題曲時切掉。

塞進去是有代價的。`#ifdef FTM_VERA` 同時涵蓋 X16 版與 Apple II 的 FTM 版，新增的程式碼
把 ONCE 推過 `$6750` 的 FTM 資料起點——X16 的 BSS 多出 5 bytes。於是搬了七 bytes 的冷門
狀態（X16 是八 bytes，`VERA_X16` 多了 `exchange_midair`）到 `FTM_HIGH_BSS`，用
`#pragma bss-name`：`level_fade_frame`、`bridge_dropped`、三個 exchange 變數、
`exchange_input_lock`（X16 再加 `exchange_midair`）。新 map：X16 BSS `$62F6-$674C`、
`FTM_HIGH_BSS` `$93A0-$94BC`（堆疊下限 `$94C0`）、FTMDATA 仍是 `$6750`——兩邊各剩 3
bytes；Apple II FTM 的 BSS 結束在 `$674F`、high BSS 結束在 `$94BB`。

證據：`vera/build/shots/x16_pause_restart.wav`（blocking load 修正後重錄：確認音只播完
淡出、stage 讀取期間是真正的數位無聲、接著關卡曲）與 `x16_pause_exit.wav`（淡出期間的
確認音、接著標題畫面）；對應的截圖顯示暫停選單停在 RESTART、重新開始後 HUD 為 `x4`、
EXIT GAME 後回到標題。改完之後兩個 `vera/build` 映像都重新建置過（Apple II 二進位其實
沒變：新的 stop 是 X16 專用）。

判讀 `-Wav` 錄音時要注意：振幅固定、只有兩三個 sample 值的整段訊號是「被卡住的 PSG
語音」，不是錄音瑕疵——PSG 是自主發聲，gain 沒被改寫就會一直響。修正前的錄音之所以
看起來像「約一秒的安靜」，其實既不是安靜也不是音樂，就是那個被凍住的提示音。反之，
stage 讀取期間的長段無聲是真的無聲（用 SOUND mute 交叉驗證過）。`playtest.ps1
-TailSeconds <n>` 可以在最後一個按鍵之後讓模擬器多活 n 秒，錄音才收得到新關卡。


---

## 9. 打包與發行

X16 的發行形式有三種：

1. **多檔案目錄 / HostFS**：`LOADER.PRG` + `GAME` + `MUSIC` + 資產檔。開發期最方便
   （`-fsroot`），**現在已可用**（檔名必須小寫，見 §7.5）。
2. **`.zip`/SD 映像（AutoBoot）**：把上述檔案打包成 SD 卡映像，`X16` 開機自動載入
   `AUTOBOOT.X16`。這是實機發行形式。
3. **瀏覽器（GitHub Pages）**：用官方 X16Community r49 的 WebAssembly 模擬器
   （`x16emu_wasm-r49.zip`，SHA-256 固定）跑同一份 `dist/`。`web/x16/assemble.mjs` 在
   建站時下載發行版、把資產複製成**小寫檔名**加 `manifest.json` 寫進 `x16/game/`；
   `web/x16/app.js` 再用 `FS.writeFile` 把每個檔案放進模擬器虛擬磁碟 `/`，以
   `-prg loader.prg -run` 啟動。頁面在 `/x16/index.html`，`x16emu.data` 內含 X16 ROM，
   所以 `web/x16/` 一併附上 `emulator-license.txt`／`rom-license.md`／`NOTICE.md`。

建議發行名沿用 `vera/` 的 `alter-ego-vera*` 命名規則（例如 `alter-ego-x16.prg` +
`alter-ego-x16.zip`），不要改動既有 release 名稱。

第 3 種發行形式不是另外一份移植：它原封不動地跑 `x16/spike/dist/`，而
`.github/workflows/deploy-web.yml` 的觸發條件包含 `x16/spike/dist/**`，所以只要 X16 的
修正有把重build 的 `GAME` 推上去，瀏覽器版就會自動重新部署。不過不要只憑這點假設，直接
比對線上那份（站上檔名一律小寫）：

```powershell
Invoke-WebRequest https://anomixer.github.io/alter-ego/x16/game/game -OutFile tmp\web-game
(Get-FileHash x16\spike\dist\GAME).Hash -eq (Get-FileHash tmp\web-game).Hash
```

`feb4c1b`（RESTART 提示音修正）已驗證：workflow run `42466205760` 成功，線上的
`x16/game/game` 是 `0398F06A…0B65`，與本機 `GAME` 完全相同。

瀏覽器版（§9 第 3 種形式）跑的就是這個 binary，所以 RESTART 的修正不用另外改就在裡面；
它的 HostFS 讀取比實機/HostFS 快，所以以前被凍住的音比較短，但現在一樣在同一個位置切掉。

---

## 10. 風險清單

| 風險 | 現況（2026-11-06） |
| --- | --- |
| HostFS/DOS 載入路徑（§7） | **已解決**：檔名小寫即可（§7.5）；`-sdcard`／DOS 開機還沒實測 |
| ZP `$9A-$9F` 衝突 | **仍在**：`ftm_envelopes.s` 的 4 個 byte 還在 `$9A-$9F`（X16 的 BASIC ZP），目前沒踩到，屬未爆彈；上實機前建議搬到 `$22-$7F` |
| 中斷風暴 | **已解決**：`VERA_IEN=0x01` ＋ handler 串接 KERNAL `$0314`（見 §7.7 前一段） |
| 節奏（60 Hz 模擬 vs 8 MHz） | **已解決**：VSYNC IRQ frame counter、`logic_delta=1`、每 frame 一個音樂 tick（§8） |
| `$9F00-$9FFF` 越界 | **已解決**：cfg 限制在 `$2000-$9400`，每次 build 檢查 map |
| 資產格式 | 無風險：VERA 4bpp tile/palette 與 Apple II 版是同一個二進位，直接複製 |
| 記憶體 | **高**：主 RAM 只剩 3 bytes（CODE `$5A72`／BSS `$674C`），新功能得先找空隙或砍死碼（`x16/README.md` 的 "Memory headroom"；中文原文 `x16/readme-tw.md` 的「記憶體餘裕」）|

---

## 11. 工作量估計（1 人）

| 階段 | 內容 | 估計 |
| --- | --- | --- |
| A. 打通檔案 I/O | DOS/HostFS 或 SD 映像，讓資產載入成功 | 3–5 天 |
| B. 資產載入層 | `ae_load_raw_asset` / level stream（含 `address==0` 與 bank1） | 2–3 天 |
| C. 輸入 | `input_cx16.s` 對映、鍵盤/搖桿實測 | 2 天 |
| D. 節奏與音樂 | IRQ frame counter、FTM tick 校正、SFX | 3–4 天 |
| E. 記憶體/ZP 整理 | ZP 搬移、cfg 收斂、map 驗證 | 1–2 天 |
| F. 驗證與打包 | 標題→關卡→ending 全流程、SD 映像 | 3–5 天 |
| **合計** | | **約 3–4 週（單人、兼職可能 1.5–2 個月）** |

**實際結果**：A–F 在 2026-11-05～11-06 兩天內做完（不含實機與 SD 映像打包），主要
是因為檔案 I/O 的根因只是檔名大小寫、VERA 層真的 1:1。剩下的就是 §10 的 ZP 未爆彈
與真人長時間試玩。

對照：`time-pilot` 的 CX16→Apple II VERA 版沒有共用 HAL，等於重寫 `main.c`，約 1 人月；
本專案的 `main.c` 已經是 cc65 且 VERA 層 1:1，重用率明顯較高，主要成本集中在平台差異
（檔案 I/O、輸入、中斷）而非遊戲邏輯。

---

## 12. 驗證計畫（可執行的步驟）

1. `powershell -NoProfile -File x16\spike\build.ps1` → 產生 `dist\GAME`、`dist\MUSIC`、
   `dist\LOADER.PRG`、`dist\*.PSG`、`dist\LVxx`。
2. `x16emu -prg x16\spike\dist\LOADER.PRG -run -fsroot x16\spike\dist`
   （或加 `-warp` 加速）→ 觀察 loader 是否走到 `jmp $2000`。
3. `$9FB9` beacon：`User debug 1: $xx` 會印在 emulator console，可當進度燈（本輪用它
   追出 loader 的 'B'/'M'/'J' 與資產層的 'A'/'V'）。
4. VRAM 內容驗證：`-dump V` + `$9FB5=1` + 跳到 `$FFFF`，會產生 `dump.bin`
   （128 KB VRAM + composer + palette + layer 暫存器），可離線比對 `TILES`/`CRPAL`。
5. 截圖：`x16/tools/shot.ps1 -Prg ... -FsRoot ... -Out ...png`（前景截圖，不需模擬器配合）。
6. 按鍵自動化：`x16/tools/playtest.ps1 -KeySequence 'enter,right:2,z,enter'`。
   **合成按鍵要帶真實 scan code 才會進 guest**：`keybd_event(vk, MapVirtualKey(vk,0), flags)`；
   方向鍵還要 `KEYEVENTF_EXTENDEDKEY`（flags=1、放開 flags|2）。這也是早期誤判
   「x16emu 不吃合成按鍵」的原因（`SendKeys`/`SendMessage` 都沒有 scan code）。
   可用的鍵名包含 `t`/`m`/`n`/`one`/`esc`（§7.9 的特殊按鍵）；`-Wav <file.wav>`
   會讓 x16emu 錄音，之後用 `python x16/spike/wavstat.py <file.wav> [窗秒數]`
   看逐段 RMS/peak（腳本強制 kill，wav header 會沒收尾，`wavstat.py` 會先修）。
   注意：playtest 的 `try/finally` 一定會關掉 emulator，否則被 redirect 的 stdout
   會讓呼叫端看起來像卡住。
7. 通關驗證：載入 `LV00`…`LV25`，確認 `load_level_file()` 的 2 B 標頭、512 B 碰撞圖、
   實體 3 B/筆、參數 3 B + 640 B 碰撞圖都與 Apple II 版一致。

---

## 13. 實測結果（本輪留下來的證據）

| 檔案 | 內容 |
| --- | --- |
| `x16/probe/main.c` | VERA 基本測試（顯示模式、palette、tile） |
| `x16/probe/io*.c` | 20+ 支檔案 API / LOAD 行為 probe |
| `x16/probe/shot-io13.png`、`shot-io18.png`、`shot-io19.png`、`shot-io20.png` | LOAD/VERA 位址行為的畫面證據（含 `read`/`read2` 的 palette 值） |
| `x16/probe/shot-io6.png`、`shot-io7.png`、`shot-io11.png` | CHRIN 串流失敗證據（狀態 `0x42`、畫面空白） |
| `x16/spike/` | 完整 cc65 `-t cx16` 建置：`GAME` 29,698 B、`MUSIC` 4,097 B、`LOADER.PRG` 1,026 B |
| `x16/spike/shot-title-final.png` | X16 上的標題畫面（`ALTER EGO` + 四行選單 + 星空） |
| `x16/spike/shot-level1-plays.png` | X16 上的 Level 1（`HELLO WORLD`、HUD `5`/`x2`、磚台、敵人、水） |
| `x16/spike/play-1-enter.png` … `play-5-enter.png` | 實際操作序列：進關卡 → 方向鍵右移 2 秒 → `Z` 交換（HUD `x2`→`x1`）→ `Enter` 暫停（RESUME/RESTART/EXIT GAME）→ `Enter` 恢復 |
| `x16/spike/menu-1-down.png` … `menu-5-enter.png` | 標題選單 Down/Right 選到 START LEVEL 03 → `Enter` 載入「BROKEN BRIDGE」 |
| `x16/spike/shot-credits-x16.png` | 開機 credits：最後兩行是 `COMMANDER X16 CONVERSION BY` / `ANOMIXER 2026`（§7.8） |
| `x16/spike/shot-input-right.png` | 方向鍵按住移動（按住即連續、不在第 8 frame 後停頓） |
| `x16/spike/shot-input-exchange-fall.png` | `right+z:3`：走過平台邊緣掉落時交換，HUD `x2`→`x1`、兩隻 Ego 對調、Z 按住 3 秒只花一次 |
| `x16/spike/ma-3-z.png`、`fx-3-z.png` | 修正 §7.10 之後：掉落中按下 `Z` 的第一個 frame 就開始交換（HUD `x2`→`x1`）|
| `x16/spike/mb-3-x.png` | 同一段掉落改用 `X`（A 鍵）也是第一個 frame 就交換 |
| `x16/spike/g1-3-z.png` | §7.11 修正後（出貨版）：LV01 掉落中 `Z` 交換，落地後站在地面上（HUD `x2`→`x1`）|
| `x16/spike/g24-27-z.png` | §7.11 修正後：LV24（垂直鏡像）掉落到主平台高度時 `Z` 交換，主角站在主平台上面（HUD `x6`→`x5`）|
| `x16/spike/fallswap_sim.py` | 從 `dist/LVxx` 重建碰撞圖重播掉落／交換幾何：修正前 756／65,667 個情境會卡進方塊，修正後 0 |
| `x16/spike/gate_cx16.s` | 主 RAM 區塞不下的 `ae_midair_ok()`（放在 `GATE` 段 `$92DC`，見 §7.11）|
| `web/x16/`、`web/x16/assemble.mjs` | 瀏覽器版：官方 r49 wasm 模擬器（下載後比對 SHA-256）＋ `dist/` 的小寫檔名＋`manifest.json`；`web/build-site.mjs` 把它併進 `web/_site/x16/` |
| `x16/spike/web-title.png`、`x16/spike/web-level1.png` | 瀏覽器版的標題畫面與 Level 1（headless Edge 送 `Enter` 後截圖；`HELLO WORLD`、HUD `x5`／`x2`），證明 wasm 版的 HostFS、鍵盤事件與 VERA 輸出正常 |
| `x16/spike/irq-1-after-enter.png` | 修正「KERNAL IRQ 來源是 VERA VSYNC」後，`Enter` 第一次成功進關卡 |
| `x16/spike/shot-soundtest.png` | 標題按 `T` 開 SFX/BGM 測試畫面（`SFX 00 BGM 1`，右鍵切 BGM 模式）|
| `x16/spike/shot-mute-keys.png` | `M`、`N` 兩個靜音鍵：標題同時顯示 `MUSIC OFF` 與 `SOUND OFF` |
| `x16/spike/shot-cow-level.png` | 標題 `1`（SELECT）+ `Enter` → `COW LEVEL`（level 0）|
| `x16/spike/shot-level-skip.png` | 跳關密技 `z,left,x,z,left,x` + `Enter` + `1` → `LEVEL CLEAR` |
| `x16/spike/wavstat.py` | wav 修 header + 逐段 RMS/peak 分析（`-Wav` 抓到的音訊證據，§7.9）|
| `x16/spike/tritrace.py`、`bytrace.py` | 解析 `AE_DEBUG_XY`（x/y/pad）與 `AE_DEBUG_FALL`（1 byte：`y`+`pad`）的 `User debug 1` beacon（§7.10）|
| `x16/tools/shot.ps1` | 自動截圖工具（列舉 x16emu 自身 PID、設 HWND_TOPMOST，避開 console 窗） |
| `x16/tools/playtest.ps1` | 送鍵＋截圖的自動化腳本（真實 scan code、`KeySequence`、`right+z` 同時按、前景搶奪失敗會直接報錯、`-Wav` 錄音、`-TailSeconds` 在最後一鍵之後讓模擬器多活幾秒） |

**已完成**：標題畫面渲染、Level 1 載入與渲染、資產載入（小寫檔名）、
`read()` 位址保留、X16 鍵盤/手把輸入層（含 KERNAL IRQ 與 VSYNC 節奏修正，§8）、
掉落中交換（§6）、掉落中的交換改成每個 frame 都檢查（§7.10）、中途交換落點對齊格子與
「垂直鏡像關卡的鏡像點要有地板」（§7.11）、credits 平台行（§7.8）、特殊按鍵 T/M/N/ESC
與 cow level／跳關密技（§7.9）、瀏覽器版（官方 wasm 模擬器＋GitHub Pages，§9），並用按鍵
自動化走過一輪關卡內操作。
**未完成**：真人手感的長時間確認（死亡／換關流程只做了渲染驗證）、26 關裡只實玩了
LV01／LV03／LV24（其餘載入路徑相同）、`ftm_envelopes.s` 的 ZP 從 `$9A-$9F` 搬離
BASIC ZP 區（目前能跑，屬未爆彈）、DOS/SD 打包發行。

---

## 14. 給後續接手者的建議順序

1. 真人用鍵盤／手把玩一次 Level 1（`Enter` = START、方向鍵移動、`Z`/`X` = A/B），
   確認 `keyboard_pad()` 的 X16 分支手感與死亡／換關流程。
2. 把 `ftm_envelopes.s` 的 ZP 從 `$9A-$9F` 搬到 `$22-$7F`（目前 X16 build 還能跑，
   但 `$9A-$9F` 在 X16 是 BASIC 的 ZP 區，屬未爆彈）。
3. （已做）`$0314/$0315` VSYNC frame counter：見 §8；後續可拿它量測 60 Hz 節奏與
   音樂 tick 是否穩定。
4. 打包（`.zip`/SD 映像），把 `dist` 的資產與 `GAME`/`MUSIC`/`LOADER.PRG` 裝進
   X16 的 DOS 檔案系統，確認不靠 HostFS 也能跑。
5. 之後才是可選項：把 `io_cx16.c` 的 VRAM staging 改成 banked RAM 緩衝，省掉
   `$A000-$BFFF` 與 staging 位址互踩的風險。

---

## 15. 參考

- 本 repo：`vera/AGENTS.md`（Apple II VERA 版建置與現況）、`vera/src/a2vera/main.c`、
  `vera/build/build_a2vera.ps1`
- cc65：`C:\dev\cc65\lib\cx16.lib`、`cfg\cx16.cfg`（`STARTADDRESS $0801`、ZP `$22-$7F`、
  `__HIMEM__ $9F00`、`__STACKSIZE__ $0800`）
- X16 官方文件：`C:\dev\emu\x16emu`（`readme.txt`、`prg.txt`：VERA 暫存器、KERNAL
  `LOAD/SETNAM/SETLFS`、`joystick_get`、`memory_copy/fill`）
- 參考移植：`C:\dev\time-pilot\TimePilot-CX16` ↔ `TimePilot-IIvera`（無共用 HAL、單檔
  `main.c` 改寫）、`C:\dev\x16-hero-vera`（LLVM-MOS）、`C:\dev\cx16-othello-vera`
- 社群範例：<https://github.com/mwiedmann/cx16CodingInC>（X16 C 範例與 VERA 用法）
