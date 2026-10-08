-- en_host.lua - TEST DRIVER, HOST side of the Envoy loopback set: from the Atlas main menu through ONLINE (a main-menu row now, hovered = 68),
-- switches Envoy on with gd.netplay_act("envoy", true) (the host's Online > Envoy preference; the menu readback does not follow the Atlas
-- cursor, so the row is not driven by presses), hosts a room, logs "ROOMCODE <code>" and waits for the lobby. The set itself is driven by
-- run_set.py over the console (stocks/time: MELEE_NETPLAY_STOCKS / MELEE_NETPLAY_MINUTES are not read by the menu path; the lobby settings apply).
-- @name: Envoy net test - host
-- @version: 2.0.0
-- @gameplay: true
local function step(msg) gd.log("en_host: " .. msg) gd.label("en_host: " .. msg) end
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
  step("before: " .. tostring(gd.netplay_act("envoy")))
  gd.netplay_act("envoy", true)
  step("the host's Envoy preference is now: " .. tostring(gd.netplay_act("envoy")))
  step("ONLINE PLAY -> Host a Room")
  pick(function() return gd.menu().item == "Host a Room" end)
  if not gd.wait_until(function() local c = gd.netplay().code return c ~= "" and not c:find("?", 1, true) end, 1800) then step("no room code from the server") return end
  step("room " .. gd.netplay().code .. " - waiting for the guest")
  gd.log("ROOMCODE " .. gd.netplay().code)
  if not gd.wait_until(function() return gd.netplay().phase == "lobby" end, 36000) then step("the guest never arrived") return end
  step("lobby")
end)
