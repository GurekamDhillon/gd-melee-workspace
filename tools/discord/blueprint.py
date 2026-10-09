"""GD-approved Melee-only server layout and original welcome copy."""

REPOSITORY = "https://github.com/GurekamDhillon/gd-melee-workspace"
RELEASES = REPOSITORY + "/releases/latest"
DESCRIPTION = "GD's Melee: native PC play, rollback netplay, mods, Lua scripting, and the LAB. Play, build, and help shape the port."

ROLE_SPECS = [
    ("Moderator", 0xE5483B, True),
    ("Contributor", 0xF0B429, True),
    ("Playtester", 0x9DA2F8, False),
    ("Modder", 0x45B78A, False),
    ("Player", 0x2F7CF0, False),
]

CATEGORIES = [
    ("start", "START HERE", None, "readonly"),
    ("community", "COMMUNITY", "1552483230446264320", "public"),
    ("melee", "MELEE WORKSHOP", None, "public"),
    ("voice", "VOICE", "1552483230446264321", "public"),
    ("staff", "STAFF", None, "staff"),
]

# key, display name, type, category, topic, slowmode seconds, existing channel
CHANNELS = [
    ("welcome", "welcome", 0, "start", "Start here: GD's Melee downloads, matches, support, and community links.", 0, None),
    ("rules", "rules", 0, "start", "Keep the Workshop welcoming. Read these rules before posting.", 0, None),
    ("announcements", "announcements", 5, "start", "Official GD's Melee releases and important project updates.", 0, None),
    ("releases", "patch-notes-and-releases", 5, "start", "Published builds, patch notes and upgrade requirements. Development progress is in announcements.", 0, None),
    ("downloads", "downloads", 0, "start", "Get GD's Melee from the official GitHub releases. Game data is not included.", 0, None),
    ("general", "general", 0, "community", "Melee, the port, and the people building and playing it. Make yourself at home.", 3, "1552483230446264322"),
    ("introductions", "introductions", 0, "community", "Say hello: your main, broad region, and what brings you to GD's Melee.", 5, None),
    ("showcase", "clips-and-creations", 0, "community", "Clips, combos, original art, mods, and scripts. Credit the creators.", 5, None),
    ("suggestions", "suggestions", 0, "community", "One idea per message. Describe the problem it solves; use a thread for discussion.", 10, None),
    ("matchmaking", "matchmaking", 0, "melee", "Find friendlies: broad region, build, disc/mod pack, and room code. Both players need matching content.", 10, None),
    ("help", "help-and-setup", 15, "melee", "One question per post. Include build version, Windows/GPU/controller, what you tried, and the exact error. Use a tag; mark solved when fixed. Do not upload game discs or private credentials.", 15, None),
    ("bugs", "bug-reports", 15, "melee", "Search first; one issue per post. Include version, disc/mod pack, reproduction steps, expected/actual behavior, and a sanitized log. Never attach disc data or credentials.", 30, None),
    ("training", "training-and-lab", 0, "melee", "Practice, dummy setups, DI/tech experiments, and SOLO > LAB workflows.", 3, None),
    ("modding", "modding-and-scripting", 0, "melee", "m-ex mods, Lua gd.* / gd.kit, and original projects. Share source and patches with credits.", 3, None),
    ("hangout", "The Workshop", 2, "voice", None, 0, "1552483230446264323"),
    ("friendlies1", "Friendlies 1", 2, "voice", None, 0, None),
    ("friendlies2", "Friendlies 2", 2, "voice", None, 0, None),
    ("staff_chat", "staff-chat", 0, "staff", "Private moderation coordination. Keep reports factual and share only what is needed.", 0, None),
    ("mod_alerts", "mod-alerts", 0, "staff", "Discord AutoMod alerts. Review context before taking action.", 0, None),
    ("discord_updates", "discord-updates", 0, "staff", "Private Discord Community and safety notices for the server team.", 0, None),
]

FORUM_TAGS = {
    "help": ["Installation", "Controller", "Graphics / audio", "Netplay", "Mods / LAB", "Solved"],
    "bugs": ["Crash", "Gameplay", "Graphics / audio", "Netplay", "Mods / LAB", "Needs info", "Confirmed", "Fixed"],
}

POSTS = {
    "welcome": ("WELCOME TO GD'S WORKSHOP", "The home of **GD's Melee**: a native PC port with rollback netplay, mod support, Lua scripting, and the LAB.\n\n**Start playing**\nRead {rules}, then grab the build in {downloads}.\n\n**Find your people**\nIntroduce yourself in {introductions}, find a set in {matchmaking}, and share your best work in {showcase}.\n\n**Get help or get involved**\nSetup questions → {help}\nReproducible problems → {bugs}\nPractice and experiments → {training}\nMods and scripts → {modding}\n\nUse **Channels & Roles** to choose Player, Modder, or Playtester. You can pick more than one.\n\n**New here?** Your main, a broad region, and what you want to try are a good first introduction."),
    "rules": ("THE WORKSHOP RULES", "**1 · Treat people well.** No harassment, hate speech, threats, doxxing, or targeted dogpiling. Respect boundaries in chat, voice, and DMs.\n\n**2 · Keep it safe to open.** No sexually explicit content, graphic violence, scams, malware, or deceptive downloads.\n\n**3 · Share your work responsibly.** No game ISOs, ROMs, extracted game assets, or links to obtain them. Share original work, source, and patches with appropriate credits and permissions.\n\n**4 · Keep channels useful.** No spam, unsolicited advertising, mass mentions, or repeated bumps. Put help requests in {help} and reproducible bugs in {bugs}.\n\n**5 · Play fair.** Agree on the build, rules, and mods before a set. No cheating, griefing, or deliberate disruption.\n\n**6 · Protect private information.** Remove personal paths, addresses, tokens, and other secrets from logs before sharing. Never ask someone for their password or token.\n\n**Need a moderator?** Use Discord's message reporting tools for platform violations, or contact the owner / a Moderator with the message link. Avoid public callouts. Moderators may remove content, time out, or remove members when needed."),
    "announcements": ("GD'S MELEE · PROJECT UPDATES", "This channel is for official builds, release notes, and important Workshop updates.\n\n**Latest build and setup:** {downloads}\n**Questions:** {help}\n**Bug reports:** {bugs}\n\nGD's Melee is a public test project. Include your build version when discussing behavior; fixes and compatibility can change between builds.\n\nServer notifications default to mentions only. Follow this channel if you want release updates."),
    "downloads": ("GET GD'S MELEE", f"**Official downloads**\n[Latest Windows release]({RELEASES}) · [Source and README]({REPOSITORY})\n\n**First launch**\n1. Download the Windows ZIP from the release's **Assets** section and extract it.\n2. Run **GD Melee.exe**. Choose **Add disc...** and select your own Melee NTSC 1.02 disc image. Compatible mod discs can be selected too.\n3. Press **PLAY**. The release includes the port, not game data.\n\n**Online play**\nOpen **VERSUS → ONLINE**. Host a room and share its code, join a friend's room, or use **Random Opponent**. Match the build and disc/mod content with your opponent.\n\n**Need a hand?** Open a post in {{help}}. Include your build, Windows version, GPU, controller, and the exact error. Never upload a disc image."),
    "introductions": ("PULL UP A CHAIR", "Tell us a little about your Melee life:\n• Your main(s)\n• Your broad region / time zone, if you want to share it\n• Whether you're here to play, mod, test, or learn\n\nChoose your interests in **Channels & Roles**, then find a set in {matchmaking}. New players and experienced players are both welcome."),
    "showcase": ("MADE IN THE WORKSHOP", "Post a clip, combo, original creation, mod, or script. A little context helps: what build/content you used and what you are showing.\n\nCredit collaborators and link the source or project page when you can. Share your original work and patches; game discs and extracted game assets do not belong here."),
    "suggestions": ("A GOOD IDEA STARTS WITH A PROBLEM", "Use this format for suggestions:\n**Problem:** What gets in your way?\n**Idea:** What would make it better?\n**Example:** When would you use it?\n\nKeep one idea per message and discuss it in a thread. Reactions show interest; they do not promise an implementation date. Bugs go in {bugs}."),
    "matchmaking": ("FIND YOUR NEXT SET", "Post a short lobby listing:\n**Region / connection:** broad region; wired or Wi-Fi\n**Build + content:** version and vanilla / mod pack\n**Room code:** your in-game room\n**Looking for:** friendlies, practice, or a longer set\n\nBoth players should use matching builds and content. Agree on any mods or rules before starting. Use **Friendlies 1** or **Friendlies 2** for voice and edit your post when the room closes.\n\nConnection trouble? Open a **Netplay** post in {help}."),
    "training": ("PUT THE LAB TO WORK", "Share practice routines, dummy setups, matchup questions, and reproducible experiments.\n\nFor LAB discussions, include your build, fighters, stage, starting situation, and the setting or drill you used. Label measured results and theories clearly.\n\nUse **SOLO → LAB** for the port's practice tools. If something behaves incorrectly, open a reproducible report in {bugs}."),
    "modding": ("BUILD SOMETHING", f"Talk m-ex compatibility, Lua scripts, kit UI, and original additions for GD's Melee.\n\n[Scripting guide]({REPOSITORY}/blob/master/docs/scripting.md) · [Workspace source]({REPOSITORY})\n\nWhen asking for help, include the build, mod pack, relevant code, error, and the smallest steps that reproduce it. Use code blocks and thread longer investigations.\n\nShare source and patches, credit collaborators, and check permissions before redistributing someone else's work. Game discs and extracted assets stay off the server."),
    "staff_chat": ("STAFF DESK", "This category is visible to the owner, the setup bot, and Moderator roles only. Contributor, Player, Modder, and Playtester do not grant staff access.\n\n**Roles:** assign Moderator only to trusted staff. Contributor is recognition; the three interest roles are self-selectable in Channels & Roles.\n\n**Moderation:** AutoMod reports to {mod_alerts}; Discord notices go to {discord_updates}. Review context, keep a message link, and explain actions briefly.\n\nThe setup bot uses Discord's API and may appear offline. Native AutoMod and onboarding continue without a running bot service. No reaction-role or ticket bot is required."),
}

FORUM_GUIDES = {
    "help": ("START HERE · how to ask for help", "Use one post per question and pick the closest tag.\n\n**Build version:**\n**Windows / GPU / controller:**\n**Disc or mod pack:**\n**What I was trying to do:**\n**Exact error / behavior:**\n**What I already tried:**\n\nAttach a relevant screenshot or a sanitized log if it helps. Remove private information first; do not attach game discs or credentials.\n\nOnce fixed, add **Solved** and reply with the solution so the next player can find it.", "Installation"),
    "bugs": ("START HERE · bug report template", "Search existing reports before creating a new post. Use a descriptive title and one issue per report.\n\n**Build version:**\n**Disc / mod pack:**\n**Windows / GPU / controller:**\n**Steps to reproduce:**\n1.\n2.\n3.\n**Expected result:**\n**Actual result:**\n**How often it happens:**\n**Log / crash report:**\n\nFor a crash, attach the relevant report from the crashlogs folder or melee-pc.log after checking it for private information. Do not attach disc images or extracted game data.\n\nThe staff tags **Needs info**, **Confirmed**, and **Fixed** track triage. A report is evidence to investigate, not a promise that a fix is ready.", "Needs info"),
}
