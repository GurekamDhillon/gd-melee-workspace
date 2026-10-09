local function shot(tag) gd.wait(2); local ok, p = gd.screenshot(tag); gd.wait(3) end
local function reset() gd.input(1,{},1); gd.input(2,{},1); gd.loadstate(1); gd.wait(3); gd.teleport(1, -10, 0); gd.teleport(2, 40, 0); gd.wait(30) end
local P = {
  {'wait', {}}, {'turn', {{x=-80,n=8}}}, {'jab', {{buttons='A',n=3}}}, {'ftilt', {{buttons='A',x=45,n=3}}}, {'fsmash', {{buttons='A',x=127,n=3}}},
  {'usmash', {{buttons='A',y=127,n=3}}}, {'dsmash', {{buttons='A',y=-127,n=3}}}, {'nair', {{buttons='X',n=3},{n=6},{buttons='A',n=3}}},
  {'dair', {{buttons='X',n=3},{n=6},{cy=-127,n=3}}}, {'fp', {{buttons='B',n=3}}}, {'fk', {{buttons='B',y=-127,n=3}}},
  {'raptor', {{buttons='B',x=127,n=3}}}, {'dive', {{buttons='B',y=127,n=3}}}, {'shield', {{buttons='L',n=30}}}, {'crouch', {{y=-90,n=30}}},
  {'grab', {{buttons='Z',n=3}}}, {'run', {{x=127,n=30}}}, {'jump', {{buttons='X',n=14}}},
}
gd.run(function()
  assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 120 end, 6000), 'no match')
  gd.wait(30); gd.savestate(1); gd.wait(2)
  for _, p in ipairs(P) do
    reset()
    for _, st in ipairs(p[2]) do local n = st.n; gd.input(1, st, n); gd.wait(n) end
    for k = 1, 3 do gd.wait(6); shot(p[1] .. k) end
  end
  gd.wait(20); gd.quit()
end)
