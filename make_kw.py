#!/usr/bin/env python3
"""Build the three ONE-TIME Tasker imports for remote-controlled widgets.

    ./make_kw.py          # writes build/KW_Run.tsk.xml, build/KW_hourly.prf.xml, build/KW_kick.prf.xml (0600)

After these three imports the phone never needs another one for widget work: everything a widget
does and looks like lives in ONE remote file, kw-<token>.json on your static HTTPS host, written by
kw_publish.py from widgets/*.js. Change a widget = edit its .js, run kw_publish.py, then wait for
the hourly run, tap the widget, or run kw-kick.sh. The phone's other Tasker tasks are never touched
(imports only ADD).

Task "KW Run" (%par1 = slot name: car, k1, k2, k3):
  a0 HTTP GET  kw-<tok>.json?v=%TIMES                      (no caching, ever)
  a1 JS        pick slot %par1 -> %kfetch (its data URL), %kjs (its code)
  a2 HTTP GET  %kfetch
  a3 JS        run %kjs(data, slot, now) -> layout object -> %klayout (JSON text)
  a4 Widget v2 name %par1, custom layout %klayout
Profile "KW hourly" (Time, every 1 h) and profile "KW kick" (Intent Received KW_REFRESH, sent by
kw-kick.sh) both run a task that does Perform Task "KW Run" x4, one per slot.
Widget taps run "KW All" too (set in each layout's "task").

Tasker actions carry positional arguments whose meaning is undocumented, and a hand-written one
imports as a silent no-op. So every action here is CLONED from templates/actions.xml (lifted from a
working Tasker export, values blanked) and only the one field that matters is substituted.

Config comes from the environment (see kw.env.example):
  KW_TOKEN    the private token in every file name on the host (treat it as a password)
  KW_PUB_URL  the public URL of the folder those files live in, ending in /
"""
import html, os, pathlib, re, sys
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
DONORS = HERE / "templates/actions.xml"
BUILD = HERE / "build"
SLOTS = ["car", "k1", "k2", "k3"]
KICK_ACTION = "kw.KW_REFRESH"
RUN, ALL = "KW Run", "KW All"
PUB = os.environ.get("KW_PUB_URL", "https://example.com/pub/")

# Profile contexts, lifted from a working Tasker export. rep=1 means HOURS (repval=1: every hour,
# all day). The minutes unit is not decoded, so do not guess rep=0 for minutes.
TIME_CTX = ('<Time sr="con0"><repval>1</repval><fh>-1</fh><fm>-1</fm><th>-1</th><tm>-1</tm>'
            '<rep>1</rep></Time>')
INTENT_CTX = ('<Event sr="con0" ve="2"><Str sr="arg0" ve="3">%s</Str><Int sr="arg1" val="0"/>'
              '<Int sr="arg2" val="0"/><Str sr="arg3" ve="3"/><Str sr="arg4" ve="3"/>'
              '<code>599</code></Event>') % KICK_ACTION

PICK_JS = r"""
var c = JSON.parse(local('http_data'));
var s = c.slots[local('par1')] || c.empty;
setLocal('kfetch', s.fetch || c.empty.fetch);
setLocal('kjs', s.js);
""".strip()

RUN_JS = r"""
var f = new Function('data', 'slot', 'now', local('kjs'));
setLocal('klayout', JSON.stringify(f(local('http_data') || '', local('par1'), Math.floor(Date.now() / 1000))));
""".strip()


def token():
    t = os.environ.get("KW_TOKEN", "").strip()
    if not t:
        sys.exit("KW_TOKEN is not set (see kw.env.example)")
    return t


def actions(path):
    return re.findall(r'<Action sr="act\d+"\s*ve="\d+">.*?</Action>', path.read_text(), re.S)


def first(acts, code):
    for a in acts:
        if "<code>%d</code>" % code in a:
            return a
    sys.exit(f"no code {code} action in template")


def sr(a, n):
    return re.sub(r'<Action sr="act\d+"', '<Action sr="act%d"' % n, a, count=1)


def setstr(a, arg, val):
    pat = r'<Str sr="%s" ve="3"\s*(/>|>.*?</Str>)' % arg
    new, n = re.subn(pat, lambda m: '<Str sr="%s" ve="3">%s</Str>' % (arg, html.escape(val, quote=False)),
                     a, count=1, flags=re.S)
    if n != 1:
        sys.exit(f"no Str {arg}")
    return new


def perform(n, task, par1):
    a = sr(first(actions(DONORS), 130).replace(">KW Run<", ">%s<" % html.escape(task), 1), n)
    a = setstr(a, "arg2", par1)
    if "<code>130</code>" not in a or ">%s<" % task not in a:
        sys.exit("Perform Task clone did not take")
    return a


def header():
    return DONORS.read_text().splitlines()[0].strip() + "\n"


def write(name, xml):
    ET.fromstring(xml)                                # well-formed or raise
    BUILD.mkdir(exist_ok=True)
    p = BUILD / name
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)   # holds the token
    with os.fdopen(fd, "w") as f:
        f.write(xml)
    os.chmod(p, 0o600)
    return p


def build():
    t = token()
    tacts = actions(DONORS)
    run = "".join([
        setstr(sr(first(tacts, 339), 0), "arg2", PUB + "kw-%s.json?v=%%TIMES" % t),
        setstr(sr(first(tacts, 129), 1), "arg0", PICK_JS),
        setstr(sr(first(tacts, 339), 2), "arg2", "%kfetch"),
        setstr(sr(first(tacts, 129), 3), "arg0", RUN_JS),
        setstr(setstr(sr(first(tacts, 461), 4), "arg1", "%par1"), "arg13", "%klayout"),
    ])
    out = [write("KW_Run.tsk.xml", header() +
                 '<Task sr="task1"><id>1</id><nme>%s</nme><pri>100</pri>%s</Task>\n</TaskerData>\n' % (RUN, run))]

    all_task = "".join(perform(i, RUN, s) for i, s in enumerate(SLOTS))
    for fname, pname, ctx, tname in (("KW_hourly.prf.xml", "KW hourly", TIME_CTX, ALL),
                                     ("KW_kick.prf.xml", "KW kick", INTENT_CTX, "KW Kick")):
        out.append(write(fname, header() +
            '<Profile sr="prof1" ve="2"><id>1</id><nme>%s</nme>%s<mid0>1</mid0></Profile>\n'
            '<Task sr="task1"><id>1</id><nme>%s</nme><pri>100</pri>%s</Task>\n</TaskerData>\n'
            % (pname, ctx, tname, all_task)))
    return out


if __name__ == "__main__":
    for p in build():
        root = ET.fromstring(p.read_text())
        codes = [a.findtext("code") for a in root.iter("Action")]
        names = [e.findtext("nme") for e in list(root) if e.tag in ("Profile", "Task")]
        print(f"wrote {p.relative_to(HERE)}: {names} {codes}")
