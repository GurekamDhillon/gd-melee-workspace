-- en_guest.lua - TEST DRIVER, GUEST side of the Envoy loopback set: main menu > VERSUS > ONLINE > Join a Room, then waits for the room code (run_set.py
-- sends it with gd.netplay_act("code", ...)) and joins. The set itself is driven by run_set.py over the console.
-- @name: Envoy net test - guest
-- @version: 1.0.0
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
  step("main menu -> VERSUS")
  pick(function() return gd.menu().native_hovered == 1 end)
  gd.wait_until(function() return gd.menu().native_menu == 2 end, 600)
  gd.wait(20)
  step("VERSUS -> ONLINE")
  pick(function() return gd.menu().native_hovered == 64 end)
  if not gd.wait_until(function() return gd.menu().screen == "ONLINE PLAY" end, 600) then step("never reached ONLINE PLAY") return end
  step("ONLINE PLAY -> Join a Room")
  pick(function() return gd.menu().item == "Join a Room" end)
  gd.wait_until(function() return gd.menu().screen == "JOIN ROOM" end, 600)
  step("on the JOIN ROOM screen")
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
