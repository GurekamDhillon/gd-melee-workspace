import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WS = 'https://github.com/GurekamDhillon/gd-melee-workspace'
DEV = WS + '/tree/master'
DOC = WS + '/blob/master/docs/'
GAME = 'https://github.com/GurekamDhillon/melee/tree/pc-port'
UPDATES = {
'welcome': ('WELCOME TO THE WORKSHOP', "The home of **GD's Melee**: native PC Melee, rollback netplay, mod support, Lua scripting and the LAB.\n\n**Play the public build**\nv0.2.2 is the latest published release, for Windows and Linux. Windows and Linux players can play each other online. Start with #rules and #downloads.\n\n**Explore development**\nLinux performance work, the map editor and a roguelite campaign are active development work. They are ahead of the public release; follow #announcements for status.\n\nFind sets in #matchmaking, ask in #help-and-setup, report bugs in #bug-reports, and share work in #clips-and-creations. Choose your interests in Channels & Roles."),
'announcements': ('PROJECT STATUS | OCTOBER 8, 2026', "**Public release: v0.2.2 for Windows and Linux**\nDownload it in #downloads. Windows and Linux play each other online (netplay protocol 5); every player needs 0.2.2 (0.2.1 and earlier cannot match). Since 0.1.7 the release adds fullscreen (F11 or Alt+Enter), an in-game mod browser for SSBM Nucleus, everything unlocked by default, Envoy (the roguelike mode), Turbo and steadier netplay, a native Qt launcher with a Diagnostics tab, opt-in crash report upload, and afterimages and tracers for technique. New branch work is not included just because it is pushed.\n\n**Next**\nLinux performance: on some Linux laptops the game runs below 60 fps, which also slows an online match with a Windows player. Broader Linux gameplay, audio and controller acceptance continues.\n\n**Roguelite campaign**\nDevelopment now includes branching room generation, save/resume, encounters, rewards, inventory/equipment, gene actions and loadout/HUD integration. Production room recipes remain uncertified; generated-route admission and watched gameplay checks are still pending.\n\n**Editor + scripting**\nThe map editor supports gizmos, multi-select, undo/redo and spawn editing. Lua stage/model tools and fighter effects continue to grow.\n\nSee the development links below. Report the version or branch/commit when testing."),
'downloads': ("GET GD'S MELEE", "**Latest public release: v0.2.2 (Windows + Linux)**\nDownload from the official release Assets. Add your own Melee NTSC 1.02 disc image. Game data is not included.\n\n**Windows:** GDMelee-0.2.2-win64.zip. Extract it, run GD Melee.exe, pick your disc image and press PLAY.\n**Linux:** GDMelee-0.2.2-linux-x86_64.tar.xz. Extract it to a new folder and run ./GD-Melee from the melee-linux-i686 folder. If it stops with \"No supported adapters\", try MELEE_BACKEND=opengles ./GD-Melee.\n\n**Online**\nUse VERSUS > ONLINE. Windows and Linux 0.2.2 play each other (netplay protocol 5). Every player needs 0.2.2; 0.2.1 and earlier cannot match it. Match your opponent's disc/mod content.\n\n**Known issues**\nSome Linux laptops run below 60 fps, which also slows online matches with Windows players.\n\nFor help, include version or commit, operating system, GPU, controller and exact error in #help-and-setup."),
'modding': ('BUILD SOMETHING', "**Lua, kit UI and map editing**\nUse gd.* / gd.kit for gameplay scripts and UI, stage collision/models, camera tools and the LAB. The map editor has gizmos, multi-select, undo/redo, saved layouts and spawn editing.\n\n**Fighters and effects**\nm-ex compatibility and Ultimate fighter conversion/effect tooling continue in development. Installed content and visual fidelity need their own verification.\n\n**Campaign development**\nThe roguelite modules cover routes, persistence, encounters, rewards, inventory, gene actions and presentation. Room certification and gameplay acceptance remain pending; do not treat a planned feature or passing module test as a finished campaign.\n\nThe current development links are below. Include your branch/commit and a small reproduction when sharing code or reporting a problem. Share original work, source and patches with credits; no disc-derived assets."),
'help': ('START HERE | HOW TO ASK FOR HELP', "Use one post per question and choose the closest tag.\n\n**Build version or branch + commit:**\n**Windows / Linux distribution:**\n**GPU / graphics driver / controller:**\n**Disc or mod pack:**\n**Launcher: release or development Qt:**\n**What I was trying to do:**\n**Exact error / behavior:**\n**What I already tried:**\n\nv0.2.2 (Windows and Linux) is the public release. Campaign branch testing is development work; include the commit and whether you built from source.\n\nAttach relevant screenshots and sanitized logs. Never attach game discs or credentials. When fixed, add Solved and explain the solution."),
'bugs': ('START HERE | BUG REPORT TEMPLATE', "Search existing reports first. One issue per post.\n\n**Build version or branch + commit:**\n**Windows / Linux distribution:**\n**GPU / driver / controller:**\n**Disc / mods / launcher:**\n**Steps to reproduce:**\n1.\n2.\n3.\n\n**Expected result:**\n**Actual result and frequency:**\n**Log / crash report:**\n\nFor campaign bugs, include seed, room, fighter, save/resume state and whether you used a certification fixture or normal play.\n\nSanitize personal paths and secrets. No disc images or extracted game data. Needs info, Confirmed and Fixed track triage; development test results do not establish release compatibility."),
'showcase': ('MADE IN THE WORKSHOP', "Share clips, combos, original art, mods, scripts, map-editor layouts and campaign experiments.\n\nInclude your build or branch/commit, content and what the clip demonstrates. Label development footage, certification fixtures and prototypes clearly. A development clip does not mean the feature is in the public release.\n\nCredit collaborators and link source when possible. Share original work and patches; game discs and extracted game assets stay off the server.")}

def prepare():
    source = json.loads((HERE / 'pin-art-source.json').read_text(encoding='utf-8'))
    posts = []
    for p in source['posts']:
        if p['key'] not in UPDATES: continue
        title, text = UPDATES[p['key']]
        p.update(title=title, text=text)
        p['buttons'] = [b for b in p['buttons'] if b['label'] not in {'Source and README', 'Scripting guide', 'Workspace source', 'Latest Windows release'}]
        extras = {
          'welcome': [('Development source', DEV)],
          'announcements': [('Linux status', DOC+'LINUX_PORT_STATUS.md'), ('Campaign acceptance', DOC+'ROGUELITE-ACCEPTANCE.md'), ('Game development', GAME)],
          'downloads': [('Release v0.2.2', WS+'/releases/tag/v0.2.2'), ('Development source', DEV)],
          'modding': [('Scripting guide', DOC+'scripting.md'), ('Workspace development', DEV), ('Game development', GAME)],
        }.get(p['key'], [])
        p['buttons'] += [dict(label=l,url=u) for l,u in extras]
        posts.append(p)
    assert len(posts) == len(UPDATES)
    (HERE / 'refresh-source.json').write_text(json.dumps(dict(posts=posts), indent=2), encoding='utf-8')
    print('Prepared',len(posts),'updated posts')

if __name__ == '__main__':
    prepare()
