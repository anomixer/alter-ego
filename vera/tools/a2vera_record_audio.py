"""Record the emulator's Windows output endpoint for playback verification.

Optional host dependency: soundcard (WASAPI loopback), installed locally under
vera/build/audio_deps for this diagnostic, never needed by the game build.
"""
import argparse
import sys
import wave
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'vera/build/audio_deps'))
import numpy as np
import soundcard as sc

p=argparse.ArgumentParser()
p.add_argument('output')
p.add_argument('--seconds',type=float,default=4)
args=p.parse_args()
rate=48000
speaker=sc.default_speaker()
loopback=sc.get_microphone(id=speaker.id,include_loopback=True)
with loopback.recorder(samplerate=rate,channels=[0,1]) as rec:
    data=rec.record(numframes=int(rate*args.seconds))
pcm=(np.clip(data,-1,1)*32767).astype('<i2')
with wave.open(args.output,'wb') as out:
    out.setnchannels(2)
    out.setsampwidth(2)
    out.setframerate(rate)
    out.writeframes(pcm.tobytes())
peak=float(np.max(np.abs(data)))
rms=float(np.sqrt(np.mean(data*data)))
print(f'{speaker.name}: {args.seconds:g}s, peak={peak:.5f}, RMS={rms:.5f}')
if rms<1e-5:
    raise SystemExit('FAIL: recorded output is silent')
