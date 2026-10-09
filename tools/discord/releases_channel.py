"""Create/update the authorized patch-notes channel and its release index."""
from discord_setup import Setup, GUILD_ID, ScopeError, save_json
s = Setup()
c = s.channel('releases', dict(name='patch-notes-and-releases', type=5,
    parent_id=s.state['channels']['start'], permission_overwrites=s.overwrites('readonly'),
    topic='Published GD Melee releases, patch notes and upgrade requirements. Development progress is in #announcements.', nsfw=False, rate_limit_per_user=0))
cid = c['id']
s.api.request('PATCH', '/channels/'+cid, {'position':s.channels[s.state['channels']['announcements']]['position']+1})
release='https://github.com/GurekamDhillon/gd-melee-workspace/releases/tag/v0.1.7'
r020='https://github.com/GurekamDhillon/gd-melee-workspace/releases/tag/v0.2.0'
r021='https://github.com/GurekamDhillon/gd-melee-workspace/releases/tag/v0.2.1'
r022='https://github.com/GurekamDhillon/gd-melee-workspace/releases/tag/v0.2.2'
posts={
 'release_index': {'content':"**PATCH NOTES & RELEASES**\nPublished builds and upgrade notes live here. Follow this channel for future release posts.\n\nLatest public release: **v0.2.2 for Windows and Linux** (they play each other online). Development updates belong in <#"+s.state['channels']['announcements']+"> until released.\n\nDownloads and setup: <#"+s.state['channels']['downloads']+">\n[All releases](https://github.com/GurekamDhillon/gd-melee-workspace/releases)", 'embeds':[]},
 'release_v0_2_0': {'content': '', 'embeds':[{'title':"GD's Melee v0.2.0 | Windows + Linux public test build",'url':r020,'color':0xF0B429,'description':"**Released October 8, 2026 (UTC)**\n\n**Windows and Linux play together**\nThe Windows and Linux builds play each other online. A build id checked before every match refuses builds that would drift apart.\n\n**Envoy**\nThe roguelite mode ships with original drive models, a strength index (x4.58) and clearer signals for its rules.\n\n**Look and feel**\nEarned afterimages and crit tracers, with more colour options for creators.\n\n**Launcher**\nThe new launcher can upload crash reports again: opt-in, off by default, only on a click. A bad saved shader cache no longer crashes every launch.\n\n**Online upgrade required**\nNetplay protocol 5: every player needs 0.2.x. Older builds are refused.\n\n[Full patch notes and download]("+r020+")\nBring your own NTSC-U 1.02 disc image; game data is not included."}]},
 'release_v0_2_1': {'content': '', 'embeds':[{'title':"GD's Melee v0.2.1 | Hotfix",'url':r021,'color':0xF0B429,'description':"**Released October 8, 2026 (UTC)**\n\n**Fixed**\nOpening Data > Snapshots from the main menu could freeze the game. Fixed.\n\n**Update both sides**\n0.2.1 plays 0.2.1 (Windows and Linux), not 0.2.0.\n\n**Coming next**\nA fullscreen option (F11 / Alt+Enter, and a launcher setting) and better speed on some Linux laptops.\n\n[Patch notes and download]("+r021+")"}]},
 'release_v0_2_2': {'content': '', 'embeds':[{'title':"GD's Melee v0.2.2 | Mod browser, fullscreen, Envoy online",'url':r022,'color':0xF0B429,'description':"**Released October 8, 2026 (UTC)**\n\n**New**\nAn in-game mod browser for SSBM Nucleus (https://ssbmnucleus.net, built with permission from sc00p), with an install queue that survives restarts. Everything is unlocked by default (Settings > Gameplay turns it off). Fullscreen with F11 / Alt+Enter. 255 costumes per fighter.\n\n**Online**\nEnvoy sets resume after a disconnect, ties replay instead of sudden death, and a stricter disc check refuses a different disc. The Windows-vs-Linux checksum false alarm is fixed.\n\n**Linux**\nMuch faster rollback snapshots, turbo crash fixes, and Envoy drive items and shaders now work.\n\n**Update both sides**\n0.2.2 plays 0.2.2 (Windows and Linux), not 0.2.1.\n\n[Patch notes and download]("+r022+")\nBring your own NTSC-U 1.02 disc image; game data is not included."}]},

 'release_v0_1_7': {'content': '', 'embeds':[{'title':"GD's Melee v0.1.7 | Windows public test build",'url':release,'color':0xF0B429,'description':"**Released September 28, 2026 (UTC)**\n\n**Performance**\nHigher-refresh rendering/interpolation fixes, faster logic and loading, cheaper rollback snapshots, and safer heavy-scene rendering.\n\n**Tools and gameplay**\nLAB performance overlay, scalable menu frames, offline debug flight, Classic/1P loading and boss-clear fixes, and corrected short time limits/stock counts.\n\n**Creators**\nScripted cameras, stage collision and targets, custom 3D models, map-editor example, Adventure enemies, hit/damage hooks, and Geno v5.5 effects and fighter features.\n\n**Online upgrade required**\nNetplay protocol 3: both players need v0.1.7. Protocol 1/2 clients are incompatible. Match build and disc/mod content.\n\n[Full patch notes and download]("+release+")\nBring your own NTSC-U 1.02 disc image; game data is not included."}]}
}
for key,payload in posts.items():
    payload['allowed_mentions']={'parse':[]}
    meta=s.state['messages'].get(key)
    if meta:
        old=s.api.request('GET',f"/channels/{cid}/messages/{meta['id']}")
        if old.get('author',{}).get('id')!=s.snapshot['bot_id']: raise ScopeError('Unexpected message author')
        m=s.api.request('PATCH',f"/channels/{cid}/messages/{meta['id']}",payload)
    else:
        payload.update(nonce='gd-'+key,enforce_nonce=True)
        m=s.api.request('POST',f'/channels/{cid}/messages',payload)
    s.state['messages'][key]={'channel_id':cid,'id':m['id']};s.save()
    if not m.get('pinned'):s.api.request('PUT',f"/channels/{cid}/messages/pins/{m['id']}")
    check=s.api.request('GET',f"/channels/{cid}/messages/{m['id']}")
    assert check['pinned'] and check.get('content','')==payload['content']
    if payload['embeds']: assert check['embeds'][0]['description']==payload['embeds'][0]['description']
for key in ('welcome','announcements','downloads'):
    meta=s.state['messages'][key]; path=f"/channels/{meta['channel_id']}/messages/{meta['id']}"
    m=s.api.request('GET',path)
    assert m['author']['id']==s.snapshot['bot_id']
    rows=m.get('components',[])
    url=f'https://discord.com/channels/{GUILD_ID}/{cid}'
    if not any(b.get('url')==url for row in rows for b in row.get('components',[])):
        button={'type':2,'style':5,'label':'Patch notes & releases','url':url}
        if rows and len(rows[-1]['components'])<5: rows[-1]['components'].append(button)
        else: rows.append({'type':1,'components':[button]})
        s.api.request('PATCH',path,{'components':rows,'allowed_mentions':{'parse':[]}})
    check=s.api.request('GET',path)
    assert any(b.get('url')==url for row in check['components'] for b in row['components'])
check=s.api.request('GET','/channels/'+cid)
assert check['type']==5 and check['parent_id']==s.state['channels']['start']
print('Verified channel, four pinned posts, and three navigation links:',url)
save_json('release-channel-verification.json',{'url':url,'verified':True})
