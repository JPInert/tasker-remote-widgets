#!/usr/bin/env python3
"""Publish the remote widget config: widgets/*.js -> kw-<token>.json on your static HTTPS host.

    ./kw_publish.py            # build, self-test every slot in node, upload, read back
    ./kw_publish.py --dry      # build + self-test only (no network)

The phone's Tasker task "KW Run" (make_kw.py) fetches this file on every run, so this IS the
deploy. Slots: car, k1, k2, k3 (make_kw.SLOTS); a slot without widgets/<slot>.js gets
widgets/empty.js. The token never reaches stdout.

Upload is `ssh $KW_PUB_HOST "cat > $KW_PUB_DIR/..."` (write to a temp name, then rename), so any
host that serves a folder over HTTPS works. See kw.env.example.
"""
import json, os, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_kw  # noqa: E402

FETCH = {"car": "car-{t}.txt"}            # slot -> data file on the host (default: the config itself)
SAMPLE = {"car": "54 Disconnected 1791119700"}   # what publish.sh writes: level state read_at


def build():
    t = make_kw.token()
    base = make_kw.PUB + "car-" + t
    cfg_url = make_kw.PUB + "kw-%s.json" % t
    js = lambda name: (HERE / "widgets" / f"{name}.js").read_text().replace("__BASE__", base)
    slots = {}
    for s in make_kw.SLOTS:
        if (HERE / "widgets" / f"{s}.js").exists():
            slots[s] = {"fetch": make_kw.PUB + FETCH[s].format(t=t) if s in FETCH else cfg_url, "js": js(s)}
    return {"slots": slots, "empty": {"fetch": cfg_url, "js": js("empty")}}, t


def selftest(cfg):
    """Run every slot's JS the way KW Run will, in node, on a sample datum; the layout must be JSON."""
    for s in make_kw.SLOTS:
        slot = cfg["slots"].get(s, cfg["empty"])
        prog = ("const f=new Function('data','slot','now',%s);"
                "const o=f(%s,%s,%d);if(!o||!o.type)throw new Error('no layout');"
                "const t=JSON.stringify(o);if(t.includes('%%'))throw new Error('literal %% in layout');"
                "console.log(t.length)") % (json.dumps(slot["js"]), json.dumps(SAMPLE.get(s, "")), json.dumps(s), 1791120000)
        r = subprocess.run(["node", "-e", prog], capture_output=True, text=True)
        if s not in cfg["slots"]:
            if r.returncode and "KW_FREE_SLOT" in r.stderr:
                print(f"  slot {s:4s} ok (free: stops before Widget v2, no pin prompt)")
                continue
            sys.exit(f"slot {s}: a free slot must throw KW_FREE_SLOT, got rc={r.returncode}")
        if r.returncode:
            # only the "SomeError: message" line: node's other stderr lines echo the source, which
            # holds the private URL
            err = [l for l in r.stderr.splitlines() if re.match(r"^[A-Za-z]*Error: ", l)] or ["(no message)"]
            sys.exit(f"slot {s}: JS failed: {err[0].strip()}")
        print(f"  slot {s:4s} ok (own, layout {r.stdout.strip()} B)")


if __name__ == "__main__":
    cfg, t = build()
    selftest(cfg)
    if "--dry" in sys.argv:
        sys.exit(0)
    host, pubdir = os.environ.get("KW_PUB_HOST"), os.environ.get("KW_PUB_DIR")
    if not host or not pubdir:
        sys.exit("KW_PUB_HOST and KW_PUB_DIR must be set to upload (see kw.env.example)")
    body = json.dumps(cfg)
    try:
        subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host,
                        f"cat > {pubdir}/.kw.tmp && mv {pubdir}/.kw.tmp {pubdir}/kw-{t}.json"],
                       input=body, text=True, check=True, capture_output=True, timeout=60)
        got = subprocess.run(["curl", "-fsS", "-m", "10", make_kw.PUB + f"kw-{t}.json"],
                             capture_output=True, text=True, timeout=20).stdout
    except subprocess.SubprocessError:
        # the exception text would carry argv, and argv holds the token
        raise SystemExit("kw_publish: upload/readback failed (details withheld: argv holds the token)") from None
    if got != body:
        sys.exit("kw_publish: read-back does NOT match what was uploaded")
    print(f"published kw-<tok>.json ({len(body)} B), read back identical")
