#!/usr/bin/env bash
# Atlas online isolation guards (step 6). Textual by design: they say what the files may contain, and fail loudly.
#   tools/port/check_atlas_online.sh [GAME_CHECKOUT]     (default: $GW_MELEE, else <root>/melee)
#
#   1  no pure Atlas unit (gw_ui_*.c/.h) includes a netplay header or names a netplay function; the host halves
#      (gw_script_ui*.inc) name no netplay function either, except the one read gw_Netplay_Enabled (the registry's online rule)
#   2  the game-side adapter only READS netplay state (an allow-list); every write stays in gmfrontend_online.inc
#   3  the adapter adds no netplay call the legacy lobby did not already make
#   4  the intent-to-menu-bit table: one line per intent, exactly once
#   5  the pad term of the menu input is the legacy retail read, untouched
#   6  no input mask and no mod hook from the Atlas online files
#   7  the opponent's blind pick never reaches the host view (Netplay_FighterName sits after fl_card_portrait)
#   8  the room door writes game memory only through gs_ui_put_be32 (the out-parameters are big-endian guest memory)
#   9  every Ui_Room* call site is in the function expected to make it (the adapter's fa_room_* functions; fl_frame only for the freeze)
#   10 a click on a stage that is not open cannot reach Confirm (the stage_click branch tests fl_stage_open and fl_my_stage_turn first)
set -u
G="${1:-${GW_MELEE:-$(cd "$(dirname "$0")/../.." && pwd)/melee}}"
fail=0
bad() { echo "FAIL: $*"; fail=1; }

# 1. No pure Atlas file includes a netplay header or names a netplay function; the host halves name none but the one read.
hits=$(grep -n -E '#include[[:space:]]*[<"][^>"]*netplay|\bNetplay_[A-Za-z]|\bgw_Netplay_' "$G"/pc/platform/gw_ui_*.c "$G"/pc/platform/gw_ui_*.h 2>/dev/null || true)
if [ -n "$hits" ]; then
    echo "$hits"
    bad "a pure Atlas unit touches netplay (lines above)"
fi
hits=$(grep -n -E '#include[[:space:]]*[<"][^>"]*netplay|\bNetplay_[A-Za-z]|\bgw_Netplay_' "$G"/pc/platform/gw_script_ui*.inc 2>/dev/null | grep -v -E '\bgw_Netplay_Enabled\b' || true)
if [ -n "$hits" ]; then
    echo "$hits"
    bad "a host Atlas file touches netplay beyond gw_Netplay_Enabled (lines above)"
fi

# 2. The game-side adapter only READS netplay state: every Netplay_ name in it is in the read allow-list. All writes stay in
#    gmfrontend_online.inc, where the state machine is.
ADAPTER="$G/src/melee/gm/gmfrontend_atlas_online.inc"
READS="LobbyInfo LobbyPlayer LobbyMe LobbyPhase LobbyStage LobbyStageGroup LobbyStageOpen IsHost RoomCode Ping PlayerName FighterName MenuStatus Turbo Envoy StageMode TurboPref EnvoyPref RandomStatus RandomSeconds CodeChar CodeSlot"
if [ -f "$ADAPTER" ]; then
    for name in $(grep -o -E 'Netplay_[A-Za-z]+' "$ADAPTER" | sort -u | sed 's/^Netplay_//'); do
        case " $READS " in *" $name "*) ;; *) bad "the adapter calls Netplay_$name, which is not a read (writes belong in gmfrontend_online.inc)";; esac
    done
fi

# 3. The adapter introduces no Netplay call the legacy lobby did not already make.
LEGACY="$G/src/melee/gm/gmfrontend_online.inc"
if [ -f "$ADAPTER" ] && [ -f "$LEGACY" ]; then
    for name in $(grep -o -E 'Netplay_[A-Za-z]+' "$ADAPTER" | sort -u); do
        grep -qw "$name" "$LEGACY" || grep -qw "$name" "$G/src/melee/gm/gmfrontend.c" || bad "$name is new: the adapter must not add a netplay call"
    done
fi

# 4. The intent to menu-bit table. Intents cross the shim BY NAME (at_room_intent_name), and each name maps to one MenuInput bit,
#    on one line, once. (accept is A: the retail pad read sets both Confirm and AButton for it, and the ready phase tests AButton.)
if [ -f "$ADAPTER" ]; then
    for pair in "up:MenuInput_Up" "down:MenuInput_Down" "left:MenuInput_Left" "right:MenuInput_Right" "accept:MenuInput_Confirm" "accept:MenuInput_AButton" \
                "back:MenuInput_Back" "start:MenuInput_StartButton" "copy:MenuInput_XButton" "paste:MenuInput_YButton" "page_l:MenuInput_LTrigger" "page_r:MenuInput_RTrigger"; do
        k="${pair%%:*}"; b="${pair##*:}"
        n=$(grep -c -E "strcmp\(n, \"$k\"\) == 0\).*$b" "$ADAPTER")
        [ "$n" = 1 ] || bad "intent \"$k\" must map to $b exactly once in the adapter (found $n)"
    done
    # 5. The pad term of the menu input is the legacy read, untouched.
    grep -q 'mn_80229624(4) | ' "$G/src/melee/gm/gmfrontend_online.inc" || bad "fl_frame no longer ORs the retail pad read (mn_80229624(4)) with the mouse bits"
    # 7. The opponent's blind pick never reaches the host view: the one Netplay_FighterName call sits inside fa_room_fighter, after
    #    the same fl_card_portrait test the legacy card used to decide what to show.
    [ "$(grep -c 'Netplay_FighterName' "$ADAPTER")" = 1 ] || bad "Netplay_FighterName must be called exactly once in the adapter, inside fa_room_fighter"
    awk '/static .*fa_room_fighter/ {f=1} f && /fl_card_portrait/ {ok=1} f && /Netplay_FighterName/ {exit !ok}' "$ADAPTER" || bad "fa_room_fighter reads the fighter before asking fl_card_portrait (the blind pick would leak)"
fi

# 6. No mask and no mod hook from the Atlas online files.
hits=$(grep -n -E 'input_mask|input_chord|gs_require_offline' "$G"/pc/platform/gw_ui_room*.c "$G"/pc/platform/gw_ui_room*.h "$G"/pc/platform/gw_script_ui_room.inc "$ADAPTER" 2>/dev/null || true)
if [ -n "$hits" ]; then
    echo "$hits"
    bad "an Atlas online file mentions the input mask"
fi

# 8. The room door's out-parameters are the game's locals (guest memory, big-endian): a plain store through one is a bug (the
#    settings poll was dead once for it). Only gs_ui_put_be32 may write them.
DOOR="$G/pc/platform/gw_script_ui_room.inc"
if [ -f "$DOOR" ]; then
    hits=$(grep -n -E '^[[:space:]]*\*[A-Za-z_]+[[:space:]]*=[^=]' "$DOOR" || true)
    if [ -n "$hits" ]; then
        echo "$hits"
        bad "the room door stores through an out-parameter directly (use gs_ui_put_be32)"
    fi
fi


# 9. Every Ui_Room* call site is in the function that is expected to make it. The adapter's calls are an allow-list of (function, shim) pairs;
#    the legacy files call none but Ui_RoomFreeze, from fl_frame (everything else goes through the adapter's fa_room_* functions).
sites() { awk '/^static [^;]*\(/ { fn = $0; sub(/\(.*/, "", fn); n = split(fn, a, " "); fn = a[n]; gsub(/\*/, "", fn) }
               /^extern/ { next }
               { line = $0; while (match(line, /Ui_Room[A-Za-z]+\(/)) { print fn ":" substr(line, RSTART, RLENGTH - 1); line = substr(line, RSTART + RLENGTH) } }' "$1"; }
if [ -f "$ADAPTER" ]; then
    OK_ADAPTER=" fa_room_on:Ui_RoomOpen fa_room_end:Ui_RoomEnd fa_room_begin:Ui_RoomBegin fa_room_grid:Ui_RoomGridFor fa_room_grid:Ui_RoomGridCell fa_room_players:Ui_RoomPlayerName fa_room_players:Ui_RoomPlayer fa_room_common:Ui_RoomSetStr fa_room_common:Ui_RoomSetInt fa_room_submit:Ui_RoomSetStr fa_room_submit:Ui_RoomSetInt fa_room_submit:Ui_RoomStageCount fa_room_submit:Ui_RoomStage fa_room_submit:Ui_RoomGridFor fa_room_submit:Ui_RoomFrame fa_room_leaving:Ui_RoomFreeze fa_room_leaving:Ui_RoomSetInt fa_room_leaving:Ui_RoomFrame fa_room_bits:Ui_RoomPollName "
    for site in $(sites "$ADAPTER" | sort -u); do
        case "$OK_ADAPTER" in *" $site "*) ;; *) bad "$site: a Ui_Room call in an unexpected function of the adapter";; esac
    done
    for f in "$LEGACY" "$G/src/melee/gm/gmfrontend.c"; do
        for site in $(sites "$f" | sort -u); do
            [ "$site" = "fl_frame:Ui_RoomFreeze" ] || bad "$site: a Ui_Room call outside the adapter ($(basename "$f"))"
        done
    done
    # 10. A click on a stage that is not open cannot reach Confirm: the one place the room sets Confirm for a stage is the stage_click branch, and it
    #     tests fl_stage_open and fl_my_stage_turn before it does. No other line adds Confirm but the accept row of the table.
    blk=$(awk '/strcmp\(n, "stage_click"\) == 0/ {f=1} f {print} f && /MenuInput_Confirm/ {exit}' "$ADAPTER")
    echo "$blk" | grep -q 'fl_stage_open(arg)' || bad "the stage_click branch does not test fl_stage_open before it sets Confirm"
    echo "$blk" | grep -q 'fl_my_stage_turn()' || bad "the stage_click branch does not test fl_my_stage_turn before it sets Confirm"
    n=$(grep -c 'bits |= MenuInput_Confirm' "$ADAPTER")
    [ "$n" = 2 ] || bad "Confirm is set in $n places of the adapter (the accept row and the stage_click branch are the only two)"
fi
# 11. Mods are never toggled during a session: the legacy Settings > MODS toggle tests the online state before it calls Mods_SetEnabled (the Atlas
#     MODS screen has the same rule in gw_ui_mods.c, tested by atlas-mods and atlas-mods-door).
blk=$(awk '/^static void fsm_toggle/ {f=1} f {print} f && /^}/ {exit}' "$G/src/melee/gm/gmfrontend_settings.inc")
echo "$blk" | grep -q 'fsm_online()' || bad "fsm_toggle does not test fsm_online() (mods could be toggled during a session)"
echo "$blk" | awk '/fsm_online\(\)/ {a=NR} /Mods_SetEnabled/ {b=NR} END {exit !(a && b && a < b)}' || bad "fsm_toggle calls Mods_SetEnabled before it tests fsm_online()"
[ "$fail" = 0 ] && echo "check_atlas_online: ok"
exit "$fail"
