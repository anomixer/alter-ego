# 把 a2vera 遊戲移植到 Commander X16 — 工作指引

> 英文版：[`A2VERA-to-CX16.md`](A2VERA-to-CX16.md)。本檔是 2026-11-06 的繁體中文版，內容與英文版
> 相同；改動請兩邊一起改（A2VERA-to-CX16.md 是英文主檔，本檔是中文版）。

這份清單是從 Alter Ego 的移植（Apple II + VERA → Commander X16，2026-11-05/06）沉澱出來的，每一節
指到的參考實作都在 [`x16/`](../)：`x16/spike/asset_cx16.c`、`input_cx16.s`、`gate_cx16.s`、
`loader.s`、`game.cfg`、`build.ps1`，完整記錄在 [`PORT-CX16-EVAL.md`](PORT-CX16-EVAL.md)（中文原文
`PORT-CX16-EVAL-tw.md`）。

它假設來源專案長得像一個典型的 **a2vera** 遊戲：cc65 C（`main.c`）加 ca65 組語（`title.s`、
`oam.s`、`music_*.s`、`ftm_*.s`、`input.s`），VERA 在 slot `$C200/$C400`，用 ProDOS
`open/read/close`，靠 Applesoft/Monitor ROM，`input.s` 讀 `$C000`/`$C010` 和遊戲埠 PB0/PB1/PDL，
再用一個 `STARTUP.BAS` BLOAD 音樂、BRUN 遊戲。下一個要移植的目標是 `freegemas` a2vera，所以這份
指引的重點是「Alter Ego 的每個零件是怎麼被改寫的」，而不是 Alter Ego 本身的細節。

**先講結論**：VERA 層几乎可以原封不動搬過來（同一顆晶片、同一組暫存器，只有 base 位址不同），真正
的工作是五件事——**檔案 I/O、開機鏈、輸入、影格節奏，以及零頁/記憶體預算**。第一次移植請抓三到四
週，大部分時間會花在前兩項。

---

## 0. 一張表看完「什麼變、什麼不變」

| 層 | Apple II + VERA | Commander X16 | 工作量 |
| --- | --- | --- | --- |
| VERA 暫存器 | base `$C200`/`$C400` | base `$9F20` | **改巨集** |
| 畫面/圖磚/精靈/PSG 邏輯 | — | 完全相同 | 無 |
| CPU | 6502/65C02 @ 1 MHz | 65C02S @ 8 MHz | 無（但要留意時序） |
| 主 RAM | 48–64 KB 線性 | `$0000-$9EFF` 固定，`$A000-$BFFF` 分頁 | 要驗證 linker map |
| I/O | `$C000-$CFFF` 插槽 | `$9F00-$9FFF` | **改寫讀取** |
| 檔案系統 | ProDOS MLI | KERNAL `LOAD`（HostFS / DOS） | **重寫** |
| 開機 | `STARTUP.BAS`（BLOAD/BRUN） | `$0801` PRG loader，`-prg -run` | **重寫** |
| 鍵盤 | `$C000` latch、`$C010` strobe | KERNAL `GETIN` + `joystick_get` | **重寫** |
| 中斷 | 直接輪詢 VERA VSYNC | KERNAL IRQ 就是由 VERA VSYNC 驅動 | **重做** |
| 音樂時序 | 約 40 迴圈/秒，1.5× 補償 | VSYNC 鎖 60/秒，不需要補償 | **把補償拿掉** |

---

## 1. 動手改之前：先盤點

### 1.1 量一次 Apple II 版本

帶 map 檔建置一次，記下：

- `CODE`/`BSS` 的範圍與最高位址（必須塞得進 `$9EFF` 以下）；
- 零頁用法（`$00-$FF`），特別是 `$9A-$9F` 上的東西（`ftm_envelopes.s` 用了那裡，而 X16 的
  `$9D-$A8` 是保留區——見 §4）；
- 資產清單與大小（`TILES`、調色盤、title/credits、關卡檔、音樂）；
- 所有 Apple II 專屬的程式路徑（善用 grep）：`$C0`、`PEKA`/`poke`、`open(`、`read(`、`close(`、
  `STARTUP`、`KBDSTRB`、`keyboard_model`、`iobuf`。

### 1.2 grep 出平台相依

```text
$C000  $C010  $C020  $C030  PDL  pdl  KBD  KBDSTRB  ROM  Monitor
open  read  close  SETNAM?  ProDOS  MLI
text  gotoxy  print  BASIC
```

每一個命中不是改寫，就是用 `#ifndef VERA_X16` 包起來（在 X16 上是死碼，順便省記憶體——§4）。

### 1.3 列出用到的 VERA 功能

Layer 0（圖磚或點陣）、精靈/OAM、調色盤、PSG 聲道、H/V 捲動、縮放（`DC_HSCALE/VSCALE`）、IRQ
用法。這些全部可以搬，只有 base 位址換掉。如果遊戲用點陣模式，注意 tile base 位址：X16 開機時
layer 0 已經有預設值，`L0_CFG/MAP/TIL` 一定得自己覆寫，不能「繼承」。

### 1.4 決定機器假設

512 KB 分頁 RAM 一定在；X16 開機時磁碟裡不一定有 DOS。除非你要附 SD 卡映像，否則不要假設
cmdr-dos 在——HostFS（模擬器的 `-fsroot`）和 DOS 是兩個完全不同的世界（§5）。

---

## 2. 工具鏈與建置旗標

用同一個 cc65（2.19），只換 target：

```powershell
ca65 --cpu 65C02 ...                 # 原本是 --cpu 6502（X16 是 65C02S）
cl65 -t cx16 -Oirs -DVERA_BASE=0x9F20 ...
```

- `-t cx16` 會給你 `cx16.lib` + `cx16.cfg`（`STARTADDRESS $0801`、ZP `$22-$7F`、
  `__HIMEM__ $9F00`、`__STACKSIZE__ $0800`）。把 RAM 區改在自己的 `game.cfg`，例如
  `RAM: load = $2000, type = rw;`，細節看 §4。
- **同一份原始碼要能兩邊編**：每個改動都用 `#ifdef VERA_X16` 包起來，`-t apple2` 繼續能編。最後
  把兩種編法各產一份 listing 比對（Alter Ego 的驗收標準是「6,166 條指令、0 行差異」——§9）。
- VERA 巨集：base 只定義一次。

```c
#ifdef VERA_X16
#define VERA_BASE 0x9F20
#else
#define VERA_BASE 0xC200
#endif
```

如果 a2vera 專案是在 ca65 巨集裡用，就改成傳 `-D VERA_BASE=$9F20`。注意 **`.s` 檔裡的
`VERA_BASE` 是組譯器常數**，而 `main.c` 用的是 `-DVERA_BASE=0x9F20`——兩種拼法要同步。

---

## 3. VERA 層

同一顆晶片、同一組偏移，只有 `$C200`/`$C400` 變成 `$9F20`：

| 用途 | Apple II | X16 |
| --- | --- | --- |
| 位址 low/mid/high | base+$00/$01/$02 | `$9F20/$9F21/$9F22` |
| Data 0/1 | base+$03/$04 | `$9F23/$9F24` |
| Control | base+$05 | `$9F25` |
| IRQ enable/status | base+$06/$07 | `$9F26/$9F27` |
| 顯示模式 | base+$29 | `$9F29` |
| Layer0 cfg/map/til | base+$2C/$2D/$2E | `$9F2C/$9F2D/$9F2E` |
| 捲動 | base+$2F/$30 | `$9F2F/$9F30` |
| OAM / PSG / 調色盤 | `$1FC00` / `$1F9C0` / `$1FA00` | 相同 |

Alter Ego 移植時最花時間的三個地雷：

1. **`VERA.address` 只有 16 bit，會把第 17 個位址位元吃掉。** `cx16.h` 提供 `VERA.address`
   （16 bit）和 `address_hi`（bit 0 是 A16、bit 6-4 是增量）。寫 `VERA.address = 0x10000` 會
   靜靜變成 0。正確寫法：

   ```c
   VERA.address = addr & 0xFFFF;
   VERA.address_hi = 0x10 | ((addr >> 16) & 1);   /* + increment bits 6-4 */
   ```

2. **`struct __vera` 沒有 `video` 欄位**，所以 `VERA.video` 編不過；請用
   `*(volatile unsigned char *)0x9F29`。

3. **`DC_VIDEO` 的 `0x01` 只是輸出模式**（VGA）；要 VGA + layer 0 + 精靈得用 `0x51`。Apple II
   版本的 `0x51` 仍然是對的，但如果你是自己算這個值，別忘了 layer 位元。

其餘的——調色盤寫入、圖磚表、OAM、PSG——都可以從 Apple II 版本原封不動複製過來。

---

## 4. 記憶體地圖、零頁，以及最後的 6 bytes

X16 記憶體：

```
$0000-$9EFF   固定 RAM（你的程式必須塞在這裡）
$9F00-$9FFF   I/O（VERA 在 $9F20-$9F3F、SMC 等）—— 絕對不要碰
$A000-$BFFF   512 KB 分頁 RAM（bank 由 $00 選擇；cc65 有自己的 bank）
$C000-$FFFF   ROM（BASIC/KERNAL）
```

X16 的零頁：`$02-$21` 是 r0-r15，`$22-$7F` 給 cc65 用，`$80-$9C` 是 KERNAL/DOS，`$9D-$A8`
**保留**，`$A9-$D3` 是數學函式庫，`$D4-$FF` 是 BASIC。

- 如果移植過來的常數放在 `$9A-$9F`（Alter Ego 的 FamiTone envelope 就是），把它們搬進
  `$22-$7F` 並在 linker config 裡保留起來。Alter Ego 現在仍然跑在 `$9A-$9F`，但那是潛在 bug
  ——上實機前該改。
- 給 BSS 留一點餘裕。Alter Ego 的 `game.cfg` 最後只剩 **6 bytes** 空間；這很正常，也是下一節
  存在的理由。

### 4.1 不改 Apple II 版本也能擠出記憶體

兩個技巧，`x16/` 兩個都用了：

1. **把 Apple II 的死碼包起來。** `KEYBOARD`/`KBDSTRB`/`keyboard_model` 區塊、
   `keyboard_level_reset`、暫停選單的 latch 測試——外面包 `#ifndef VERA_X16`。Alter Ego 因此
   回收了約 96 B 的 CODE 和 3 B 的 BSS。
2. **空洞區段（hole segment）。** 某個函式的 C 版塞不下時，用組語寫，丟進 linker map 的空洞
   （Alter Ego 的 `gate_cx16.s` 放在 `$92DC`，剛好在 `FTMTABLE` 和 `FTM_HIGH_BSS` 之間）：

   ```text
   GATE: load = RAM, type = ro, start = $92DC;
   ```

   找空洞的方法：讀 map 檔（`ld65 -m game.map`），看區段之間哪裡有空隙——然後確認那塊在 loader
   映像裡真的是空的（loader 是整份映像載入、含 padding，所以 `fill = yes` 的映像沒問題）。

每次建置都用 map 檢查：`ld65: Segment 'BSS' overflows memory area 'BSS' by N bytes` 的意思是
「砍死碼或找空洞」，不是「把區域放大」。

---

## 5. 檔案 I/O：KERNAL LOAD 與 HostFS

重寫資產層（Alter Ego：`x16/spike/asset_cx16.c` + `kload_cx16.s`）。流程是：

```c
/* 一個檔案，無檔頭，載到指定位址/bank */
ae_load(name, sa, addr, bank);       /* SETNAM/SETLFS，然後 jsr $FFD5 */
```

幾個真正重要的實作細節：

1. **檔名一定要小寫。** x16emu r49 的 HostFS 是逐 byte 比對 `SETNAM`，所以 `"GAME"` 會回
   `A=4`（FILE NOT FOUND），`"game"` 才載得到。在你送出名稱的地方就轉小寫（`asset_cx16.c` 的
   `ae_lname()`）；Apple II 那邊可以保留大寫檔名。
2. **`LOAD` 回的 carry 旗標不可信**——成功時它也是設著的（`P=31`）。要檢查 `A`
   （0 = OK、4 = 找不到……），不要用 `bcs fail`。
3. **`SA=2` 是對 VRAM 友善的形式**（無檔頭，位址在 `X/Y`，bank 在 `A`）：用它把調色盤或圖磚表
   直接載進 `$1xxxx`。`SA=1` 期待 2 byte 檔頭；`SA=3` 是 bank1。Alter Ego 的資產是 `SA=2`、
   `A=3`，目的地是 `$1FA00` 這一類。
4. **目的位址 `$0000` 不被接受。** 先載到 `$A000` 再複製，`ae_load_raw_asset()` 就是這樣做。
5. **遮蔽中斷、切 `RAM_BANK=1`** 再載（如果你在分頁 RAM 裡暫存），之後還原；結尾要 `CLRCHN`
   （`$FFCC`），否則 `GETIN` 會繼續從檔案讀，而不是從鍵盤。
6. **不要讓你的 `read()` 把 VERA 位址蓋掉。** 關卡串流時 `read()` 被呼叫，而
   `load_level_file()` 同時在寫 `VERA_DATA0`；每次讀 byte 前後存回
   `VERA.address`/`address_hi`，就是 Alter Ego 黑畫面的解法（`x16/spike/io_cx16.c`）。
7. **HostFS vs DOS：** `-fsroot` 是開發用；正式發行請把檔案放進 SD 映像、走 DOS。`-sdcard`
   最接近實機。

骨架（參考實作的簡化版，不是可直接編譯的成品）：

```c
/* asset_cx16.c — 參考實作另外控制 $B9（RAM bank），並在組語裡做 LOAD，
 * 所以暫存區和 bank 都在自己手上。 */
static char ae_name[16];

extern unsigned char ae_kload(unsigned char sa, unsigned int addr);  /* jsr $FFD5 */

static void ae_lname(void) {                    /* HostFS 比對 SETNAM bytes */
    for (char *p = ae_name; *p; ++p)
        if (*p >= 'A' && *p <= 'Z') *p = (char)(*p + ('a' - 'A'));
}

unsigned char ae_load(const char *name, unsigned char sa,
                      unsigned int addr, unsigned char bank)
{
    unsigned char i = 0, st;
    while (name[i] && i < 15) { ae_name[i] = name[i]; ++i; }
    ae_name[i] = 0;
    ae_lname();
    __asm__("sei");
    *(volatile unsigned char *)0x00 = bank;     /* RAM_BANK */
    cbm_k_setlfs(2, 8, sa);                     /* channel 2、device 8、SA */
    cbm_k_setnam(ae_name);
    st = ae_kload(sa, addr);
    ae_clrchn();                                /* GETIN 交還給鍵盤 */
    __asm__("cli");
    return st;                                  /* 0 = OK、4 = FILE NOT FOUND */
}
```

```asm
; kload_cx16.s — 唯一的魔法就是 "jsr $FFD5"
; in: A = secondary address、X/Y = 載入位址、$B9 = RAM bank
_ae_kload:
        jsr     $FFD5
        rts                 ; A = 狀態（0 = OK）；carry 不可信
```

暫存器慣例請直接看 `x16/spike/kload_cx16.s`，以及 `x16/spike/loader.s` 裡的 loader（
`music_name: .byte "music"`、`game_name: .byte "game"`）。

---

## 6. 開機鏈

Apple II 的 `STARTUP.BAS`（BLOAD 音樂 → BRUN 遊戲）換成**帶 BASIC `SYS` stub 的 `$0801` PRG**：

```basic
10 SYS 2061
```

stub 只是為了讓 `-prg loader.prg -run` 和 `LOAD "loader.prg",8,1` + `RUN` 都能用。loader 接著：

1. `LOAD "music",8,1` 到 overlay 位址（Alter Ego 是 `$1000`），
2. `LOAD "game",8,1` 到 `$2000`（這裡用 2-byte 檔頭形式沒問題），
3. `jmp $2000`。

把開機鏈弄起來的時候，每個階段丟一個 `$9FB9` beacon 字母——那是模擬器給你的最便宜進度燈（§10）。

發行時，要嘛留一個目錄 + `AUTOBOOT.X16`，要嘛做一個 SD 映像、把同樣的檔案用**大寫**檔名放進去
（DOS 不需要 HostFS 的小寫規則——但要實測）。

---

## 7. 輸入

換掉 `input.s`。在 X16 上：

- **`joystick_get`（`$FF56`）的 device 0 是 KERNAL 鍵盤搖桿**，反映當下按住的狀態——方向鍵和
  A/B 都用它。回傳 `Y=0` 表示存在；SNES 手把是 device 1-4（`Y=$FF` = 未接）。
- **方向鍵和 A/B 要做成 level-sensitive**；**START/SELECT 要是上升緣的單 frame 脈衝**（否則
  `Enter` 每 frame 都會重新打開暫停選單）。重複觸發的防抖動交給遊戲邏輯（Alter Ego 的
  `exchange_input_lock`），不要放在輸入層。
- **把舊的「按住計時器」補償刪掉。** 在 X16 上讀 `$C000`/`$C010` 拿到的是 ROM 內容：`$C000`
  讀起來是常數，結果變成「某個方向永遠按住」。如果你保留鍵盤事件當 fallback（`Space`、`1`、
  特殊鍵），那沒問題，但鍵盤搖桿存在時不要讓 fallback 跑。
- **金手指序列：** 不要每 frame 比 `pad == code[i]`——按住的按鈕下一 frame 仍然相等，索引會被
  重置。改成數**變化**：

  ```c
  static unsigned char code_last_pad;
  ...
  if (pad != code_last_pad) {          /* 一次按鍵算一步 */
      code_last_pad = pad;
      if (pad == code[code_index]) { ... }
  }
  ```
- 每次 KERNAL `LOAD` 之後、呼叫 `GETIN` 之前要 `CLRCHN`（§5 第 5 點）。

鍵盤事件仍然有約 0.5 秒的自動重複延遲，這就是為什麼 Alter Ego 的 X16 版砍掉 `WASD`、改用
鍵盤搖桿移動。

---

## 8. 影格節奏與音樂——最常讓人意外的一節

**X16 的 KERNAL 60 Hz 中斷是由 VERA VSYNC 中斷驅動的。** 如果你清掉 `VERA_IEN` 去輪詢
`VERA_ISR`（從 Apple II 版本照抄過來非常自然），KERNAL 中斷會整個停掉：jiffy 時鐘凍結、鍵盤
掃描停止、`GETIN` 永遠回 0，看起來就像「按鍵全死了」。

正確做法：

1. 把 KERNAL IRQ 串起來，不要取代它：

   ```asm
   _ae_irq_install:
           lda     $0314
           sta     _old_irq
           lda     $0315
           sta     _old_irq+1
           lda     #<_ae_irq
           sta     $0314
           lda     #>_ae_irq
           sta     $0315
           rts
   _ae_irq:
           inc     _ae_irq_frames          ; 16-bit 影格計數器
           bne     forward
           inc     _ae_irq_frames+1
   forward:
           jmp     (_old_irq)
   ```

2. X16 上的 `vera_sync_init()` 只做 `VERA_ISR = 0x0F; VERA_IEN = 0x01;` 再掛上 hook；
   `ISR` 的清除交給 KERNAL 原本的處理。
3. `wait_frame()` 等 `_ae_irq_frames` 變化（或用 KERNAL 的 jiffy）。

接著要處理**時序補償**：慢的 Apple II 迴圈通常把遊戲邏輯跑成「每圈 1.5 個 NES step」、音樂
「每圈 1.5 個 source tick」。在 VSYNC 鎖定的 X16 60 Hz 迴圈上，這會變成 **1.5 倍太快**（主角
走 ≈90 px/s 而不是 60）。兩處都用 `#ifdef VERA_X16` 包起來，改成每 frame 一個 step／一個 tick。
驗收方法：量走路速度（px/s），跟 NES 原版比。

如果改完覺得「有一點點慢」，加一個 **tempo trim**，用 8-bit 累加器（每 frame 1/256 tick），
而不是改 tick 頻率——這樣不會長期漂移：

```c
temp_tempo += AE_X16_TEMPO_TRIM;      /* 8 ≈ +3.1% */
if (temp_tempo >= 256) { temp_tempo -= 256; extra_tick = 1; }
```

---

## 9. X16 移植通常會需要的行為修正

Alter Ego 有三個 Apple II 版本從沒出現過的遊戲感 bug，模式可以推廣：

1. **「只有 1/N frame 會吃到按鍵。」** NES 原版只在玩家沒在移動時檢查交換；掉落的過程，那是每
   8 px 一排才一個 frame。Apple II 上 `$C010` 的 any-key 旗標（level-sensitive）剛好蓋住那個
   frame；X16 上換成脈衝就只剩 1/8 的機率。解法：每 frame 都檢查，**放在 `#ifdef VERA_X16`
   裡**。
2. **「空中動作之後穿地板。」** 動畫若凍結在兩排圖磚之間，會留下非零的 step 計數，下一拍重力
   就跳過地板測試。解法：動畫結束時把位置對齊回那一排、把 step 計數歸零。
3. **「傳送後掉進牆裡。」** 垂直鏡像關卡（`y = 240 - y`）可能鏡像到實心圖磚上。解法：只有在
   目的地有地板時才允許傳送，否則繼續掉落、等到第一個合法 frame 再切換。

每個修正都放在 `#ifdef VERA_X16` 裡，然後證明 Apple II 版本沒動：

```powershell
cl65 -t apple2 --cpu 6502 -Oirs ...   # 舊版與新版各產 listing
# 指令數相同、0 行差異，只多出 .export 行
```

再寫一個**幾何模擬**跑過關卡資料（`x16/spike/fallswap_sim.py` 對 Alter Ego 做的就是這件事：
65,667 種情況，修正前 756 次穿地板、修正後 0 次）。它一秒跑完、不需要模擬器，也是確認「有時
會穿地板」這種 bug 真的消失的唯一方法。

---

## 10. 驗證與自動化

- **Beacon：** 寫 `$9FB9` 會讓 x16emu 在 stdout 印 `User debug 1: $xx`——loader 和資產層的
  免費進度紀錄。需要 frame 對齊時，把 payload 壓成一個 byte（每 frame 三個 byte 偶爾會掉）。
- **VRAM dump：** `-dump V` + `$9FB5=1` + 跳到 `$FFFF` → `dump.bin`（128 KB VRAM + composer +
  調色盤 + layer 暫存器），可以跟資產逐 byte 比對。
- **截圖：** 前景 `PrintWindow`/`BitBlt` 截圖可行；不需要模擬器配合（`x16/tools/shot.ps1`）。
- **合成按鍵要真掃描碼：** `keybd_event(vk, MapVirtualKey(vk, 0), flags)`。`SendKeys`/
  `SendMessage` 不帶掃描碼、永遠到不了 guest；方向鍵還要 `KEYEVENTF_EXTENDEDKEY`（按下 `1`、
  放開 `|2`）。要搶前景、並確認真的搶到（`GetForegroundWindow() == hwnd`），沒搶到就大聲失敗
  ——否則你拍到的是別人的視窗。
- **一定要在 `try/finally` 裡殺掉模擬器：** 留下一個 stdout 被重導的行程，會讓呼叫端看起來
  永遠卡住。
- **音訊：** `-Wav <file.wav>` 會錄音；強制砍掉行程會讓 RIFF 長度沒寫回去，分析前要先補
  （逐段 RMS/peak）——`x16/spike/wavstat.py`。

驗收清單（Alter Ego 的，可以直接沿用）：

| 檢查 | 方法 |
| --- | --- |
| 開機到標題 | `-prg LOADER.PRG -run`，截圖 |
| 所有資產都到位 | VRAM dump 對照 host 檔案；每個資產一個 beacon |
| 第 1 關可顯示、可玩 | Enter → 方向鍵 → 動作 → 暫停選單 |
| 特殊鍵/金手指 | `T`/`M`/`N`/`1`、金手指序列、截圖 |
| 音樂與音效 | `-Wav` + 逐段 RMS/peak |
| 節奏 | 走路 px/s 對照 NES 原版 |
| 兩種版本都能編 | `-t cx16` 與 `-t apple2`，Apple II listing 差異 = 0 |
| 無頭煙霧測試 | 按鍵 + 截圖，不需要人手點 |

---

## 11. GitHub Pages 瀏覽器版（選配但很便宜）

Alter Ego 的 `web/x16/` 把真正的 `dist/` 跑在官方 X16Community WebAssembly 版本上：

1. 釘住版本（`x16emu_wasm-r49.zip`）與它的 **SHA-256**；在組站時下載 + 驗證，快取在
   gitignore 的目錄，壓縮檔永遠不進版控。
2. 把資產檔**轉小寫**複製到 `site/x16/game/`，再加一份 `manifest.json` 列出它們（§5 的大小寫
   規則在這裡同樣成立——瀏覽器檔案系統大小寫敏感）。
3. `Module` 設定：`arguments: ['-prg', 'loader.prg', '-run', '-ram', '512', ...]`、
   `locateFile: n => 'emulator/' + n`，以及一個 `preRun` 逐一抓檔並
   `FS.writeFile('/' + name, bytes)`，然後移除 run 的 dependency。
4. 音訊需要使用者手勢：呼叫 wasm 的 hook（`j2c_start_audio`），只有在
   `Module.SDL2.audioContext.state === 'running'` 之後才回報「聲音開了」。
5. 把模擬器/ROM 的授權文字放在頁面旁邊；ROM 不是開源，只是授權給 X16 使用。

整個東西大約 200 行 JS 加 60 行建置腳本；看 `web/x16/`。

---

## 12. 打包

| 形式 | 時機 | 注意 |
| --- | --- | --- |
| 目錄 + `-fsroot` | 開發 | 小寫檔名（HostFS） |
| `AUTOBOOT.X16` 目錄 | 交給別人 | 仍然依賴 HostFS/DOS |
| `.zip` / SD 映像 | 發行 | DOS 上大寫檔名沒問題；要上實機測 |

產物名稱要穩定、帶版本（`<game>-x16-…`），而且永遠不要改掉已發行的名字。

---

## 13. 症狀對照表

| 症狀 | 原因 | 解法 |
| --- | --- | --- |
| 「按鍵全都沒反應」 | `VERA_IEN` 被清零 → KERNAL IRQ 死 → `GETIN` 永遠 0 | 串接 `$0314/$0315`，`IEN` 絕不清零（§8） |
| 標題畫面全是條紋/雜訊 | 資產根本沒載入 | `SETNAM` 檔名轉小寫（§5） |
| 進關卡黑畫面 | `read()` 在寫入中途重設 `VERA.address` | 在 `read()` 前後存回 VERA 指標 |
| `LOAD` 回 `A=4` | 檔名大小寫 | 名稱轉小寫 |
| `LOAD`「失敗」但資料正確 | carry 永遠是 1 | 測 `A`，不要測 carry |
| `$0000` 的資產不見 | KERNAL LOAD 不接受位址 0 | 暫存到 `$A000` 再複製 |
| load 之後 `GETIN` 回垃圾 | 輸入通道還指向檔案 | 每次 load 後 `CLRCHN`（`$FFCC`） |
| 點一下走過頭一格 | 舊的按住計時器補償 | 刪掉它；改用鍵盤搖桿 |
| 動作 8 次只吃到 1 次 | 只在落地 frame 檢查 | 每 frame 檢查，放進 `#ifdef VERA_X16` |
| 空中動作後穿地板 | 動畫凍結在兩排之間、step 計數留下 | 對齊回那一排、計數歸零 |
| 傳送後掉進牆裡 | 鏡像目的地沒有地板 | 驗證目的地，等合法 frame 再切 |
| 全部動作快了約 1.5 倍 | 把 Apple II 的「1.5 step/tick」補償帶過來 | `logic_delta=1`、每 frame 一個 tick |
| `ld65: BSS overflows by N bytes` | 新程式塞進已滿的 RAM 區 | `#ifndef` 砍死碼，或用空洞區段（§4） |
| 開機後行為錯亂 | 誤寫 `$9F00-$9FFF` | 限制 linker 區域，檢查 map |
| `DCL`/`video` 編不過 | `struct __vera` 沒有 `video` | `*(volatile unsigned char *)0x9F29` |
| 畫面偏移/空白 | `DC_VIDEO` 少了 layer 位元 | 用 `0x51` |
| 按鍵正常但暫停每 frame 重開 | START 是 level-sensitive | START/SELECT 改上升緣 |
| 金手指要 frame-perfect 才輸入得了 | 用「按住等於密碼」比對 | 改成數 pad 變化 |
| 音樂愈跑愈慢/快 | 用 tick 頻率調速度 | 用 1/256 累加器 |

---

## 14. 工作順序與工期

| 步驟 | 內容 | 時間 |
| --- | --- | --- |
| 1 | 盤點、工具鏈、VERA base、記憶體地圖 | 1–2 天 |
| 2 | KERNAL LOAD 資產層 + 小寫檔名 | 3–5 天 |
| 3 | 開機鏈（loader PRG） | 1–2 天 |
| 4 | 輸入層（joystick_get、edge/level） | 2 天 |
| 5 | VSYNC IRQ 節奏 + 音樂 tick 修正 | 3–4 天 |
| 6 | 記憶體/零頁整理 | 1–2 天 |
| 7 | 行為修正 + 模擬驗證工具 | 2–4 天 |
| 8 | 端到端驗證、截圖、音訊 | 3–5 天 |
| 9 | 瀏覽器版、打包 | 2–3 天 |

Alter Ego 的 1–8 步兩天就做完，因為 VERA 層真的 1:1；換成規模大一點的 a2vera 遊戲，請抓三到
四週。像 freegemas 這種，資產型態更多、也有自己的時序假設——那些要在第 1 步重新量，不要照抄這裡
的數字。

---

## 15. 這個 repo 裡要對照哪個檔案

| 問題 | 檔案 |
| --- | --- |
| 當初的計畫、順序、風險清單 | `x16/docs/PORT-CX16-EVAL.md` |
| 資產層骨架、小寫檔名、暫存 | `x16/spike/asset_cx16.c` |
| `jsr $FFD5` 包裝 | `x16/spike/kload_cx16.s` |
| 關卡串流、VERA 位址存回 | `x16/spike/io_cx16.c` |
| 鍵盤搖桿、按鍵對應、IRQ 計數 | `x16/spike/input_cx16.s` |
| loader 與 overlay 開機 | `x16/spike/loader.s`、`loader.cfg` |
| linker 區域、空洞區段 | `x16/spike/game.cfg` |
| 建置腳本/旗標 | `x16/spike/build.ps1` |
| 塞不進去的單 byte 函式 | `x16/spike/gate_cx16.s` |
| 自動化、截圖、wav | `x16/tools/shot.ps1`、`playtest.ps1`、`x16/spike/wavstat.py` |
| 幾何模擬 | `x16/spike/fallswap_sim.py` |
| 瀏覽器播放器 | `web/x16/assemble.mjs`、`web/x16/app.js` |

---

## 附錄 A — 開工前檢查清單（複製到新移植的筆記裡）

```text
[ ] Apple II 版本還能建置，map 已記錄（CODE/BSS 範圍、零頁用法）
[ ] 所有 $C0xx / ProDOS / iobuf / 鍵盤 latch 的引用都列出來了
[ ] VERA 功能已列出（layer0 模式、精靈、PSG、調色盤、縮放）
[ ] main.c 用 -t cx16 -DVERA_BASE=0x9F20 編出零錯誤
[ ] ca65 原始碼用 --cpu 65C02 和新 base 組得過
[ ] game.cfg 的 RAM 區在 $9EFF 以下；map 檢查過；不會寫到 $9F00
[ ] $9A-$9F 的零頁（若有）已搬進 $22-$7F
[ ] 載入路徑的檔名已轉小寫；檢查 A=0 而不是 carry
[ ] 每次 load 後 CLRCHN；RAM_BANK 有還原
[ ] read() 會存回 VERA.address
[ ] loader PRG 能開機、音樂 overlay 到位、jmp 成功
[ ] 用鍵盤搖桿 device 0；START/SELECT 是上升緣
[ ] $C000/$C010 的讀取已移除（或用 #ifndef 包掉）
[ ] IRQ 已串接 KERNAL；VERA_IEN 從不清零；影格計數器正常
[ ] 1.5× 補償已在 VERA_X16 下移除
[ ] 走路速度與 NES 原版相符
[ ] Apple II 版本 byte 相同（listing 差異 = 0）
[ ] 標題、第 1 關、特殊鍵都有截圖；用 -Wav 檢查音訊
[ ] 幾何/行為模擬結果正確
[ ] 瀏覽器版已組好並做過煙霧測試（若要發佈）
```
