import sys
def patch(path, edits):
    raw = open(path,'rb').read().decode('latin-1')
    crlf = '\r\n' in raw
    s = raw.replace('\r\n','\n')
    for old,new in edits:
        assert s.count(old)==1, (path, s.count(old), old[:80])
        s = s.replace(old,new)
    out = s.replace('\n','\r\n') if crlf else s
    open(path,'wb').write(out.encode('latin-1'))
