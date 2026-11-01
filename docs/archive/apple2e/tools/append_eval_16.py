import io

SEC = """
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
"""

with io.open('docs/PORT-APPLE2-EVAL.md', 'a', encoding='utf-8') as f:
    f.write(SEC)
print('appended')
