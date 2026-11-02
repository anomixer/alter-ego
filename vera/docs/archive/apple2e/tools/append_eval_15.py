import io

SEC = """
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
"""

with io.open('docs/PORT-APPLE2-EVAL.md', 'a', encoding='utf-8') as f:
    f.write(SEC)
print('appended')
