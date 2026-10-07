-- en_host.lua - TEST DRIVER, HOST side of the Envoy loopback set: from the main menu through VERSUS > ONLINE, sets Stocks 1 and Time Limit 1 min, turns
-- Online > Envoy on THROUGH THE MENU ROW (the real toggle), hosts a room, waits for the lobby. The set itself is driven by run_set.py over the console.
-- @name: Envoy net test - host
-- @version: 1.0.0
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
local function goto_item(name)
  for _ = 1, 16 do
    if gd.menu().item == name then return true end
    gd.press(1, "Down", 4)
    gd.wait(8)
  end
  return gd.menu().item == name
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
  if goto_item("Stocks") then for _ = 1, 4 do gd.press(1, "Left", 4) gd.wait(6) end end
  if goto_item("Time Limit") then for _ = 1, 10 do gd.press(1, "Left", 4) gd.wait(6) end end
  if goto_item("Envoy") then
    step("the Envoy row is there; before: " .. tostring(gd.netplay_act("envoy")))
    gd.press(1, "Right", 4) gd.wait(10)
    step("Envoy row pressed Right; the host's preference is now: " .. tostring(gd.netplay_act("envoy")))
  else
    step("NO Envoy row found in the ONLINE menu (item=" .. tostring(gd.menu().item) .. ")")
  end
  step("ONLINE PLAY -> Host a Room")
  pick(function() return gd.menu().item == "Host a Room" end)
  if not gd.wait_until(function() local c = gd.netplay().code return c ~= "" and not c:find("?", 1, true) end, 1800) then step("no room code from the server") return end
  step("room " .. gd.netplay().code .. " - waiting for the guest")
  if not gd.wait_until(function() return gd.netplay().phase == "lobby" end, 36000) then step("the guest never arrived") return end
  step("lobby")
end)
