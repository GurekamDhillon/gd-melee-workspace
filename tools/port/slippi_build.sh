# Sourced by build.sh after native shims have compiled. Shares that script's
# fail-fast behavior and per-lane GW_* paths; never changes the curated template.
slippi_link="$GW_BUILD_ROOT/.slippi_link_objects.rsp"
slippi_names=(gw_slippi_pad gw_slippi_wire gw_slippi_peer gw_slippi_match_json gw_slippi_match gw_slippi_mode)
slippi_parts=(callbacks compress host list packet peer protocol win32)

if [ -f "$GW_MELEE/pc/platform/gw_slippi_peer.c" ] ||
   [ -f "$GW_MELEE/pc/platform/gw_slippi_match.c" ]; then
    enet_include="$GW_MELEE/extern/enet/include"
    [ -f "$enet_include/enet/enet.h" ] || gw_die "Slippi requires vendored ENet headers"
    # agent_new.sh backdates sources and hardlinks old objects. Timestamps cannot
    # establish that this lane's ENet revision was compiled. Include the compiler,
    # flags and all public headers in each object's content key instead.
    enet_config="$( {
        "$GW_CLANG" --version
        printf '%s\n' "$GW_CLANG" '--target=i686-pc-windows-msvc -c -O2'
        find "$enet_include" -type f -name '*.h' -print0 | sort -z | xargs -0 sha256sum
    } | sha256sum )"
    for enet_part in "${slippi_parts[@]}"; do
        enet_source="$GW_MELEE/extern/enet/$enet_part.c"
        enet_object="$GW_SHIMOBJ/enet_$enet_part.obj"
        [ -f "$enet_source" ] || gw_die "missing ENet source $enet_part.c"
        enet_key="$( { printf '%s\n' "$enet_config"; sha256sum "$enet_source"; } | sha256sum )"
        if [ ! -f "$enet_object" ] || [ ! -f "$enet_object.sha256" ] ||
           [ "$(cat "$enet_object.sha256")" != "$enet_key" ]; then
            echo "ENet  $enet_part"
            # Replace the directory entry to preserve agent_new.sh hardlinks.
            "$GW_CLANG" --target=i686-pc-windows-msvc -c -O2 -I "$enet_include" \
                "$enet_source" -o "$enet_object.tmp"
            mv -f "$enet_object.tmp" "$enet_object"
            printf '%s\n' "$enet_key" > "$enet_object.sha256.tmp"
            mv -f "$enet_object.sha256.tmp" "$enet_object.sha256"
        fi
    done
    slippi_needs_enet=1
else
    slippi_needs_enet=0
fi

# Strip these explicitly managed optional objects even if a lane's old curated
# file contains them. All other objects retain their original order and paths.
grep -Ev '[/\\](gw_slippi_(pad|wire|peer|match_json|match|mode)|enet_(callbacks|compress|host|list|packet|peer|protocol|win32))\.obj"?\r?$' \
    "$GW_LINK_OBJECTS" > "$slippi_link"
for slippi_name in "${slippi_names[@]}"; do
    if [ -f "$GW_MELEE/pc/platform/$slippi_name.c" ]; then
        [ -f "$GW_SHIMOBJ/$slippi_name.obj" ] || gw_die "missing compiled Slippi shim $slippi_name"
        printf '"%s/%s.obj"\n' "$GW_SHIMOBJ" "$slippi_name" >> "$slippi_link"
    fi
done
if [ "$slippi_needs_enet" = 1 ]; then
    for enet_part in "${slippi_parts[@]}"; do
        printf '"%s/enet_%s.obj"\n' "$GW_SHIMOBJ" "$enet_part" >> "$slippi_link"
    done
fi
GW_LINK_OBJECTS="$slippi_link"
