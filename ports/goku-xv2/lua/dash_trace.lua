-- debug trace (DASHTR): x / velocity per frame through Dash and into a dash attack
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000))
    gd.cpu_mode(2, 'stand')
    local function tp(p,x,y) for i=1,80 do if pcall(gd.teleport,p,x,y) then return end gd.wait(30) end end
    tp(1,-60,0); tp(2,150,0); gd.wait(40)
    gd.input(1,{x=127},3); gd.wait(3); gd.input(1,{},1); gd.wait(30); tp(1,-60,0); gd.wait(30)
    local p = gd.player(1); local ks = {}
    for k in pairs(p) do ks[#ks+1]=k end table.sort(ks); gd.log('DASHTR keys '..table.concat(ks,','))
    local pressed = false
    for t=1,60 do
      local btn = nil
      if not pressed and gd.player(1).motion_name=='Dash' and (gd.player(1).action_frame or 0)>=5 then btn='A'; pressed=true end
      gd.input(1, btn and {x=0,buttons=btn} or (pressed and {} or {x=127}), 1); gd.wait(1)
      local q=gd.player(1)
      gd.log(string.format('DASHTR t%d %s af%s x %.2f vx %s gr %s animid %s', t, tostring(q.motion_name), tostring(q.action_frame), q.x, tostring(q.vx), tostring(q.ground_vel), tostring(q.anim_id)))
    end
  end)
  gd.log('DASHTR done '..tostring(ok)..' '..tostring(why)); gd.quit()
end)
