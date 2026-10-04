-- Opt-in acceptance diagnostics. No automatic input, casts or scene changes.
-- Registered in the owning roguelite script so FX ownership/cleanup stays valid.
local function envoy_probe_report(message)
 gd.log('envoy render probe: '..message)
 print(message)
end
gd.command('envoy_map',function(arg)
 local on=arg=='on'
 if not on and arg~='off' then envoy_probe_report('Use envoy_map on or envoy_map off; collision remains active.');return end
 gd.stage_view(on,false)
 envoy_probe_report('Map geometry '..(on and 'shown' or 'hidden')..'; collision unchanged.')
end,'envoy_map on|off: show/hide map geometry without removing collision')
gd.command('envoy_fx_probe',function(arg)
 if not gd.player(1) then envoy_probe_report('No player 1; enter a run first.');return end
 if arg~='' and arg~='cinder' and arg~='rime' then envoy_probe_report('Use envoy_fx_probe cinder or envoy_fx_probe rime.');return end
 local package=arg=='rime' and 'RogueRimeRelease' or 'RogueCinderRelease'
 local handle=gd.fx_play(package,1,0,0,16,0,1,1)
 if handle and handle>0 then
  if type(fx_handles)=='table' then fx_handles[#fx_handles+1]=handle end
  envoy_probe_report(package..' attached, handle '..tostring(handle)..'. Close the console to observe; repeat with map on/off.')
 else envoy_probe_report(package..' attachment refused; inspect FX logs.') end
end,'envoy_fx_probe cinder|rime: cast a diagnostic effect above player 1; no damage or gene spend')
