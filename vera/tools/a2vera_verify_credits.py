"""Check the Credits actually displayed by AppleWin, including glyph pixels."""
from pathlib import Path
from PIL import Image
from a2vera_snapshot import read_snapshot

BUILD = Path(__file__).resolve().parents[2] / 'vera/build'


def glyph_mask(image):
    pixels = image.convert('RGB').tobytes()
    return bytes(max(pixels[i:i+3]) > 8 for i in range(0, len(pixels), 3))


if __name__ == '__main__':
    _, _, vram, _ = read_snapshot(BUILD/'shots/credits_verified.aws.yaml')
    assert vram[0x2000:0x3000] == (BUILD/'credits_map.bin').read_bytes()
    assert vram[0x1FA00:0x1FC00] == (BUILD/'credits_palette.bin').read_bytes()
    actual = Image.open(BUILD/'shots/credits_verified.bmp')
    expected = Image.open(BUILD/'credits_preview.png')
    assert actual.size == (640, 480)
    actual = actual.resize((320, 240), Image.Resampling.NEAREST)
    assert glyph_mask(actual) == glyph_mask(expected), 'Credits scanout is incomplete or garbled'
    print('PASS: actual Credits map, palette and glyph pixels match the artwork')
