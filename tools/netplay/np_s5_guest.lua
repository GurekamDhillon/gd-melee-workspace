-- np_s5_guest.lua - TEST DRIVER, GUEST side of the Envoy stage-5 loopback proofs (np_envoy_resume.py): joins THE HOST'S ROOM BY CODE (MELEE_LAB_ROOM, never random matchmaking)
-- and joins it AGAIN whenever the game has dropped it back to the menu (a lost connection leaves the guest on the online screens). The code of the room is the host's.
-- @name: Envoy stage 5 test - guest
-- @version: 1.0.0
-- @gameplay: true
local function step(msg) gd.log("np_s5_guest: " .. msg) gd.label("np_s5_guest: " .. msg) end
local function pick(ok, max)
  for _ = 1, max or 12 do
    if ok() then break end
    gd.press(1, "Down", 4)
    gd.wait(8)
  end
  gd.press(1, "A", 4)
  gd.wait(10)
end
local code = gd.lab_env("ROOM")
local joins = 0
local function join()
  joins = joins + 1
  local s = gd.menu().screen
  step("join #" .. joins .. " from screen '" .. tostring(s) .. "'")
  if s ~= "ONLINE PLAY" and s ~= "JOIN ROOM" then
    pick(function() return gd.menu().native_hovered == 68 end)
    if not gd.wait_until(function() return gd.menu().screen == "ONLINE PLAY" end, 600) then step("never reached ONLINE PLAY") return false end
  end
  if gd.menu().screen == "ONLINE PLAY" then
    gd.wait(60)
    gd.press(1, "Down", 4) gd.wait(40) -- Host a Room -> Join a Room (the readback does not follow the Atlas cursor)
    gd.press(1, "A", 4) gd.wait(10)
  end
  if not gd.wait_until(function() return gd.menu().screen == "JOIN ROOM" end, 600) then step("never reached JOIN ROOM") return false end
  if code and #code == 4 then gd.netplay_act("code", code) end
  gd.wait(20)
  gd.press(1, "A", 4)
  return gd.wait_until(function() return gd.netplay().phase == "lobby" end, 3600)
end
gd.run(function()
  gd.wait_until(function() return gd.scene().name == "GS_FRONTEND" end, 3600)
  gd.wait(30)
  if join() then step("lobby") else step("could not join: " .. gd.netplay().status) end
  -- after that: whenever the connection is gone and the game is on a menu again, join again
  while true do
    gd.wait(60)
    local np = gd.netplay()
    if gd.scene().name == "GS_FRONTEND" and (np.phase == "idle" or np.phase == "failed") then
      gd.wait(120)
      np = gd.netplay()
      if gd.scene().name == "GS_FRONTEND" and (np.phase == "idle" or np.phase == "failed") then
        if join() then step("lobby (again)") else step("could not join again: " .. gd.netplay().status) end
      end
    end
  end
end)
