-- Pad script for sweep_1p.py: let the scene run 600 logic frames, report, quit.
local done = false
function on_frame()
  if not done and gd.frame() >= 600 then
    done = true
    gd.log("sweep: reached 600 frames")
    gd.quit()
  end
end
