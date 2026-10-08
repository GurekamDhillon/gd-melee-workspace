-- en_guest.lua - TEST DRIVER, GUEST side of the Envoy loopback set: Atlas main menu > ONLINE > Join a Room, then joins THE HOST'S ROOM BY CODE:
-- the code is MELEE_LAB_ROOM (gd.lab_env("ROOM")) when the driver set it, else run_set.py sends gd.netplay_act("code", ...) over the console.
-- Never random matchmaking. The set itself is driven by run_set.py over the console.
-- @name: Envoy net test - guest
-- @version: 2.0.0
-- @gameplay: true
local function step(msg) gd.log("en_guest: " .. msg) gd.label("en_guest: " .. msg) end
local function pick(ok, max)
  for _ = 1, max or 12 do
    if ok() then break end
    gd.press(1, "Down", 4)
    gd.wait(8)
  end
  gd.press(1, "A", 4)
  gd.wait(10)
end
gd.run(function()
  gd.wait_until(function() return gd.scene().name == "GS_FRONTEND" end, 3600)
  gd.wait(30)
  step("main menu -> ONLINE")
  pick(function() return gd.menu().native_hovered == 68 end)
  if not gd.wait_until(function() return gd.menu().screen == "ONLINE PLAY" end, 600) then step("never reached ONLINE PLAY") return end
  step("ONLINE PLAY -> Join a Room")
  gd.wait(60)
  gd.press(1, "Down", 4) gd.wait(40) -- Host a Room -> Join a Room (the readback does not follow the Atlas cursor)
  gd.press(1, "A", 4) gd.wait(10)
  gd.wait_until(function() return gd.menu().screen == "JOIN ROOM" end, 600)
  step("on the JOIN ROOM screen")
  local env = gd.lab_env("ROOM")
  if env and #env == 4 then
    step("room code from MELEE_LAB_ROOM: " .. env)
    gd.netplay_act("code", env)
  end
  local t = 0
  while t < 36000 do
    local c = gd.netplay().code
    if #c == 4 and not c:find("?", 1, true) then break end
    gd.wait(1)
    t = t + 1
  end
  step("joining " .. gd.netplay().code)
  gd.press(1, "A", 4)
  if not gd.wait_until(function() return gd.netplay().phase == "lobby" end, 3600) then step("could not join: " .. gd.netplay().status) return end
  step("lobby")
end)
