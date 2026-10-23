"""Original, subtle synthetic mechanical Foley for this standalone animation."""
import argparse
import array
import math
import random
import wave
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
target = args.output.expanduser().resolve()
if target.exists():
    parser.error('output already exists; choose a new filename')
target.parent.mkdir(parents=True, exist_ok=True)

RATE=44100
DURATION=9
rng=random.Random(42)
samples=[0.0]*(RATE*DURATION)

def impact(at,weight=.2,length=.14):
    start=int(at*RATE)
    low=0
    for n in range(int(length*RATE)):
        t=n/RATE
        low=.7*low+.3*rng.uniform(-1,1)
        transient=(rng.uniform(-1,1)-low)*math.exp(-t*125)*.5
        resonance=(math.sin(2*math.pi*370*t)*.35+math.sin(2*math.pi*1190*t)*.18)*math.exp(-t*52)
        if start+n<len(samples):samples[start+n]+=weight*(transient+resonance)

for t in [.18,.52,.86,1.2]:impact(t,.11,.10)
impact(2.70,.42,.10)
impact(3.03,.16,.08)
for t in [5.26,6.82,8.38]:impact(t,.27,.2)

# An accelerating motor, soft drive-belt friction, and spaced roller contacts.
phase=0
smooth_noise=0
for n in range(int(2.9*RATE),len(samples)):
    t=n/RATE-2.9
    onset=min(1,t/.55)
    fade=min(1,(DURATION-n/RATE)/.3)
    frequency=65+45*onset
    phase+=2*math.pi*frequency/RATE
    smooth_noise=.91*smooth_noise+.09*rng.uniform(-1,1)
    whirr=.032*math.sin(phase)+.013*math.sin(2.03*phase)+.006*math.sin(4.01*phase)
    friction=.07*smooth_noise*(.7+.3*math.sin(t*2*math.pi*8))
    samples[n]+=(whirr+friction)*onset*fade

pcm=array.array('h',(int(max(-.95,min(.95,v))*32767) for v in samples))
with target.open('xb') as stream, wave.open(stream,'wb') as out:
    out.setnchannels(1);out.setsampwidth(2);out.setframerate(RATE);out.writeframes(pcm.tobytes())
print(target)
