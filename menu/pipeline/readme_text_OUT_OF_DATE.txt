readme_text.json is out of date compared with the README art committed in docs/readme/.

The committed feature tiles (12, including lobby, roster, scripting, training, launcher and
settings) and the banner tagline were rendered from an updated copy of readme.py and its text,
which were not put back into menu/pipeline/. Running `python pipeline/readme.py` as it is now
rebuilds the older 6-tile set. Bring readme_text.json (and readme.py's icons for strike, code,
roster, launcher and the ico_* tiles) up to date before you regenerate and copy the art over.
