# Discord administration

Permanent home for GD Workshop server tooling. Python standard library; GitHub integration requires gh.

Run: python tools/discord/discord_setup.py inspect
Tests: python -m unittest discover -s tools/discord -p test_*.py

discord_setup.py manages server layout, roles, posts, artwork and invites.
blueprint.py holds the intended layout and copy. pin_art.py supports branded pins.
github_discord.py is the original GitHub README link publisher.

Adjacent .env credentials and JSON server state are private and Git-ignored.
Restore them separately on other PCs. Original temporary copies remain as backup.
Only run external write actions for an explicitly authorized update.

Project refresh copy: refresh_project.py (dated October 8, 2026).
Prepare: python tools/discord/refresh_project.py
Render: python menu/pipeline/discord_pins.py --source tools/discord/refresh-source.json --output menu/out_discord_refresh
Publish authorized changes: python tools/discord/publish_refresh.py
Publisher verifies every edited pin, image count and navigation link after uploading.
Future project updates must recheck GitHub release assets and current branch acceptance notes.
Legacy blueprint text predates these image panels; maintain current copy through refresh_project.py.

releases_channel.py maintains the read-only patch-notes-and-releases announcement channel,
its pinned index and v0.1.7 summary, and navigation buttons on welcome/announcements/downloads.
Run it only for an authorized external update.
