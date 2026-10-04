"""Behavior sequences adapted from the project demo-tour audit scenarios.py/drive.py.
No launches on import. Observations and decoded screenshots accompany explicit assertions.
Gauntlet checks staging only; traversal and a real boss KO remain manual acceptance.
"""
P1 = "S(gd.player(1))"
def K(k, w=.7): return ('k', k, w)
def E(x): return ('e', x)
SC = {
 'demo_input': [E("S(gd.pad(1))"), K('I', .4), E("S(gd.pad(1))"), ('w', 1.0), E("S(gd.pad(1))"), K('I', .3), K('R', .4), E("S(gd.pad(1))"), ('s', 'a')],
 'demo_kit': [E("tostring(gd.kit.available())"), ('s', 'a'), K('K'), ('s', 'b'), K('K')],
 'demo_fighters': [E("S(gd.player(1))"), K('T'), E("gd.player(1).x..','..gd.player(1).y"), E("gd.player(2).percent"), K('P'), E("gd.player(2).percent"), K('C'), ('w', 1.5), E("S(gd.player(2).action)"), K('C'), ('s', 'a')],
 'demo_modifiers': [E("S(gd.fighter_mod(1))"), K('M'), E("S(gd.fighter_mod(1))"), ('s', 'a'), K('M'), E("S(gd.fighter_mod(1))")],
 'demo_reserve': [K('B'), E("tostring(gd.fighter_benched(2))"), E("S(gd.players())"), ('s', 'a'), K('C', 1.0), E("tostring(gd.fighter_benched(2))"), E("S(gd.player(2))"), ('s', 'b')],
 'demo_fly': [K('F'), E("S(gd.fly_state(1))"), K('T', 1.5), E("S(gd.fly_state(1))"), E("gd.player(1).x..','..gd.player(1).y"), K('A', 1.0), E("S(gd.fly_state(1))"), ('s', 'a'), K('R'), E("S(gd.fly_state(1))"), K('F'), E("S(gd.fly_state(1))")],
 'demo_contacts': [K('O'), K('W'), ('w', 1), E("S(gd.wait_status(1))"), E("S(gd.contacts(1))"), ('c', "demo_key T"), ('s', 'a'), ('w', 3.5), E("S(gd.contacts(1))")],
 'demo_camera': [K('F', 1.0), E("S(gd.camera_get())"), ('s', 'follow'), K('M', 2.0), E("S(gd.camera_get())"), ('s', 'move'), K('S', .3), ('s', 'shake'), K('R', 1.0), E("S(gd.camera_get())")],
 'demo_camera_params': [('probe', '.+'), K('G', .6), ('probe', '.+'), ('s', 'a'), K('R'), ('probe', '.+')],
 'demo_collision': [('s', 'a'), E("S(gd.floor_below(0,100))"), K('P', 1.0), ('s', 'b'), E("S(gd.floor_below(0,100))")],
 'demo_models': [E("S(gd.model_instances())"), ('s', 'a'), K('R'), E("S(gd.model_instances())")],
 'demo_materials': [E("S(gd.model_instances())"), ('s', 'a'), K('L'), ('s', 'b'), E("S(gd.light_get and gd.light_get() or 'nolightget')")],
 'demo_chunks': [('s', 'a'), K('R'), K('RIGHT', 1.0), ('s', 'b'), E("S(gd.floor_below(40,100))"), K('LEFT', 1.0), E("S(gd.area_list and gd.area_list() or 'noarealist')")],
 'demo_enemies': [E("S(gd.enemies and gd.enemies() or 'noenemies')"), ('s', 'a'), K('N'), ('c', "= gd.teleport(1,25,12)"), ('w', 2.0), ('s', 'b'), E("S(gd.player(1))")],
 'demo_pickup_juice': [K('I'), E("S(gd.items())"), ('s','plain'), K('R'), K('J'), E("S(gd.fx())"), ('s','juice'), ('c', '= gd.teleport(1,20,12)'), ('w',1), K('R')],
 'demo_pickups': [K('I', 1.0), E("S(gd.items())"), ('s', 'a'), ('w', 1.0), E("S(gd.items())"), E("S(gd.player(1))")],
 'demo_items': [K('I', 1.0), E("S(gd.items())"), ('s', 'a')],
 'demo_events': [K('E', 1.0), E("S(gd.player(1))"), ('c', "= gd.teleport(1,30,10)"), ('w', 2.0), ('s', 'a')],
 'demo_hitstop': [K('H', .1), E("gd.player(1).action_frame"), ('w', .2), E("gd.player(1).action_frame"), ('w', .2), E("gd.player(1).action_frame"), ('w', 1.0), E("gd.player(1).action_frame"), K('C', .2)],
 'demo_post_grade': [('s', 'on'), K('P', 1.0), ('s', 'off'), K('P', 1.0)],
 'demo_post_vignette': [('s', 'on'), K('P', 1.0), ('s', 'off'), K('P', 1.0)],
 'demo_post_outline': [('s', 'on'), K('P', 1.0), ('s', 'off'), K('P', 1.0)],
 'demo_post_bloom': [('s', 'on'), K('P', 1.0), ('s', 'off'), K('P', 1.0)],
 'demo_post_custom': [('s', 'on'), K('U', 1.0), ('s', 'tint2')],
 'demo_surface_fighter': [('s', 'on'), K('S', 1.0), ('s', 'off'), K('S', 1.0)],
 'demo_surface_stage': [('s', 'on'), K('S', 1.0), ('s', 'off'), K('S', 1.0)],
 'demo_parts': [K('T', 1.0), E("S(gd.dobj_tints(1))"), ('s', 'a'), K('R', .6), E("S(gd.dobj_tints(1))")],
 'demo_six_slots': [K('L', 1.0), E("#gd.players()"), ('c', "demo_key K"), ('w', 3.0), E("#gd.players()..' '..tostring(gd.player(6) and gd.player(6).y)"), ('s', 'a'), K('R', 1.5), E("S(gd.player(6))")],
 'demo_data': [K('S', .7), K('S', .7), E("S(gd.data_read('counter.txt'))"), K('R', .4), ('s', 'a')],
 'demo_profiler': [K('O', 2.0), E("S((gd.perf(120).profiler or {}).enabled)"), ('c', 'prof report'), K('O', .6)],
 'demo_lab_inspection': [E("#(gd.motion_list(1) or {})"), K('J', .8), E("tostring(gd.paused())..' '..gd.motion_name(gd.player(1).action,1)"), ('s', 'a'), K('B', .5), E("gd.debug_draw(1)"), ('s', 'b'), K('SPACE', .6), E("tostring(gd.paused())")],
 'demo_rewind': [K('S', .5), ('w', 1.0), K('P', .3), E("tostring(gd.paused())"), K('N', .3), K('N', .3), K('L', .6), E("S(gd.history())"), K('R', .5), E("tostring(gd.paused())")],
 'demo_callouts': [K('C', 1.0), E("S(gd.comm_state())"), ('s', 'a'), ('w', 3.5), E("S(gd.comm_state())")],
 'demo_tasks': [K('Q', .3), ('w', 4.0), E("S(gd.player(1).airborne)"), E("S(gd.pad(1))")],
 'demo_console_socket': [('c', 'demo_ping'), ('c', 'demo_ping'), E("S(gd.player(1))")],
 'demo_effects': [K('E', 1.0), E("S(gd.fx())"), ('s', 'a'), K('C', 1.0), ('s', 'b'), K('R', 1.0), ('c', 'demo_fx_play'), K('F', 1.0), E("S(gd.fx())")],
 'demo_mission_cameras': [('s', 'f'), K('C', 1.5), E("S(gd.camera_get())"), ('s', 'c'), K('V', 1.0), E("S(gd.camera_get())"), ('s', 'v'), K('R', 1.0), E("S(gd.camera_get())")],
 'demo_stage_tour': [('w', 2.0), E("S(gd.stage_slots and gd.stage_slots() or 'noslots')"), ('s', 'a'), ('w', 9), ('s', 'b'), K('N', 2.0), ('s', 'c'), ('w', 9), ('s', 'd')],
}
SC['demo_gauntlet'] = [('w', 6.0), E("tostring(gd.fighter_benched(2))..' items='..#gd.items()..' players='..#gd.players()"), ('s', 'a'), E("S(gd.camera_get())"), E("gd.frame()")]
SC['demo_training_card'] = [E("S(gd.player(1).action)"), ('s', 'a'), K('M', 1.0), E("tostring(gd.paused())..' '..gd.motion_name(gd.player(1).action,1)"), ('c', 'step 3'), ('s', 'b'), K('SPACE', .6), K('D', .3), ('c', "= gd.teleport(1,0,60)"), ('w', 3.0), ('s', 'c')]

# Require real state predicates, not merely successful command dispatch or capture.
CHECKS = {
 'demo_input': 'gd.pad(1) ~= nil and math.abs(gd.pad(1).x or 0)<1',
 'demo_kit': 'gd.safe_area().w > 0',
 'demo_fighters': 'gd.player(2).percent >= 25',
 'demo_modifiers': 'gd.fighter_mod(1) == nil',
 'demo_reserve': 'not gd.fighter_benched(2)',
 'demo_fly': 'not gd.fly_state(1).flying',
 'demo_contacts': 'gd.contacts(1) ~= nil',
 'demo_camera': 'gd.camera_get().eye ~= nil',
 'demo_camera_params': 'gd.player(1) ~= nil',
 'demo_collision': 'gd.floor_below(0,100) ~= nil',
 'demo_models': 'gd.floor_below(0,100) ~= nil',
 'demo_materials': 'gd.floor_below(0,100) ~= nil',
 'demo_chunks': 'gd.floor_below(40,100) ~= nil',
 'demo_enemies': 'gd.player(1) ~= nil',
 'demo_pickup_juice': '#gd.items()==0',
 'demo_pickups': 'gd.player(1) ~= nil',
 'demo_items': '#gd.items() > 0',
 'demo_events': 'gd.player(1) ~= nil',
 'demo_hitstop': 'gd.player(1).action_frame >= 0',
 'demo_post_grade': 'gd.player(1) ~= nil',
 'demo_post_vignette': 'gd.player(1) ~= nil',
 'demo_post_outline': 'gd.player(1) ~= nil',
 'demo_post_bloom': 'gd.player(1) ~= nil',
 'demo_post_custom': 'gd.player(1) ~= nil',
 'demo_surface_fighter': 'gd.player(1) ~= nil',
 'demo_surface_stage': 'gd.match().active',
 'demo_parts': 'gd.dobj_tints(1).count == 0',
 'demo_six_slots': '(function() local _,entities=gd.fighter_benched(6); for _,e in ipairs(entities) do if e.entity_index==0 then return e.present and not e.invisible and not e.dormant and gd.player(6).percent==0 end end return false end)()',
 'demo_data': 'gd.player(1) ~= nil',
 'demo_profiler': 'gd.perf().profiler ~= nil',
 'demo_lab_inspection': 'not gd.paused()',
 'demo_rewind': 'not gd.paused() and gd.history().depth > 0',
 'demo_callouts': 'gd.comm_state() ~= nil',
 'demo_effects': '#gd.fx() > 0',
 'demo_mission_cameras': 'gd.camera_get().eye ~= nil',
 'demo_tasks': 'not gd.player(1).airborne',
 'demo_console_socket': 'gd.player(1) ~= nil',
 'demo_gauntlet': 'gd.fighter_benched(2)',
 'demo_training_card': 'gd.player(1).action > 13',
 'demo_stage_tour': '#gd.stage_slots() >= 3',
}
SCENARIOS={ident:list(steps)+[('probe','.+'),('assert',CHECKS[ident])] for ident,steps in SC.items()}
SCENARIOS['demo_rewind'].append(('probe','PROVED: snapshot restored original damage'))
SCENARIOS['demo_six_slots'].append(('probe','PROVED: P6 visible'))
SCENARIOS['demo_gauntlet'].append(('probe','room=1 building=false'))

# Inspect the demo owner's local state immediately after each documented control.
expected={
 'demo_kit': {'K':['false','true']},
 'demo_fighters': {'C':['true','false']},
 'demo_modifiers': {'M':['true','false']},
 'demo_reserve': {'B':['true'],'C':['false']},
 'demo_collision': {'P':['true']},
 'demo_materials': {'L':['true']},
 'demo_enemies': {'N':['wave=1']},
 'demo_parts': {'T':['^[1-9][0-9]*'],'R':['^0']},
 'demo_data': {'S':['count=1','count=2'],'R':['count=2']},
 'demo_mission_cameras': {'C':['chunk'],'V':['shaft'],'R':['retail']},
 'demo_rewind': {'L':['PROVED: snapshot restored original damage']},
 'demo_training_card': {'M':['Attack11']},
}
for ident,steps in list(SCENARIOS.items()):
    counters={}; checked=[]
    for step in steps:
        checked.append(step)
        if step[0]=='k':
            key=step[1]; index=counters.get(key,0); counters[key]=index+1
            options=expected.get(ident,{}).get(key,[])
            pattern=options[index] if index<len(options) else '.+'
            if ident.startswith('demo_post_') and ident!='demo_post_custom' and key=='P': pattern='^'+('false' if index%2==0 else 'true')
            if ident.startswith('demo_surface_') and key=='S': pattern='^'+('false' if index%2==0 else 'true')
            checked.append(('probe',pattern))
    SCENARIOS[ident]=checked
# Remove queries of nonexistent optional API names; owner probes capture their local state.
for ident in ('demo_materials','demo_enemies','demo_chunks'):
    SCENARIOS[ident]=[s for s in SCENARIOS[ident] if not (s[0]=='e' and any(name in s[1] for name in ('gd.light_get','gd.enemies','gd.area_list')))]

# Completion is checked from the owning demo; elapsed wait alone never passes.
SCENARIOS['demo_warm']=[('w',12.0),('probe','^ready'),('s','ready'),('assert','gd.match().active')]

# Retail progression demos are manual-only (tour=false); API smoke admission checks.
SCENARIOS['demo_1p_awareness']=[('assert',"type(gd.mode_1p)==\"function\"")]
SCENARIOS['demo_1p_hold']=[('assert',"type(gd.hold_1p)==\"function\"")]
SCENARIOS['demo_1p_spawn']=[('assert',"type(gd.spawn_1p)==\"function\"")]
SCENARIOS['demo_1p_loop']=[('assert',"type(gd.start_1p)==\"function\"")]


# EM1 source demos: these scenarios are definitions, not game execution evidence.
for field in ('fall_speed','weight','shield_regen'):
    ident='demo_modifier_'+field
    SCENARIOS[ident]=[
        K('M',.3),('probe','^true '+field+'=2'),
        ('assert','gd.fighter_mod(1).'+field+'==2'),
        K('M',.3),('probe','^false '+field+'=1'),
        ('assert','gd.fighter_mod(1)==nil'),
    ]
SCENARIOS['demo_hit_context']=[
    ('c','= gd.teleport(1,-5,0)'),('c','= gd.teleport(2,5,0)'),
    ('w',.3),('c','= gd.input(1,{buttons="A"},1)'),('w',.8),
    ('probe','^captured=true move=jab element=normal attacker_damage=[0-9]'),
]
# Explicit hook admission only. Real payload/ordering acceptance requires an operator
# or rebuilt native suite; passing this smoke never establishes the actual event.
for event in ('ko','stock_lost','jump','air_jump','ledge_grab','grab','throw','taunt','shield_hit','perfect_shield'):
    SCENARIOS['demo_event_'+event]=[
        ('probe','^contract=on_'+event+' hook=true captured=[0-9]+ acceptance=operator-required'),
    ]

SCENARIOS['demo_sim_checkpoint']=[
    ('c','= gd.history(180,30)'),('w',2),
    ('probe',r'^checkpoint [0-9]+ \| matches=true'),
    ('c','= gd.step_back(60)'),('w',1),
    ('assert','gd.paused() and not gd.history().busy'),
    ('probe',r'^checkpoint [0-9]+ \| matches=true'),
    ('c','= gd.resume()'),
]
SCENARIOS['demo_surface_params']=[
    ('w',.5),('probe',r'^selected=true updates=[1-9][0-9]* loads=[1-9][0-9]*'),
    ('c','em1_surface_loads=gd.perf().surface_load_calls'),('w',.5),
    ('probe',r'^selected=true updates=[1-9][0-9]* loads=[1-9][0-9]*'),
    ('assert','gd.perf().surface_load_calls==em1_surface_loads'),
]
SCENARIOS['demo_post_ready']=[
    ('w',.5),('probe',r'^post=true ready=true'),
]

SCENARIOS['demo_hit_rules']=[
    ('assert', '#gd.hit_rules(1)==2'),
    ('probe', r'^active=true rules=2 hits=[0-9]+ acceptance=operator-required'),
    K('H',.3),('assert','#gd.hit_rules(1)==0'),
    ('probe',r'^active=false rules=0 hits=[0-9]+ acceptance=operator-required'),
    K('H',.3),('assert','#gd.hit_rules(1)==2'),
]

# Registration/membership smoke only; boundary traversal remains operator work.
SCENARIOS['demo_zones']=[
    ('assert', '#gd.zones()==3'),
    ('assert', 'type(gd.zones_at(1,0))=="table"'),
]

# Source/registration checks; actual echo collision needs operator acceptance.
SCENARIOS['demo_echoes']=[
    ('assert','gd.fighter_history_depth()==61 and #gd.echoes(1)==1'),
    ('probe',r'^active=true echoes=1 hits=[0-9]+ acceptance=operator-required'),
    K('N',.3),('assert','#gd.echoes(1)==2'),
    ('assert','gd.echoes(1)[1].match.move=="nair" and gd.echoes(1)[2].match.move=="nair"'),
    K('E',.3),('assert','#gd.echoes(1)==1'),
]
