"""Refresh the shared pickup controller embedded in its single-feature demo."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'melee/pc/scripts/lib/pickup_juice.lua'
TARGET=ROOT/'melee/pc/scripts/examples/demos/pickup-juice/scripts/main.lua'
def bundle():
 text=TARGET.read_text(encoding='utf-8')
 start=text.index('local J=assert(load(')+len('local J=assert(load(')
 end=text.index(',"@lib/pickup_juice.lua","t"))()',start)
 return text[:start]+json.dumps(SOURCE.read_text(encoding='utf-8'),ensure_ascii=False)+text[end:]
if __name__=='__main__': TARGET.write_text(bundle(),encoding='utf-8')
