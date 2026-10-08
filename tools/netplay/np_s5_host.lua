-- np_s5_host.lua - TEST DRIVER, HOST side of the Envoy stage-5 loopback proofs (np_envoy_resume.py): Atlas main menu > ONLINE, the host's Envoy mode
-- (MELEE_LAB_ENVOY_MODE = versus | coop, read with gd.lab_env("ENVOY_MODE")), Host a Room, then it waits. The host stays up for the whole scenario: when a guest leaves, the game
-- itself reopens the room with the same code. The lobby is driven by the Python driver over the console.
-- @name: Envoy stage 5 test - host
-- @version: 1.0.0
-- @gameplay: true
local function step(msg) gd.log("np_s5_host: " .. msg) gd.label("np_s5_host: " .. msg) end
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
  local mode = gd.lab_env("ENVOY_MODE") or "versus"
  gd.netplay_act("envoymode", mode)
  step("the host's Envoy mode is now: " .. tostring(gd.netplay_act("envoymode")) .. " (" .. mode .. ")")
  step("ONLINE PLAY -> Host a Room")
  pick(function() return gd.menu().item == "Host a Room" end)
  if not gd.wait_until(function() local c = gd.netplay().code return c ~= "" and not c:find("?", 1, true) end, 1800) then step("no room code from the server") return end
  step("room " .. gd.netplay().code .. " - waiting for the guest")
  gd.log("ROOMCODE " .. gd.netplay().code)
end)
