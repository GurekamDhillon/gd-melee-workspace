-- On-screen cycle of Goku's ground rows next to an idle Mario (visible: run without turbo). Logs GROUNDSHOW lines.
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no LAB match')
    gd.cpu_mode(2, 'stand')
    gd.teleport(1, -12, 0); gd.teleport(2, 14, 0)
    gd.wait(60)
    local function step(name, spec, frames, after)
      gd.input(1, {}, 1); gd.wait(2)
      gd.set_percent(2, 0)
      gd.input(1, spec, frames)
      local seen = {}
      for _ = 1, after do
        gd.wait(1)
        local m = gd.player(1).motion_name
        if m ~= seen[#seen] then seen[#seen + 1] = m end
      end
      gd.log('GROUNDSHOW ' .. name .. ' -> ' .. table.concat(seen, ' > '))
      gd.teleport(1, -12, 0); gd.teleport(2, 14, 0); gd.wait(25)
    end
    gd.log('GROUNDSHOW idle (Goku hover, Mario floor) ...'); gd.wait(120)
    step('walk', {x = 80}, 40, 50)
    step('run', {x = 127}, 40, 60)
    step('jab', {buttons = 'A'}, 2, 60)
    step('ftilt', {x = 60, buttons = 'A'}, 2, 50)
    step('utilt', {y = 50, buttons = 'A'}, 2, 50)
    step('dtilt', {y = -50, buttons = 'A'}, 2, 50)
    step('fsmash', {cx = 127}, 2, 80)
    step('usmash', {cy = 127}, 2, 80)
    step('dsmash', {cy = -127}, 2, 80)
    step('dashattack', {x = 127, buttons = 'A'}, 20, 70)
    step('grab', {buttons = 'Z'}, 2, 60)
    step('shield', {l = 200}, 30, 40)
    step('spotdodge', {l = 200, y = -127}, 3, 40)
    step('kamehameha', {buttons = 'B'}, 40, 140)
    step('rush', {x = 127, buttons = 'B'}, 3, 70)
    step('instant transmission', {y = 127, buttons = 'B'}, 3, 90)
    step('z-vanish', {y = -127, buttons = 'B'}, 2, 70)
    step('ki charge', {y = -127, buttons = 'B'}, 70, 90)
    gd.log('GROUNDSHOW DONE')
  end)
  if not ok then gd.log('GROUNDSHOW FAIL ' .. tostring(why)) end
  gd.quit()
end)
