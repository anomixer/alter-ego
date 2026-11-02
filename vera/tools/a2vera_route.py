"""Find an enemy-free puzzle route from NES map data for input regression.

This plans tile choices, including mirrored item pickup and collapsed bridges.
It does not claim to validate enemy timing; the route is subsequently executed
in AppleWin to verify the real port's movement, pickup and completion states.
"""
from collections import deque
from pathlib import Path
import argparse
import json

ROOT=Path(__file__).resolve().parents[2]

def route(level,limit=500000):
    folder=ROOT/'vera/build/levels'/f'LV{level:02}'
    cells=(folder/'level_collision.bin').read_bytes()
    params=(folder/'level_params.bin').read_bytes()
    entities=(folder/'level_entities.bin').read_bytes()
    player=next((entities[i+1],entities[i+2]-6) for i in range(1,len(entities),3) if entities[i]==0x20)
    items=[(i,t&12) for i,t in enumerate(cells) if t&12]
    bridges={i:n for n,i in enumerate(i for i,t in enumerate(cells) if t&16)}
    def tile(x,y,dropped):
        if x<0 or x>31 or y<0 or y>=20: return 1
        i=y*32+x
        return 0 if i in bridges and dropped>>bridges[i]&1 else cells[i]
    def alter(x,y):
        return (max(2,min(30,31-x)),y) if not params[1] else (x,max(0,min(20,18-y)))
    def settle(state):
        x,y,left,remaining,dropped=state
        while True:
            ax,ay=alter(x,y)
            for n,(cell,kind) in enumerate(items):
                if (kind==4 and cell==y*32+x) or (kind==8 and cell==ay*32+ax): remaining&=~(1<<n)
            if not remaining: return x,y,left,remaining,dropped
            if y>=19 or tile(x,y,dropped)&32: return None
            if tile(x,y,dropped)&2 or tile(x,y+1,dropped)&19: return x,y,left,remaining,dropped
            y+=1
            if y>=19: return None
    initial=settle((*player,params[0],(1<<len(items))-1,0))
    queue=deque([initial]); previous={initial:None}
    while queue:
        state=queue.popleft()
        x,y,left,remaining,dropped=state
        if not remaining:
            keys=[];trace=[]
            while previous[state]:
                prev,key=previous[state]
                x0,y0=prev[:2]
                tx,ty=alter(x0,y0) if key=='J' else (x0+({'A':-1,'D':1}.get(key,0)),y0+({'W':-1,'S':1}.get(key,0)))
                frames=max(abs(tx-x0),abs(ty-y0))*2 if key=='J' else 8
                frames+=max(0,state[1]-ty)*8+5
                trace.append({'key':key,'x':state[0]*8,'y':(state[1]+6)*8,'frames':frames})
                state=prev;keys.append(key)
            return ''.join(reversed(keys)),len(previous),list(reversed(trace))
        here=tile(x,y,dropped); below=tile(x,y+1,dropped)
        moves=[]
        for dx,key in ((-1,'A'),(1,'D')):
            if not tile(x+dx,y,dropped)&1:
                bridge=bridges.get((y+1)*32+x)
                d=dropped if bridge is None else dropped|(1<<bridge)
                moves.append((key,(x+dx,y,left,remaining,d)))
        if here&2 and tile(x,y-1,dropped)&2: moves.append(('W',(x,y-1,left,remaining,dropped)))
        if (here|below)&2 and not below&17: moves.append(('S',(x,y+1,left,remaining,dropped)))
        ax,ay=alter(x,y)
        if left and not tile(ax,ay,dropped)&1: moves.append(('J',(ax,ay,left-1,remaining,dropped)))
        for key,next_state in moves:
            next_state=settle(next_state)
            if next_state is not None and next_state not in previous:
                previous[next_state]=(state,key);queue.append(next_state)
        if len(previous)>limit: raise RuntimeError('Route search limit exceeded')
    raise RuntimeError('No settled route; a mid-air exchange or enemy interaction may be required')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('level',type=int);p.add_argument('--json',action='store_true');args=p.parse_args()
    keys,states,trace=route(args.level)
    if args.json: print(json.dumps(trace))
    else: print(f'LV{args.level:02}: {len(keys)} actions, {states} states, route={keys}')
