-- Windows LAB execution gate for the shallow Goku package. No XV2 fidelity claim.
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    assert(gd.lab_mode(), 'not LAB mode')
    gd.cpu_mode(2, 'stand'); gd.teleport(1, 0, 0); gd.teleport(2, -55, 0)
    gd.set_percent(1, 0); gd.set_percent(2, 0); gd.wait(30)
    assert(gd.fighter_lua(1), 'Goku fighter Lua did not load')
    -- Native article models load lazily. Warm every tier before a MEM1 snapshot:
    -- native-side model caches otherwise outlive the bytes restored by loadstate.
    for _,held in ipairs({2,28,53}) do
      gd.input(1,{buttons='B'},held);gd.wait(150)
      gd.input(1,{},1);gd.wait(3)
    end
    gd.log('GOKUCHECK all article models warmed before baseline snapshot')
    gd.savestate(1); gd.wait(2)
    local cases = {
      {'n-tap', {}, 2, 'KameTap', 0},
      {'n-mid', {}, 28, 'KameMid', 1},
      {'n-full', {}, 53, 'KameFull', 2},
      {'s', {x=127}, 2, 'Rush'},
      {'hi', {y=127}, 2, 'Recovery'},
      {'lw', {y=-127}, 2, 'Counter'},
    }
    local total=0
    for _,air in ipairs({false,true}) do
      for _,case in ipairs(cases) do
        if not air or case[3]==2 then -- long charge tiers are isolated on the ground
        gd.input(1, {}, 1);gd.loadstate(1);gd.wait(3)
        if air then gd.teleport(1, 0, 95);gd.wait(2) end
        local want=case[4]
        if air and want=='Recovery' then want='RecoveryAir' end  -- cape pair: air partner state
        local input={buttons='B'}
        for k,v in pairs(case[2]) do input[k]=v end
        gd.input(1,input,case[3])
        local seen,article,max_charge,first,last,orb=false,false,0,nil,nil,false
        for tick=1,170 do
          gd.wait(1)
          local p=gd.player(1)
          if p.motion_name==want then seen=true;first=first or p.action_frame;last=p.action_frame end
          local lua=assert(gd.fighter_lua(1),'Lua profile disappeared')
          assert(lua.faults==0,'Lua fault: '..tostring(lua.last_fault))
          max_charge=math.max(max_charge,lua.state.charge or 0)
          assert(#(gd.hitboxes(1) or {})<=4,'more than four live fighter hitboxes')
          for _,item in ipairs(gd.items() or {}) do
            if case[5]~=nil and item.owner_port==1 and item.geno_kind==case[5] then article=true end
            if item.owner_port==1 and item.geno_kind==3 then orb=true end
          end
        end
        gd.log(string.format('GOKUCHECK case=%s air=%s state=%s seen=%s article=%s orb=%s charge=%d af=%s..%s final=%s',
          case[1],tostring(air),case[4],tostring(seen),tostring(article),tostring(orb),max_charge,tostring(first),tostring(last),tostring(gd.player(1).motion_name)))
        assert(seen,'missing state '..want)
        if case[1]=='n-full' then assert(orb,'no KameOrb charge article during the charge') end
        if case[5]~=nil then assert(article,'no matching Kamehameha article for '..case[1]) end
        total=total+1
        end
      end
    end
    gd.log('GOKUCHECK PASS '..total..' ground/air casts, all8 special inputs, charge tiers, article spawns, zero Lua faults')
  end)
  if not ok then gd.log('GOKUCHECK FAIL '..tostring(why)) end
  gd.quit()
end)
