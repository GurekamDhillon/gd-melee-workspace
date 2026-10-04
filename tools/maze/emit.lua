-- Length-framed files on stdout, keeping Python a call-through rather than a port.
local base='melee/pc/scripts/examples/missions/scripts/'
local D={}
for _,name in ipairs({'maze_set','maze_clearance','maze_metrics','maze_topology','maze_check','maze_world_check','maze_route','maze_encounters','maze','maze_world'}) do
  D[name]=assert(loadfile(base..name..'.lua'))()(D)
end
local files
if arg[1]=='starter' then files=D.maze.starters()
else
  local templates=arg[7]and arg[7]~=''and assert(loadfile(arg[7],'t',{}))()or nil
  local m,name
  if arg[1]=='world'then
    local seeds={};if arg[8]then seeds['r'..arg[8]]=assert(tonumber(arg[9]))end
    m=D.maze_world.generate(assert(tonumber(arg[2])),{regions=assert(tonumber(arg[3])),size=assert(tonumber(arg[4])),seeds=seeds,templates=templates});name=arg[5]
  else
    m=D.maze.generate(assert(tonumber(arg[1])),{size=assert(tonumber(arg[2])),length=arg[4]and tonumber(arg[4])or nil,
      loops=arg[5]~='no-loops',boss=arg[6]=='boss',templates=templates});name=arg[3]
  end
  files=D.maze.files(m,name);files['maze-map.txt']=(m.world and D.maze_world.ascii(m)or D.maze.ascii(m))..'\n'
  local parts={bf_floor_4m=true}
  for _,c in ipairs(m.cells) do for _,p in ipairs(c.level.parts) do parts[p.part]=true end end
  if templates then
    for _,t in ipairs(templates) do for _,p in ipairs(t.level and t.level.parts or {}) do parts[p.part]=true end end
    files['missions/maze-chunks/library.lua']='return '..D.maze.encode(templates)..'\n'
  end
  local names={};for name in pairs(parts) do names[#names+1]=name end;table.sort(names)
  files['maze-assets.txt']=table.concat(names,'\n')..'\n'
end
local paths={};for p in pairs(files) do paths[#paths+1]=p end;table.sort(paths)
for _,p in ipairs(paths) do io.write(p,'\t',#files[p],'\n',files[p]) end
