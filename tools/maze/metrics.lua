local base='melee/pc/scripts/examples/missions/scripts/'
local D={}
for _,n in ipairs({'maze_set','maze_metrics','maze_clearance','maze_topology','maze_check','maze_encounters','maze'})do
  local f=loadfile(base..n..'.lua');if f then D[n]=f()(D)end
end
for seed=1,1000 do local size=8+seed%13;local m=D.maze.generate(seed,{size=size});local q=D.maze_metrics.measure(m)
  print(table.concat({seed,size,q.branches,q.longest_dead_end,q.turns,q.cycles,q.adjacent_repeats,q.directions.left,q.directions.right,q.directions.up,q.directions.down},'\t'))
end
