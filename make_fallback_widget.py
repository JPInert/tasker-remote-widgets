#!/usr/bin/env python3
"""FALLBACK only: a single car widget with its layout INLINED in the import (no %klayout).

    KW_TOKEN=... ./make_fallback_widget.py      # writes build/Car.prf.xml (0600: holds the token)

Use it if the remote-controlled shell (make_kw.py) renders blank on your phone, i.e. if your
Tasker's Widget v2 does not accept its whole layout / name from a variable. This shape rendered
on the target phone before the remote shell existed. Profile "Car hourly" -> task "Car Widget":
  1. HTTP Request GET car-<token>.txt  ("54 Disconnected 1791119700")
  2. JavaScriptlet -> %cver (read_at-now, cache-buster) %cago %cagecol
  3. Widget v2 "car": car-<token>.png?v=%cver + an age line; tap = refresh
The cost: every later change to the look means re-importing this file on the phone.
Actions are cloned from templates/actions.xml, the Time context from make_kw.TIME_CTX.
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_kw  # noqa: E402  (token, donors, clone helpers)

OUT = HERE / "build/Car.prf.xml"
TASK, WIDGET = "Car Widget", "car"

JS = r"""
var raw = (local('http_data') || '').trim().split(/\s+/);
var at = parseInt(raw[2], 10);
var age = isNaN(at) ? -1 : Math.floor(Date.now() / 1000) - at;
function ago(s) {
  if (s < 0) return 'no reading';
  if (s < 3600) return Math.max(1, Math.round(s / 60)) + 'm ago';
  if (s < 172800) return Math.round(s / 3600) + 'h ago';
  return Math.round(s / 86400) + 'd ago';
}
setLocal('cver', (isNaN(at) ? '0' : String(at)) + '-' + Math.floor(Date.now() / 1000));
setLocal('cago', ago(age));
setLocal('cagecol', (age < 0 || age > 86400) ? '#FF5A5F' : '#B8BDC8');
""".strip()


def layout(png_url):
    return {
        "type": "Box", "fillMaxSize": True, "backgroundColor": "#00000000", "task": TASK,
        "contentAlignment": "Center", "useMaterialYouColors": False,
        "children": [
            {"type": "Image", "url": png_url + "?v=%cver", "contentScale": "Fit", "size": "fill"},
            {"type": "Box", "fillMaxSize": True, "contentAlignment": "BottomCenter",
             "backgroundColor": "#00000000",
             "children": [{"type": "Text", "text": "%cago", "textSize": 10, "color": "%cagecol",
                           "textAlign": "Center"}]},
        ],
    }


def build():
    tacts = make_kw.actions(make_kw.DONORS)
    base = make_kw.PUB + "car-" + make_kw.token()
    http = make_kw.setstr(make_kw.sr(make_kw.first(tacts, 339), 0), "arg2", base + ".txt")
    js = make_kw.setstr(make_kw.sr(make_kw.first(tacts, 129), 1), "arg0", JS)
    w = make_kw.setstr(make_kw.sr(make_kw.first(tacts, 461), 2), "arg1", WIDGET)
    w = make_kw.setstr(w, "arg13", json.dumps(layout(base + ".png"), indent=1))
    xml = (make_kw.header() +
           '<Profile sr="prof1" ve="2"><id>1</id><nme>Car hourly</nme>%s<mid0>1</mid0></Profile>\n'
           '<Task sr="task1"><id>1</id><nme>%s</nme><pri>100</pri>%s%s%s</Task>\n'
           '</TaskerData>\n') % (make_kw.TIME_CTX, TASK, http, js, w)
    return make_kw.write(OUT.name, xml)


if __name__ == "__main__":
    import xml.etree.ElementTree as ET
    p = build()
    codes = [a.findtext("code") for a in ET.fromstring(p.read_text()).iter("Action")]
    assert codes == ["339", "129", "461"], codes
    print(f"wrote {p.relative_to(HERE)} (0600): profile 'Car hourly' -> '{TASK}' {codes}  [FALLBACK]")
