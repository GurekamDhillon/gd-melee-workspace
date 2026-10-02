# Seventh bounded correction: cooldown refund owns its spend
Same isolated gene-actions lane, same exact ownership; sixth pass terminal. Independent Sol confirms sixth-pass mark reset/sourcehost fixes work. One supported default-Cinder defect remains.

Actual-Core repro using existing scene/charge helpers:
local r,obs,st,w=scene(8202)
local ga=GA.new(Core,B,w)
charge(r,'player','direct_hit',3,'first')
st.on_apply_effect=function(rr)
 ga:on_room_leave()
 assert(Core.tick(rr,90))
 charge(rr,'player','direct_hit',3,'next')
 assert(Core.activate(rr,'player','assault',{target='enemy'}))
 assert(rr.hosts.player.state.assault.ready_at==180)
end
st.refuse_effect=true
assert(ga:begin('player','assault'));ga:advance()
-- Actual ready_at=0 and ready=true; expected preserve NEW activation ready_at=180.

Old refund gene_actions.lua around335 unconditionally st.ready_at=pre.ready_at despite later successful same-slot spend. Rollback must conditionally restore ONLY original action's cooldown if still owned, preserve newer activation's cooldown. Keep refund charge accounting/capacity and concurrent earned charge correct. Use reliable spend ownership (ephemeral Core/state revision if needed); comparing equal timestamps alone must not admit same-frame equal-value ABA. No savefields/schema changes. Add above real default-Core singleengine regression, same-frame spend if relevant, no-spend callback earn-only refund still restores original cooldown. Preserve all31findinggroups and prior reentrant/run/gene/state/mark/refundnever/expiry guarantees. Don't replace targeted refunds with whole-run snapshots.

Run focused Core/actions/checkpoint/legacy/catalogue; report exact evidence and limitations to gene-actions-followup-7-report.md, freeze. No main/native/build/install/commit/newmodel lane edits.
