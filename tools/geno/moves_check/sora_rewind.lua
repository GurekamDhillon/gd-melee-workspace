-- Rewind proof for the Sora define (or any fighter with articles): gd.rewind_test across a cast with its article in flight, across the side
-- special's dash chain, and across an air cast chain. Each case must pass with diff_compared == 0 ("0 simulation bytes differ").
-- Ends with "REWIND RESULT: PASS" or "REWIND RESULT: FAIL <why>". Run with run_scene.sh like moves_check.
local function rewind(name, frames)
  assert(gd.history(300, 1), 'history refused')
  local ok, why = gd.rewind_test(frames, true)
  if not ok then error(name .. ': rewind_test refused: ' .. tostring(why)) end
  local r
  for _ = 1, 3000 do
    gd.wait(1)
    r = gd.rewind_test_result()
    if r and r.phase == 0 and r.pass ~= nil then break end
  end
  gd.log(string.format('REWIND %s pass=%s diff=%s diff_compared=%s items=%d %s', name, tostring(r and r.pass), tostring(r and r.diff), tostring(r and r.diff_compared), #(gd.items() or {}), tostring(r and r.text)))
  if not (r and r.pass and r.diff_compared == 0) then error(name .. ': pass=' .. tostring(r and r.pass) .. ' diff_compared=' .. tostring(r and r.diff_compared)) end
end
gd.run(function()
  local ok, why = pcall(function()
    assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 90 end, 6000), 'no match')
    gd.cpu_mode(2, 'stand'); gd.teleport(1, 0, 0); gd.teleport(2, -70, 0); gd.set_percent(1, 0); gd.set_percent(2, 0)
    gd.wait(30); gd.savestate(1); gd.wait(2)
    -- 1: a ground cast, rewind begins 20 frames in (the article is alive during the 120 frames)
    gd.input(1, {buttons = 'B'}, 3); gd.wait(22)
    rewind('cast', 120)
    gd.loadstate(1); gd.wait(5)
    -- 2: the side special chain
    gd.input(1, {buttons = 'B', x = 127}, 3); gd.wait(10)
    rewind('side_dash', 100)
    gd.loadstate(1); gd.wait(5)
    -- 3: three casts in the air (Firaga, Blizzaga, Thundaga: articles of three kinds)
    gd.input(1, {buttons = 'X'}, 2); gd.wait(12)
    gd.input(1, {buttons = 'B'}, 3); gd.wait(45)
    gd.input(1, {buttons = 'B'}, 3); gd.wait(30)
    rewind('air_chain', 90)
    gd.log('REWIND RESULT: PASS')
  end)
  if not ok then gd.log('REWIND RESULT: FAIL ' .. tostring(why)) end
  gd.quit()
end)
