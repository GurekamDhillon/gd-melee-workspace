import pin_art
from discord_setup import Setup, ROOT
pin_art.OUTPUT = ROOT / 'menu/out_discord_refresh'
pin_art.publish(Setup())
