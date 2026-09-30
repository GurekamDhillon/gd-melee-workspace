"""Bounded semantic expression shared with the Lua lab; versioned saves contain traits."""
import math
TRAITS=('palette','energy','turbulence','cohesion','rhythm','persistence','structure')
def express(blend=0, traits=None, isolate=0):
    if not math.isfinite(blend) or not 0<=blend<=1:raise ValueError('blend outside [0,1]')
    traits=traits or {}
    values={k:float(traits.get(k,.5)) for k in TRAITS}
    if any(not math.isfinite(v) or not 0<=v<=1 for v in values.values()):raise ValueError('trait outside [0,1]')
    if not 0<=isolate<=7:raise ValueError('unknown layer')
    # Smoothstep balances opposing founder contributions with a constant rate sum.
    t=blend*blend*(3-2*blend)
    midpoint=1+.6*4*t*(1-t)
    out=[]
    for i in range(14):
        role=i%7+1;weight=(1-t) if i<7 else t
        if isolate and isolate!=role:weight=0
        structure=.35+1.3*values['structure'] if role in (2,4) else 1.65-1.3*values['structure'] if role in (3,5,6) else 1
        # Palette varies relative lightness across hot/cool layers; authored ramps retain their identity.
        light=.75+.5*(values['palette'] if i<7 else 1-values['palette'])
        out.append([weight,weight*structure*((.6+.4*values['rhythm']) if role in (1,3,5,6) else 1),.55+.9*values['energy'],
            .6+.8*values['persistence'],.75+.5*values['cohesion'],(.65+.7*values['energy'])*light*midpoint,.3+1.4*values['turbulence']])
    return out
