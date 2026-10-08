-- run_host.lua - TEST DRIVER, HOST side of the stage-run loopback proof (tools/netplay/run_pair.py): Atlas main menu > ONLINE > Host a Room with the
-- stage-run preference on (gd.netplay_act("run", true); MELEE_NETPLAY_RUN=1 does the same), logs "ROOMCODE <code>", waits for the lobby. The run itself is
-- driven by run_pair.py over the console. Local matchmaking server only.
-- @name: Stage run net test - host
-- @version: 1.0.0
-- @gameplay: true
local function step(msg) gd.log("run_host: " .. msg) gd.label("run_host: " .. msg) end
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
  gd.netplay_act("run", true)
  step("stage-run preference: " .. tostring(gd.netplay_act("run")))
  pick(function() return gd.menu().item == "Host a Room" end)
  if not gd.wait_until(function() local c = gd.netplay().code return c ~= "" and not c:find("?", 1, true) end, 1800) then step("no room code from the server") return end
  gd.log("ROOMCODE " .. gd.netplay().code)
  if not gd.wait_until(function() return gd.netplay().phase == "lobby" end, 36000) then step("the guest never arrived") return end
  step("lobby")
end)
