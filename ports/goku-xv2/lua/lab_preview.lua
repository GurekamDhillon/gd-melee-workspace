-- Persistent, visible LAB preview. Captures a frame and leaves controls to the user.
gd.run(function()
  assert(gd.wait_until(function() return gd.match().active and gd.match().frame > 100 end, 6000), 'no Goku preview match')
  gd.cpu_mode(2, 'stand')
  gd.teleport(1, -12, 0);gd.teleport(2, 22, 0)
  gd.debug_stage(0)
  gd.debug_draw(1,gd.draw.MODEL);gd.debug_draw(2,gd.draw.MODEL)
  gd.wait(90)
  local p=gd.player(1)
  gd.log('GOKUPREVIEW model loaded joints='..tostring(p.joint_count)..' hurtboxes='..tostring(p.hurtbox_count)..' clip='..tostring(p.anim_name))
  local ok,path=gd.screenshot('goku-v02-live.png')
  gd.log('GOKUPREVIEW screenshot queued='..tostring(ok)..' path='..tostring(path))
  -- No gd.quit(): keep the LAB running for the user.
end)
