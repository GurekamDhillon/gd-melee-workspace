local T=dofile('melee/pc/tests/envoy_testlib.lua');local D=T.rules()
for _,name in ipairs{'mod_schema','mod_pool','mod_synergy'}do D[name]=T.module(name,D)end
local pairs=D.mod_synergy.generate(D.mod_pool);local f=assert(io.open(arg[1] or 'tools/port/envoy_mod_synergy.tsv','w'))
f:write('a\tb\treasons\n');for _,pair in ipairs(pairs)do f:write(pair.a,'\t',pair.b,'\t',table.concat(pair.reasons,','),'\n')end;f:close();print('Generated '..#pairs..' interacting pairs')
