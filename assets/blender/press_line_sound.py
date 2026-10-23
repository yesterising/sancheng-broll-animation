"""Original stereo mechanical sound design, driven by the scene's event plan."""
import array
import argparse
import json
import math
import random
import wave
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--events',type=Path,default=Path(__file__).with_name('press_line_events.json'))
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args()
target=args.output.expanduser().resolve()
report_path=target.with_suffix('.events.json')
if target.exists() or report_path.exists(): parser.error('Output or report already exists; choose a new filename')
if target.suffix.lower()!='.wav': parser.error('output must be a WAV file')
E=json.loads(args.events.read_text())
if (E['duration'],E['fps'])!=(14,24): parser.error('Reference sound follows the fixed 14-second, 24fps example')
target.parent.mkdir(parents=True,exist_ok=True)
RATE=48000
DURATION=float(E['duration'])
N=round(RATE*DURATION)
left=[0.0]*N
right=[0.0]*N
rng=random.Random(20261023)
events=[]

def put(index,value,pan=0):
    if 0<=index<N:
        angle=(pan+1)*math.pi/4
        left[index]+=value*math.cos(angle)
        right[index]+=value*math.sin(angle)

def impact(at,gain=.3,body=370,decay=35,pan=0):
    events.append({'type':'plastic_or_mechanism_contact','at':at,'pan':pan})
    start=round(at*RATE)
    noise=0
    for n in range(round(.24*RATE)):
        t=n/RATE
        noise=.65*noise+.35*rng.uniform(-1,1)
        click=(rng.uniform(-1,1)-noise)*math.exp(-t*220)*.6
        tone=(math.sin(math.tau*body*t)*.50+math.sin(math.tau*body*2.71*t)*.25)*math.exp(-t*decay)
        put(start+n,gain*(click+tone),pan)

def air(at,length,gain=.1,pan=.2):
    events.append({'type':'air_or_vacuum','at':at,'duration':length})
    low=0
    start=round(at*RATE)
    for n in range(round(length*RATE)):
        t=n/RATE
        low=.91*low+.09*rng.uniform(-1,1)
        edge=min(1,t/.018)*min(1,(length-t)/.04)
        put(start+n,gain*(rng.uniform(-1,1)-low)*edge,pan)

def servo(name,gain=.04,pan=.2):
    a,b=E[name]
    events.append({'type':name,'at':a,'duration':b-a})
    phase=0
    low=0
    for i in range(round(a*RATE),round(b*RATE)):
        p=(i/RATE-a)/(b-a)
        speed=math.sin(math.pi*p)
        phase+=math.tau*(165+110*speed)/RATE
        low=.8*low+.2*rng.uniform(-1,1)
        tone=.65*math.sin(phase)+.20*math.sin(phase*2.001)+.3*low
        put(i,gain*tone*speed,pan)

def dsmooth(a,b,t):
    p=(t-a)/(b-a)
    return 6*p*(1-p)/(b-a) if 0<p<1 else 0

# Small room tone and drive-belt texture. Velocity is the derivative of the
# same position function used by the workpiece, rollers and conveyor ribs.
phase=0
noise=0
for i in range(N):
    t=i/RATE
    velocity=2.85*dsmooth(*E['belt_in'],t)+3.4*dsmooth(*E['belt_out'],t)
    speed=min(1,velocity/2)
    phase+=math.tau*(63+55*speed)/RATE
    noise=.94*noise+.06*rng.uniform(-1,1)
    running=1 if 2.25<t<13.2 else 0
    hum=(.022+.053*speed)*math.sin(phase)+.009*speed*math.sin(2.02*phase)
    friction=(.019+.095*speed)*noise
    put(i,running*(hum+friction)+.002*noise,0)

impact(E['button_down'][1],.47,680,85,-.12)
impact(E['button_up'][0],.18,920,100,-.12)
impact(2.28,.13,190,25,0)
for name in ['grip_down','grip_lift','grip_transfer','grip_place','grip_clear','grip_return']:
    servo(name,.073 if name=='grip_transfer' else .051)
air(E['grip_down'][1],.19,.10)
impact(E['grip_down'][1],.12,540,70,.2)
impact(E['belt_in'][1],.19,260,45,0)
impact(E['grip_place'][1],.24,490,65,.12)
air(E['grip_release'],.09,.09)
servo('press_approach',.037,0)
air(E['press_approach'][0],.60,.055,0)
impact(E['press_approach'][1],.24,340,45,0)
impact(E['press_fit'][1],.54,420,48,0)
air(E['press_retract'][0],.22,.075,0)
servo('press_retract',.031,0)
impact(E['press_retract'][1],.11,240,40,0)
impact(E['belt_out'][1],.18,310,55,.4)
for at in [E['scan'],E['scan']+.10]:
    for n in range(round(.045*RATE)):
        t=n/RATE
        put(round(at*RATE)+n,.045*math.sin(math.tau*1800*t)*math.sin(math.pi*t/.045)**2,.4)

# Smooth final release and keep comfortable headroom, with no borrowed samples.
peak=max(max(abs(v) for v in left),max(abs(v) for v in right))
gain=3.2
pcm=array.array('h')
energy=0
for i,(l,r) in enumerate(zip(left,right)):
    edge=min(1,i/(RATE*.02))*min(1,(N-i)/(RATE*.25))
    for v in [l,r]:
        value=.85*math.tanh(v*gain/.85)*edge
        energy+=value*value
        pcm.append(round(max(-.95,min(.95,value))*32767))
with target.open('xb') as stream, wave.open(stream,'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(pcm.tobytes())
report={'duration':DURATION,'rate':RATE,'channels':2,'source':'original procedural synthesis',
        'peak_before_gain':peak,'gain':gain,'rms_dbfs':20*math.log10(math.sqrt(energy/(2*N))), 'events':events}
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='events'}))
