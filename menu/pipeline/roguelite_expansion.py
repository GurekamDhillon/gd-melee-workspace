#!/usr/bin/env python3
"""Astra's original, deterministic vector art pack and motion review.

Build with the art venv (Pillow) and rsvg-convert. No game/disc pixels are inputs.
Outputs remain separate from the installed v1 assets and gameplay scripts.
"""
from pathlib import Path
import hashlib
import importlib.util
import itertools
import json
import math
import shutil
import subprocess
from PIL import Image
from roguelite_art import ICONS

MENU = Path(__file__).resolve().parents[1]
ROOT = MENU.parent
OUT = MENU / 'out_roguelite_expansion'
ASSETS = {}


def add(name, group, body, *, size=128, anchor=(.5, .5), usage='', blend='alpha'):
    ASSETS[name] = dict(name=name, group=group, body=body, size=size,
                        anchor=list(anchor), usage=usage, blend=blend)


def line(d, width=5, opacity=1):
    return f'<path d="{d}" fill="none" stroke="white" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" opacity="{opacity}"/>'


def poly(points, opacity=1):
    return f'<polygon points="{points}" fill="white" opacity="{opacity}"/>'


def arc(a, b, r=24):
    x, y = 32 + r*math.cos(a), 32 + r*math.sin(a)
    xx, yy = 32 + r*math.cos(b), 32 + r*math.sin(b)
    return f'M{x:.3f} {y:.3f} A{r} {r} 0 {int(b-a>math.pi)} 1 {xx:.3f} {yy:.3f}'


def author():
    # Existing vocabulary is reused verbatim, under distinct pack ownership.
    for name in ('cinder','rime','magic','item','special','assault','traversal','guard','gene','fusion','route','elite','check','left','right','up','down'):
        add('icon_'+name, 'shared', ICONS[name], usage='Existing approved roguelite glyph; copied from source, not redrawn.')
    frame = line('M18 56H8V8H56V56H46', 3)
    add('door_upper','wayfinding',frame+line('M23 32L32 23L41 32 M32 24V47')+line('M22 16H42',3),usage='Mount above a real upper socket; raised lintel is the secondary cue.')
    add('door_lower','wayfinding',frame+line('M23 31L32 40L41 31 M32 17V39')+line('M22 48H42',3),usage='Mount at real drop entrance; low sill supplements down arrow.')
    add('door_return','wayfinding',frame+line('M22 23H38Q46 23 46 32T38 41H23 M28 15L20 23L28 31',4),usage='Previously visited destination; hook plus doorway, no color dependency.')
    add('door_unknown','wayfinding',frame+line('M24 26Q24 17 33 17T41 25Q41 30 33 34V39',4)+'<circle cx="33" cy="47" r="2.7" fill="white"/>',usage='Unexplored destination, not a guaranteed reward.')
    add('door_locked','wayfinding',frame+line('M24 29V23Q24 13 32 13T40 23V29',4)+poly('21,29 43,29 43,47 21,47')+line('M32 34V41',3).replace('stroke="white"','stroke="black"'),usage='Locked state; closed shackle is always visible.')
    add('door_open','wayfinding',frame+line('M25 29V23Q25 13 33 13T41 23',4)+poly('21,29 43,29 43,47 21,47')+line('M27 37L31 41L38 34',3).replace('stroke="white"','stroke="black"'),usage='Unlocked state; open shackle and check.')
    add('map_current','wayfinding',line('M32 5L59 32L32 59L5 32Z',3)+poly('32,19 44,42 32,36 20,42'),usage='Player map position; solid pointer inside diamond.')
    add('map_seen','wayfinding',line('M32 9L55 32L32 55L9 32Z',3)+'<circle cx="32" cy="32" r="6" fill="white"/>',usage='Visited room.')
    add('map_unseen','wayfinding',line('M25 16L32 9L39 16 M48 25L55 32L48 39 M39 48L32 55L25 48 M16 39L9 32L16 25',3),usage='Discovered but unvisited; four open corners.')
    add('map_boss','wayfinding',ICONS['elite']+line('M8 60H56',2),usage='Known champion room only; never reveal hidden content automatically.')
    add('map_rest','wayfinding',line('M13 48V28H51V48 M13 37H51 M22 26V17H35V26',5),usage='Safe/rest destination.')
    add('charge_segment','ui',poly('10,23 58,23 52,41 4,41'),usage='Repeat once per actual charge capacity; do not bake count.')
    add('cooldown_arc','ui',line(arc(-math.pi/2, math.pi),4)+poly('5,31 13,24 14,37'),usage='Mask/scissor by actual cooldown fraction.')
    add('refusal','ui',line('M18 18L46 46 M46 18L18 46',6)+line(arc(0,math.pi*1.99,27),2),usage='Brief local refusal; keep reason in runtime text.')
    add('ready_notch','ui',poly('8,33 24,49 58,15 51,8 24,35 15,26'),usage='Steady ready indicator after one short pulse.')
    add('breadcrumb','ui',line('M24 15L41 32L24 49',5),usage='D-pad ancestry separator.')
    add('family_kinetic','family',line('M7 19H42L53 27H22 M9 36H35L45 44H16 M22 53H38',5),usage='Gale: three forward-flowing rails.')
    add('family_aegis','family',line('M32 6L54 18V37L32 58L10 37V18Z',5)+line('M22 25H42 M32 15V45',4),usage='Aegis: braced, symmetric structure.')
    add('family_flux','family',line('M23 9C-1 24 22 41 40 34C61 26 60 55 39 56 M41 9C64 24 42 41 24 34C3 26 4 55 25 56',4),usage='Flux: two interlocking circuits.')
    add('family_sigil','family',line('M32 7L53 23L45 49H19L11 23Z M19 25H45L32 42Z',4)+'<circle cx="32" cy="7" r="4" fill="white"/>',usage='Sigil: enclosed triangular seal.')
    add('equip_blade','equipment',ICONS['assault'],usage='Reviewed held blade, not every Assault placement.')
    add('equip_boot','equipment',ICONS['traversal'],usage='Traversal equipment.')
    add('equip_charm','equipment',line('M20 8Q32 24 44 8 M32 20V27 M32 27L47 42L32 58L17 42Z',4),usage='Charm or focus equipment.')
    add('equip_mantle','equipment',poly('22,9 42,9 45,23 58,55 40,49 32,56 24,49 6,55 19,23')+line('M24 17L20 43 M40 17L44 43',3).replace('stroke="white"','stroke="black"'),usage='Mantle equipment silhouette.')
    add('reward_tradeoff','reward',line('M18 49V13 M8 23L18 13L28 23 M46 15V51 M36 41L46 51L56 41',5),usage='Benefit and cost; values are separate text.')
    add('reward_cache','reward',line('M9 23L32 11L55 23V49H9Z M9 29H55 M27 29V39H37V29',4),usage='Supply/reward container.')
    add('reward_extract','reward',line('M10 39V54H54V39 M32 43V8 M19 21L32 8L45 21',5),usage='Collection export after a committed successful save.')
    # Continuous masks have fully clear border pixels for clamp sampling.
    add('trail_cinder','continuous', '<path fill="url(#tail)" d="M3 39Q23 14 43 29Q51 39 61 23Q58 43 44 40Q27 29 3 39Z"/><path fill="white" opacity=".85" d="M24 34Q42 23 51 34L61 23Q55 39 43 35Z"/>',size=256,anchor=(.94,.5),blend='add',usage='Hooked ribbon texture, UV.x from oldest tail to newest sample; not a simulated trail by itself.')
    add('trail_rime','continuous',poly('3,36 21,29 31,33 45,19 61,28 43,29 32,41 20,35',.65)+poly('15,34 29,35 43,25 60,28 44,31 32,40',.9),size=256,anchor=(.94,.5),blend='add',usage='Faceted double rail; sample weapon tip/base history.')
    add('trail_gale','continuous',line('M4 26Q30 38 60 18 M11 39Q35 46 58 30',3)+line('M24 46Q44 48 61 41',1.5),size=256,anchor=(.94,.5),blend='add',usage='Three separated rails, strongest head at +X.')
    add('halo_cinder','continuous',''.join(line(arc(i*math.tau/6+.10,(i+1)*math.tau/6-.16),2.8) for i in range(6))+''.join(poly('29,4 35,4 32,12').replace('<polygon',f'<polygon transform="rotate({i*60} 32 32)"') for i in range(6)),size=256,blend='add',usage='Six-lobed art carrier; actual charge segments use halo_sector instances.')
    add('halo_rime','continuous',line('M32 4L56 18V46L32 60L8 46V18Z',2)+line('M32 11L50 21V43L32 53L14 43V21Z',1,.5),size=256,blend='add',usage='Static crystalline frame; avoid sustained broad rotation.')
    add('halo_sector','continuous',line(arc(-math.pi/2+.10,-math.pi/6-.10),3.5),size=128,blend='add',usage='One independent segment; renderer places N pieces for N capacity, never a baked false charge count.')
    add('orbit_cinder','continuous','<path fill="white" d="M8 46Q20 40 24 23Q32 6 50 11Q36 21 41 35Q42 50 28 54Q14 55 8 46Z"/><path fill="black" d="M19 44Q35 35 31 24Q44 37 31 46Z"/>',size=128,blend='add',usage='Curved ember seed; deterministic authored orbit, no force claim.')
    add('orbit_rime','continuous',poly('32,5 47,26 43,48 29,60 18,36 21,17',.5)+poly('32,5 30,33 29,60 18,36 21,17',1)+line('M30 33L47 26 M30 33L43 48',1),size=128,blend='add',usage='Faceted orbiting shard.')
    add('surface_cinder','surface',line('M10 61L19 39L14 24L30 3 M19 39L36 30L42 9 M36 30L52 41L60 22',2.3)+line('M25 52L37 39L49 48',1,.4),size=256,blend='add',usage='Vein mask in reviewed surface UVs; no arbitrary anatomical isolation.')
    add('surface_rime','surface',line('M7 58L25 39L38 24L56 5 M25 39L8 29 M25 39L29 57 M38 24L25 8 M38 24L57 30 M47 14L47 3',2)+line('M16 48L10 42 M32 32L46 40 M30 15L18 18',1,.7),size=256,blend='add',usage='Frost veins, slow reveal; preserve fighter base texture.')
    add('surface_aegis','surface',line('M8 4H28L38 14V32L28 42H8L0 32V14Z M38 32H58L64 42V60H38L28 50V42',2,.75),size=256,usage='Braced facets; local armor sheen.')
    add('surface_flux','surface',line('M4 17Q25 0 35 19T61 21 M3 47Q28 26 37 46T60 46',2)+line('M10 26Q28 11 40 29T58 29',1,.5),size=256,blend='add',usage='Flow lanes for UV-scroll material support.')
    add('surface_sigil','surface',line('M32 7L55 22L46 50H18L9 22Z M20 27H44L32 44Z M32 7V18',2),size=256,blend='add',usage='Local seal on an approved material or attached plane.')
    add('crown_prong','founder',poly('10,53 23,32 18,23 40,6 33,28 46,22 29,51')+line('M21 51L34 30',1,.6),size=256,anchor=(.42,.85),blend='add',usage='Thunder Crown: stepped bolt prong, individually timed.')
    add('arc_bridge','founder',line('M4 41L16 22L26 32L35 15L46 26L60 10',2)+line('M26 32L22 45L32 51 M46 26L54 39',1,.5),size=256,blend='add',usage='Authored bridge between crown nodes; dynamic branching needs renderer support.')
    add('vortex_band','founder','<path fill="white" d="M5 35C4 9 46 3 57 24C43 10 13 21 15 34C17 49 39 47 54 35C43 60 8 60 5 35Z"/>',size=256,blend='add',usage='Astral Vortex counter-rotating scythe bands; preserve central fighter visibility.')
    add('vortex_lens','founder',line(arc(0,math.pi*1.99,24),1.5)+line(arc(.4,2.7,18),3)+line(arc(3.5,5.8,18),3),size=256,blend='add',usage='Lens rim, not an opaque black disk over the fighter.')
    add('comet_crescent','founder','<path fill="url(#tail)" d="M3 47Q8 9 42 7Q60 9 61 29Q52 10 32 23Q16 32 3 47Z"/><path fill="white" d="M9 38Q20 11 44 13Q52 14 57 20Q38 9 9 38Z"/>',size=256,blend='add',usage='Comet Crescent sweep with wide negative space.')
    add('comet_star','founder',poly('32,5 37,26 59,32 37,38 32,59 27,38 5,32 27,26'),size=128,blend='add',usage='One leading star; echoes never replace attack contact evidence.')
    add('tell_dash','tell',line('M8 20L22 32L8 44 M27 20L41 32L27 44 M46 20L59 32L46 44',3),usage='Directional windup; orientation from actual attack intent.')
    add('tell_guard','tell',ICONS['guard']+line('M3 58H61',2),usage='Armored phase cue; only when armor is mechanically active.')
    add('tell_zone','tell',line('M10 10H24 M10 10V24 M54 10H40 M54 10V24 M10 54H24 M10 54V40 M54 54H40 M54 54V40',4)+'<circle cx="32" cy="32" r="4" fill="white"/>',usage='Scale to authoritative hazard extent; no fixed damage radius in asset.')
    add('tell_dive','tell',line('M20 7L32 25L44 7 M32 26V46 M20 37L32 49L44 37 M8 57H56',4),usage='Projected landing intent.')
    add('tell_phase','tell',line('M7 18L20 27L32 9L44 27L57 18L50 45H14Z M17 55H47',3),usage='Boss phase transition; protect the punish window from ornament.')
    add('contact_rime','contact',line('M5 47L24 36L32 15L40 36L59 47 M17 44L32 36L47 44 M32 36V55',2),size=128,anchor=(.5,.85),blend='add',usage='Short ground frost footprint, not a collision surface.')
    add('contact_cinder','contact',line('M7 48Q32 28 57 48 M18 53Q32 40 46 53',3)+poly('29,39 32,22 35,39'),size=128,anchor=(.5,.85),blend='add',usage='Hot landing accent anchored to actual contact.')
    add('wing_energy','attachment',poly('5,56 13,23 59,5 44,21 60,18 35,36 47,34 16,57',.65)+line('M9 53L17 29L51 12 M17 29L24 45',2),size=256,anchor=(.12,.86),blend='add',usage='Silhouette attachment concept plane; reviewed joint orientation required.')
    add('claw_energy','attachment',poly('10,59 18,25 21,7 28,34 25,60')+poly('29,59 36,17 40,4 44,34 42,60',.8)+poly('45,59 50,31 56,14 57,39 54,60',.6),size=256,anchor=(.5,.9),blend='add',usage='Three narrow energy claws; cosmetic extent must not imply hit range.')
    add('theme_ribs','world',line('M4 64V14L18 0 M18 64V22L39 0 M34 64V30L61 3 M50 64V38L64 24',1,.7),size=256,usage='Cobalt architectural backdrop; low contrast, no fake ledges.')
    add('theme_embers','world',line('M3 61L17 44L13 27L30 5 M27 64L43 48L39 28L59 4 M48 64L61 50',1.5,.6),size=256,usage='Fire depth accent behind collision layer.')
    add('theme_frost','world',line('M2 48L18 35L32 7L43 34L63 48 M18 35L14 58 M43 34L51 61 M24 23L8 14 M38 21L56 10',1,.7),size=256,usage='Frost backdrop facets; no implied platforms.')
    add('transition_slash','world',poly('28,0 64,0 36,64 0,64'),size=128,usage='Screen transition strip; animate coverage, reveal only on runtime ready.')


FAMILIES = {
 'fire': dict(name='Cinder', color='#ff985b', icon='icon_cinder', trail='trail_cinder', halo='halo_cinder', orbit='orbit_cinder', surface='surface_cinder', shape='hook / ember / rising flow'),
 'frost': dict(name='Rime', color='#91e5f4', icon='icon_rime', trail='trail_rime', halo='halo_rime', orbit='orbit_rime', surface='surface_rime', shape='facet / split rail / held symmetry'),
 'kinetic': dict(name='Gale', color='#abedaa', icon='family_kinetic', trail='trail_gale', halo='halo_sector', orbit='comet_star', surface=None, shape='forward rails / long spacing'),
 'aegis': dict(name='Aegis', color='#f3cf79', icon='family_aegis', trail=None, halo='halo_rime', orbit='orbit_rime', surface='surface_aegis', shape='braced facets / heavy steady rim'),
 'flux': dict(name='Flux', color='#d5a6ff', icon='family_flux', trail='trail_cinder', halo='vortex_lens', orbit='orbit_cinder', surface='surface_flux', shape='opposed circuits / inward exchange'),
 'sigil': dict(name='Sigil', color='#f2a3ce', icon='family_sigil', trail='arc_bridge', halo='surface_sigil', orbit='comet_star', surface='surface_sigil', shape='enclosed seal / linked nodes'),
}
FOUNDERS = {
 'SolarEruption': dict(title='Solar Eruption', color='#ff985b', core='orbit_cinder', ring='halo_cinder', detail='trail_cinder', motion='rising_hooks', family='fire'),
 'GlacialShatter': dict(title='Glacial Shatter', color='#91e5f4', core='orbit_rime', ring='halo_rime', detail='trail_rime', motion='facet_hold_then_split', family='frost'),
 'ThunderCrown': dict(title='Thunder Crown', color='#f5dd83', core='crown_prong', ring='halo_sector', detail='arc_bridge', motion='staggered_crown', family=None),
 'AstralVortex': dict(title='Astral Vortex', color='#c4a3ff', core='vortex_band', ring='vortex_lens', detail='orbit_rime', motion='counter_rotation', family=None),
 'CometCrescent': dict(title='Comet Crescent', color='#a8eedd', core='comet_crescent', ring='comet_star', detail='trail_gale', motion='directional_sweep', family=None),
}
REACTIONS = {
 'thermal_shock': ('Thermal Shock','SolarEruption','GlacialShatter','cold shell splits; hot hooks break through; steam decays', [0,90,160,540]),
 'plasma_surge': ('Plasma Surge','SolarEruption','ThunderCrown','crown gathers; narrow hot arc advances; residual ember rail', [0,120,190,600]),
 'charged_crystals': ('Charged Crystals','GlacialShatter','ThunderCrown','held facets carry staggered arcs; facets split after contact', [0,100,220,650]),
 'fire_cyclone': ('Fire Cyclone','SolarEruption','AstralVortex','hooks wind inward on two bands; open centre; unwind upward', [0,140,280,760]),
 'orbital_shard_storm': ('Orbital Shard Storm','GlacialShatter','AstralVortex','three faceted orbitals tighten; separate outward; rim fades', [0,150,300,800]),
 'infused_comet': ('Infused Comet','SolarEruption','CometCrescent','hot leading crescent; two trailing hooks; directional recovery', [0,70,160,500]),
}

# Each midpoint is deliberately composed; these are not arbitrary field lerps.
BLEND_DIRECTION = [
 ('hot core / cold shell',[-7,8,0,1],[9,-5,0,1.04]),
 ('fire beneath a staggered crown',[0,15,0,.9],[0,-18,0,1.04]),
 ('ember hooks threaded through counter-rotating bands',[-14,7,-.15,.85],[10,0,0,1.1]),
 ('hot leading crescent / ember wake',[-24,15,-.35,.75],[17,-2,-.12,1.06]),
 ('crystal frame / charged crown nodes',[0,12,0,1.02],[0,-20,0,.85]),
 ('faceted orbitals outside a clear-centred vortex',[0,0,0,1.13],[0,0,0,.86]),
 ('cold leading blade / split facet wake',[-20,14,.18,.77],[16,-7,-.08,1.08]),
 ('crown tips carried on opposed bands',[0,-21,0,.87],[0,11,0,1.07]),
 ('one directional sweep / staggered electrical echoes',[-23,-12,.32,.78],[19,7,-.16,1.06]),
 ('vortex uncoils into a leading crescent',[-16,7,0,.9],[19,-7,-.2,1.05]),
]


def contracts():
    states = {
      'dormant': dict(opacity=.20, trail_ms=0, orbit_count=0, pulse_hz=0),
      'charging': dict(opacity=.42, trail_ms=90, orbit_count=1, pulse_hz=.6),
      'ready': dict(opacity=.70, trail_ms=140, orbit_count=3, pulse_hz=0),
      'activation': dict(opacity=.90, trail_ms=190, orbit_count=3, pulse_hz=0, duration_ms=260),
      'recovery': dict(opacity=.25, trail_ms=60, orbit_count=0, pulse_hz=0, duration_ms=420),
    }
    pairs=[]
    for index,(a,b) in enumerate(itertools.combinations(FOUNDERS,2)):
        description,at,bt=BLEND_DIRECTION[index]
        pairs.append(dict(id=a+'__'+b, parents=[a,b], weights=[0,.25,.5,.75,1],
          composition={'core':a,'shell':b,'motion':description,'parent_a_transform':at,'parent_b_transform':bt},
          midpoint={'core_gain':.7,'shell_gain':.7,'detail_alternation':True,'opaque_overlap':'forbidden'},
          endpoint_rule='At 0 render only parent A; at 1 only parent B; no residual other-parent layers.',
          max_layers=12, max_detail_sprites=8, mechanical_reaction=False))
    return dict(schema=1, status='authored art and browser motion reference; native implementation pending',
      families=FAMILIES, states=states, founders=FOUNDERS, blends=pairs,
      reactions={k:dict(title=v[0],parents=list(v[1:3]),sequence=v[3],beats_ms=v[4],
                       status='visual choreography; gameplay mapping requires action-system review') for k,v in REACTIONS.items()},
      placement={'assault':'reviewed hands / held weapon endpoints','guard':'reviewed torso / shield, avoid face',
                 'traversal':'reviewed boots / feet; contact traces require ground contact'},
      afterimages=dict(status='native pose snapshot support required; browser mannequin is illustrative',
        interval_ms=40, lifetime_ms=160, opacity=[.24,.16,.09,.04], max_snapshots=4,
        tint='family accent with P1/P2 rim distinction', skinning='immutable historical pose including owned equipment',
        reset=['teleport','respawn','transform','equipment swap','scene exit','graphics reset','script error']),
      ribbons=dict(status='native history strip support required',max_samples=16,history_ms=190,
        sampling='post-animation base and tip, world-space history',uv='x: tail 0 to head 1; y: strip width',
        discontinuity='clear on teleport or owner/asset change; do not bridge discontinuities',alpha='straight',wrap='clamp'),
      halos=dict(segment_rule='N independent segments for actual capacity; fill only actual charges',
        max_capacity=12,empty_opacity=.16,orientation='attachment local; never camera-space unless specified'),
      quality={'low':dict(orbitals=0,trail_samples=6,afterimages=0,decorative_layers=3),
               'medium':dict(orbitals=2,trail_samples=10,afterimages=2,decorative_layers=7),
               'high':dict(orbitals=3,trail_samples=16,afterimages=4,decorative_layers=12)},
      accessibility=dict(reduced_motion='static halo; no afterimages/orbits, one short opacity transition',
        reduced_flashes='no full-screen flash; no rapid alternation; ready retains steady notch',
        opposing_builds='solid under-foot diamond P1; split-circle P2; shape remains under grayscale'),
      budget=dict(ui_resident_bytes_max=1048576,fx_resident_bytes_max=4194304,full_pack_bytes_max=8388608,
        loading='Full pack is an authoring library; load selected build/room sets, not every texture at once.',
        native_ms='must be measured during integration; no browser timing claim',
        projected_coverage='persistent decorative quads <= 2 body rectangles per actor; bursts <= 4 for <=260 ms',
        priority=['enemy attack tell','live fighter silhouette','readiness','gene ornament']),
      motion_events={'menu_enter':dict(duration_ms=120,translate_px=[6,0],opacity=[0,1]),
        'menu_back':dict(duration_ms=90,translate_px=[-4,0]),'ready':dict(duration_ms=220,scale=[1,1.08,1]),
        'refusal':dict(duration_ms=130,translate_px=[0,3,-2,0]),
        'toast':dict(enter_ms=150,hold_ms=1800,exit_ms=160,coalesce=True),
        'transition':dict(close_ms=180,hold='runtime ready',open_ms=240),
        'fusion':dict(approach_ms=300,interlace_ms=480,settle_ms=220,commit='runtime success event only')})


def layouts():
    return dict(schema=1,status='authored layout contract; installer must adapt to existing kit API',
      coordinates={'height':480,'widths':[640,854],'safe_inset':16,'text':'runtime strings, no baked words'},
      combat={'status':{'anchor':'bottom-left','rect':[17,-78,154,57],
                         'slots':['damage_percent','lives','assault_charge','traversal_charge','guard_charge','item_count']},
              'root_commands':{'anchor':'bottom-right','rect':[-249,-52,232,30],'directions':['left','right','down']},
              'open_commands':{'anchor':'bottom-right','rect':[-227,-98,210,76],
                               'slots':['parent_hint','breadcrumb','branch_1','branch_2','branch_3','availability']},
              'notification':{'anchor':'top-center','rect':[-110,22,220,28],'max_visible':1,'coalesce':True},
              'minimap':{'anchor':'top-left','rect':[19,34,80,17]},
              'coverage_4_3':{'closed_primary_panels':round((154*57+232*30)/(640*480),4),
                              'open_primary_panels':round((154*57+210*76)/(640*480),4)},
              'type_px':{'damage':27,'lives':12,'command':9,'breadcrumb':9,'secondary':9},
              'long_labels':'localize; measure font advances; abbreviate approved labels with full name in build view; never shrink below 9px'},
      doors={'units':'game units','opening':[10.4,16.9],'storey':26,
             'marker_size':[3.6,3.6],'marker_anchor_from_opening_base':[0,20.2],
             'reviewed_recipe_version':2,'upper_socket_origin':[39,26],
             'upper_marker_origin':[39,46.2],
             'render_depth':'front of lintel; resolve from actual kit mesh metadata, avoid z-fighting',
             'mapping':{'upper':'door_upper','lower':'door_lower','return':'door_return','locked':'door_locked','open':'door_open','unknown':'door_unknown'},
             'states':'gate state wins over destination marker; marker reveals only known information',
             'collision':'none; symbols cannot modify socket position or certify traversal'},
      screens={'reward':'three equal cards; direction choice; benefit and cost from real stat deltas',
               'fusion':'two parent seals approach, interlace, settle after commit; cost stays visible',
               'victory':'export preview; confirm only after successful save',
               'failure':'retained collection vs expired run changes, then review/return choices',
               'transition':'close, hold until runtime ready, open; no host-stage flash'},
      gene_art={'cinder':'fire','emberline':'fire','rime':'frost','glacier':'frost','gale':'kinetic','dashstep':'kinetic',
                'bulwark':'aegis','retaliate':'aegis','siphon':'flux','convert':'flux','brand':'sigil','chain':'sigil'},
      founder_mapping='Founders are visual recipes, not additional mechanical gene families. Thunder/Astral/Comet mappings require gameplay review.',
      tell_map={'dash_windup':'tell_dash','guard_flare':'tell_guard','zone_marker':'tell_zone','dive_marker':'tell_dive','phase_roar':'tell_phase','aura':'icon_elite'},
      evidence={'native_branch_capture':'not available at art authoring; all recipes still uncertified in handoff',
                'reviewed_native_baseline':'/tmp/roguelite-door-grid-v10.png; fixed-route doorway/HUD only',
                'required_next':'native integrated branch-room capture, actual controller readability and attachment review'})


DEFS = '<linearGradient id="tail"><stop stop-color="white" stop-opacity="0"/><stop offset=".5" stop-color="white" stop-opacity=".65"/><stop offset="1" stop-color="white"/></linearGradient>'


def build():
    author()
    for folder in ('svg','rgba','gx','preview'): (OUT/folder).mkdir(parents=True,exist_ok=True)
    spec=importlib.util.spec_from_file_location('gx',ROOT/'melee/worktrees/linux/pc/tools/png2gx.py')
    gx=importlib.util.module_from_spec(spec);spec.loader.exec_module(gx)
    records=[]
    for name,a in ASSETS.items():
        size=a['size']
        # Black shapes cut out the white mask; output always white RGB / straight alpha.
        src=f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 64 64"><defs>{DEFS}<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64"><g fill="white">{a["body"]}</g></mask></defs><path d="M0 0H64V64H0Z" fill="white" mask="url(#m)"/></svg>'
        (OUT/'svg'/f'{name}.svg').write_text(src)
        png=OUT/'rgba'/f'{name}.png'
        subprocess.run(['rsvg-convert','-o',str(png),str(OUT/'svg'/f'{name}.svg')],check=True)
        im=Image.open(png).convert('RGBA');alpha=im.getchannel('A');im=Image.new('RGBA',im.size,(255,255,255,0));im.putalpha(alpha);im.save(png)
        # IA4 follows the existing menu kit; larger FX masks retain RGBA8 gradients.
        fmt='ia4' if size==128 else 'rgba8'
        gx.main([str(png),str(OUT/'gx'/f'{name}.gxtex'),'--format',fmt])
        rec={k:v for k,v in a.items() if k!='body'}
        rec.update(file=f'rgba/{name}.png',source=f'svg/{name}.svg',gx=f'gx/{name}.gxtex',
            size=[size,size],alpha='straight',wrap='clamp',format=fmt.upper(),
            sha256=hashlib.sha256(png.read_bytes()).hexdigest(),gx_bytes=(OUT/'gx'/f'{name}.gxtex').stat().st_size,
            reuse=name.startswith('icon_'))
        records.append(rec)
    data=contracts()
    (OUT/'direction.json').write_text(json.dumps(data,indent=2)+'\n')
    (OUT/'layout.json').write_text(json.dumps(layouts(),indent=2)+'\n')
    kit=json.loads((MENU/'out_kit/kit.json').read_text())
    manifest=dict(schema=1,version=1,provenance='Original Astra vector source in menu/pipeline/roguelite_expansion.py; shared icon paths reused from roguelite_art.py',
                  native_installed=False,palette=kit['palette'],textures=records,
                  gx_total_bytes=sum(a['gx_bytes'] for a in records))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Browser embeds data to support a local-file review without fetch/CORS.
    payload=dict(assets=records,**data)
    html=(MENU/'pipeline/roguelite_expansion_review.html').read_text().replace('__DATA__',json.dumps(payload).replace('</','<\\/'))
    (OUT/'index.html').write_text(html)
    for name in ('roguelite_expansion_review.js','roguelite_expansion_review.css'):
        shutil.copyfile(MENU/'pipeline'/name,OUT/name)
    shutil.copyfile(MENU/'SourceSans3/SourceSans3-Black.otf',OUT/'font.otf')
    shutil.copyfile(MENU/'SourceSans3/LICENSE.md',OUT/'font-LICENSE.md')
    (OUT/'README.md').write_text('''# TBD — continuous identity art pack

Open `index.html`: compact combat UI, interactive D-pad tree, family states,
five founder motion references, ten pair blends, six reaction choreographies,
world themes and reward/fusion/results presentation. These are original art
previews on an abstract mannequin, not native gameplay or finished mechanics.

Build: `_build/roguelite-art-venv/bin/python menu/pipeline/roguelite_expansion.py`.
Requires Pillow and rsvg-convert. Native GX conversion uses existing png2gx.py.
Source SVG, straight-alpha PNG, GX textures and hashes are in manifest.json.
Motion/state/attachment/support/budget contracts are in direction.json.
No game/disc imagery is included. Source Sans 3 retains its OFL license.

Integration must validate masks, depth/alpha, actual attachment selectors,
memory/overdraw, semantics and normal-speed motion in the native engine.
Afterimages, ribbons and animated surfaces require native support; the
mannequin review demonstrates art intent only. Do not set gameplay feature or
room certification flags based on this preview. Existing art is not overwritten.
''')
    print(f'ART PACK: {len(records)} textures, {manifest["gx_total_bytes"]} GX bytes; {OUT}/index.html')


if __name__=='__main__': build()
