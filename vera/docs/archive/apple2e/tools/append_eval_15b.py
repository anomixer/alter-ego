import io

SEC = """
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
"""

with io.open('docs/PORT-APPLE2-EVAL.md', 'a', encoding='utf-8') as f:
    f.write(SEC)
print('appended')
