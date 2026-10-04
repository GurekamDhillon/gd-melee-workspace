# Controller remapping implementation

Authorised by `docs/prompts/codex-controls-remap.md`. Preserve dirty files; no
commits, game builds, game launches, Aurora edits or launcher edits.

1. Add a pure input mapping model and behavioural native tests first. Physical
   inputs carry a set of GC destinations; analog directions retain magnitude.
2. Include the runtime in shim_pad.c (no new link object). Capture native SDL
   inputs through public APIs; raw adapter input stays calibrated. Persist named
   profiles and device assignments through Settings_*; inherit legacy deadzones.
3. Add a kit list editor with controller selection, timed capture, swap/also,
   profiles, transforms, live readout and default-layout navigation. Restore via
   a real-time START+B hold during menu heartbeats.
4. Check actual C behaviour and syntax where the toolchain permits. Update
   controls docs, credits, and the requested report with precise remaining gates.

Tap jump cannot be disabled exactly by ordinary GC byte transforms while
preserving up tilt/aim. Do not silently clamp up or consult local-only profile
state inside simulation; record that requirement as unresolved unless a safe
existing deterministic input encoding is found.

## Implemented and checked

Model, shim runtime, settings capacity and persistence tests, kit editor, shipped
preset data, docs and report are in place. Independent read-only review found
selection/hotplug issues which were repaired. Final libclang parsing of the
three native TUs/fixture and PowerPC frontend reports zero error diagnostics;
named-path diff checks pass. Compiler executable invocation was denied, so
behavioural fixtures, linking and hardware acceptance remain unverified. No
game build or launch. Exact tap-jump-off remains unresolved under the packet's
ordinary-input requirement; packet K is not fully complete.
