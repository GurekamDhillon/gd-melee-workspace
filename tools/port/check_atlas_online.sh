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
        grep -q "$name" "$LEGACY" || grep -q "$name" "$G/src/melee/gm/gmfrontend.c" || bad "$name is new: the adapter must not add a netplay call"
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

[ "$fail" = 0 ] && echo "check_atlas_online: ok"
exit "$fail"
