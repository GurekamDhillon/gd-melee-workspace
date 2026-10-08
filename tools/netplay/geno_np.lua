-- geno_np.lua - INPUT SCRIPT for the Geno slice 7 lobby proofs: one file, both roles (MELEE_LAB_ROLE=host|guest).
-- The Atlas main menu > ONLINE > Host a Room / Join a Room, the room code by MELEE_LAB_ROOM (or the console), and then the
-- lobby with a CHOSEN fighter: MELEE_LAB_CK=<resident alias CharacterKind> goes in with gd.netplay_act("char", ck, 0). A pick the
-- opponent cannot play is refused by the game with a reason (gd.netplay().refusal); this script logs it as
--     GENOLOBBY pick refused: <reason>
-- and ends, so a driver can read the reason. Otherwise it plays MELEE_LAB_GAMES games (default 1) of a set: pick, strike/ban,
-- ready, match, results, back to the lobby, and logs  GENOLOBBY game <n> started / ended.
--
--   MELEE_SCENE=mode=menu MELEE_SCRIPT=<this file> MELEE_LAB_ROLE=host MELEE_LAB_CK=122 MELEE_LAB_GAMES=2
--
-- @name: Geno lobby proof
-- @version: 1.0.0
-- @gameplay: true

local role = gd.lab_env("ROLE") or "host"
local want_ck = tonumber(gd.lab_env("CK") or "")
local games = tonumber(gd.lab_env("GAMES") or "1") or 1

local function step(msg)
  gd.log("GENOLOBBY " .. role .. ": " .. msg)
  gd.label("geno_np " .. role .. ": " .. msg)
end

local function pick(ok, max)
  for _ = 1, max or 12 do
    if ok() then break end
    gd.press(1, "Down", 4)
    gd.wait(8)
  end
  gd.press(1, "A", 4)
  gd.wait(10)
end

local function to_online()
  gd.wait_until(function() return gd.scene().name == "GS_FRONTEND" end, 3600)
  gd.wait(30)
  step("main menu -> ONLINE")
  pick(function() return gd.menu().native_hovered == 68 end)
  return gd.wait_until(function() return gd.menu().screen == "ONLINE PLAY" end, 600)
end

local function code_ready()
  local c = gd.netplay().code
  return #c == 4 and not c:find("?", 1, true)
end

local function enter_room()
  if not to_online() then step("never reached ONLINE PLAY") return false end
  if role == "host" then
    step("ONLINE PLAY -> Host a Room")
    pick(function() return gd.menu().item == "Host a Room" end)
    if not gd.wait_until(code_ready, 1800) then step("no room code from the server") return false end
    gd.log("ROOMCODE " .. gd.netplay().code)
    step("room " .. gd.netplay().code .. " - waiting for the guest")
    if not gd.wait_until(function() return gd.netplay().phase == "lobby" end, 36000) then step("the guest never arrived") return false end
  else
    step("ONLINE PLAY -> Join a Room")
    gd.wait(60)
    gd.press(1, "Down", 4) gd.wait(40)
    gd.press(1, "A", 4) gd.wait(10)
    gd.wait_until(function() return gd.menu().screen == "JOIN ROOM" end, 600)
    local env = gd.lab_env("ROOM")
    if env and #env == 4 then gd.netplay_act("code", env) end
    local t = 0
    while not code_ready() and t < 36000 do
      if t % 300 == 299 then gd.press(1, "Y", 4) end
      gd.wait(1)
      t = t + 1
    end
    if not code_ready() then step("no room code") return false end
    step("joining " .. gd.netplay().code)
    -- the A press is repeated: a press that lands before the screen takes input is lost (seen once in a run with a lagged link)
    local waited = 0
    while waited < 3600 and gd.netplay().phase ~= "lobby" do
      if waited % 240 == 0 and gd.netplay().phase == "idle" then gd.press(1, "A", 4) end
      gd.wait(30)
      waited = waited + 30
    end
    if gd.netplay().phase ~= "lobby" then
      step("could not join: " .. gd.netplay().status .. " (phase " .. gd.netplay().phase .. ")") return false
    end
  end
  step("lobby")
  return true
end

-- the pick: the chosen fighter, once the peer's identity list has arrived (common_fighters is -1 until then)
local function do_pick()
  if want_ck then
    gd.wait_until(function() return (gd.netplay().common_fighters or 0) >= 0 end, 1800)
    step(string.format("common fighters %s, peer defines complete %s", tostring(gd.netplay().common_fighters), tostring(gd.netplay().peer_defines)))
    local ok = gd.netplay_act("char", want_ck, 0)
    if not ok then
      step("pick refused: " .. gd.netplay().refusal)
      gd.log("GENOLOBBY pick refused: " .. gd.netplay().refusal)
      return false
    end
  else
    gd.netplay_act("char")
  end
  return true
end

local function play_lobby()
  local picked = false
  while not gd.match().active do
    gd.wait(30)
    local np = gd.netplay()
    if np.phase == "lobby" then
      local me = np.players[np.me + 1]
      local lp = np.lobby
      if (lp == "char_blind" and not me.locked) or
         ((lp == "char_winner" or lp == "char_loser") and np.turn == np.me) then
        if not do_pick() then return false end
      elseif (lp == "strike" or lp == "ban" or lp == "pick") and np.turn == np.me then
        -- Battlefield is entry 1 (the pad bot's default edge, 62, is its half-width): pick it, and strike/ban from the far end of the list
        if lp == "pick" and np.stages[1] == 0 then
          gd.netplay_act("stage", 1)
        else
          for i = #np.stages, 2, -1 do
            if np.stages[i] == 0 then gd.netplay_act("stage", i) break end
          end
        end
      elseif lp == "ready" and not me.ready then
        gd.netplay_act("ready", true)
      end
    elseif np.phase == "failed" then
      step("connection failed: " .. np.status)
      return false
    end
  end
  return true
end

-- coverage observer (as tools/netplay/geno_cov.lua)
local seen, gseen, last = {}, {}, 0
local function note(port)
  local p = gd.player(port)
  if not p then return end
  local m = p.action or p.motion
  if m == nil then return end
  seen[port] = seen[port] or {}
  gseen[port] = gseen[port] or {}
  seen[port][m] = (seen[port][m] or 0) + 1
  if m >= 0x400 then gseen[port][m] = (gseen[port][m] or 0) + 1 end
end

local function count(t) local n = 0 for _ in pairs(t or {}) do n = n + 1 end return n end

local function report(f)
  for port = 1, 2 do
    local p = gd.player(port)
    local l = gd.fighter_lua and gd.fighter_lua(port) or nil
    local list = {}
    for m, c in pairs(gseen[port] or {}) do list[#list + 1] = string.format("%x:%d", m, c) end
    table.sort(list)
    gd.log(string.format("GENOCOV f=%d p%d moves=%d geno=%d luafaults=%s stocks=%s pct=%s [%s]", f, port, count(seen[port]), count(gseen[port]),
      l and tostring(l.faults) or "n/a", p and tostring(p.stocks) or "?", p and tostring(p.percent) or "?", table.concat(list, " ")))
  end
end

function on_frame()
  local m = gd.match()
  if not m.active then return end
  last = m.frame
  note(1) note(2)
  if m.frame % 1200 == 0 then report(m.frame) end
end

function on_match_end() report(last) end

gd.run(function()
  if not enter_room() then gd.wait(120) gd.quit() return end
  for g = 1, games do
    if not play_lobby() then gd.wait(120) gd.quit() return end
    gd.log(string.format("GENOLOBBY %s: game %d started", role, g))
    -- the match runs; the results screen needs a press now and then
    local t = 0
    while t < 60 * 60 * 20 do
      gd.wait(60)
      t = t + 60
      if not gd.match().active then break end
    end
    gd.log(string.format("GENOLOBBY %s: game %d ended (match inactive)", role, g))
    local back = 0
    while gd.netplay().phase ~= "lobby" and back < 60 * 60 * 3 do
      if gd.scene().name ~= "GS_FRONTEND" then gd.press(1, "A", 4) end
      gd.wait(60)
      back = back + 60
    end
    if gd.netplay().phase ~= "lobby" then step("never back in the lobby: " .. gd.netplay().phase .. " " .. gd.netplay().status) break end
  end
  gd.log("GENOLOBBY " .. role .. ": SET DONE")
  gd.wait(120)
  gd.quit()
end)
