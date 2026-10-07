-- Usage from workspace root: lua tools/maze/check.lua <mod folder> <mission name>
local base=(os.getenv('GW_MELEE') or 'melee')..'/pc/scripts/examples/missions/scripts/'
local D={maze_clearance=assert(loadfile(base..'maze_clearance.lua'))()()}
local C=assert(loadfile(base..'maze_check.lua'))()(D);D.maze_check=C
D.maze_world_check=assert(loadfile(base..'maze_world_check.lua'))()(D)
local folder=assert(arg[1]);local name=assert(arg[2])
local report=C.folder({mod_read=function(path)
  local f=io.open(folder..'/'..path,'rb');if not f then return nil end
  local text=f:read('a');f:close();return text
end},name)
for _,e in ipairs(report.errors) do print(e) end
assert(report.ok,'maze proof failed')
print('maze proof PASS: start reaches goal; all chunks reachable; slots/seals/climbs/overlaps checked')
