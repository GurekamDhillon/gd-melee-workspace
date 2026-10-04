"""Extract unchanged production functions for the standalone native policy fixture."""
from pathlib import Path
import sys

source=Path(sys.argv[1]).read_text(encoding='utf-8')
sections=[]
for begin,end in [('static void gs_require_gameplay(', 'static void gs_setnum('),
                  ('static void gs_hot_do(void)', '/* the loop top:')]:
    start=source.index(begin)
    sections.append(source[start:source.index(end,start)])
Path(sys.argv[2]).write_text('\n'.join(sections),encoding='utf-8')
