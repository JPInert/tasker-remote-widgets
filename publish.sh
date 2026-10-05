#!/usr/bin/env bash
# Publish the car's battery for the phone widget: one text line plus the rendered flower face.
#
#   car-<token>.txt   <battery_level> <charging_state> <read_at epoch s>   e.g.  54 Disconnected 1791119700
#   car-<token>.png   flower.py's face for that reading
#
# Source: a JSON file that something else on this machine keeps up to date with the car's last
# reading ($KW_CAR_JSON). It needs three keys: usable_battery_level (int), charging_state (Tesla's
# Charging / Complete / Stopped / Disconnected), and _read_at (epoch seconds of the reading).
# This script never calls the car's API itself, so it can never wake the car.
#
# Destination: a folder on $KW_PUB_HOST that a web server publishes as $KW_PUB_URL. The phone pulls
# it over plain HTTPS, no VPN. The token in the file NAME is the only access control.
#
# Run it from a systemd path unit (on every write of the JSON) plus an hourly timer, or from cron.
# A systemd user unit does not source your shell rc, so PATH and the config file are set here.
set -euo pipefail
PATH=/usr/local/bin:/usr/bin:/bin
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
[ -f "$HERE/kw.env" ] && . "$HERE/kw.env"
: "${KW_TOKEN:?}" "${KW_CAR_JSON:?}" "${KW_PUB_HOST:?}" "${KW_PUB_DIR:?}"
LABEL="${KW_LABEL:-CAR}"

line="$(python3 - "$KW_CAR_JSON" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
lvl, st, at = d.get("usable_battery_level"), d.get("charging_state"), d.get("_read_at")
if not isinstance(lvl, int) or not isinstance(at, (int, float)) or not st:
    sys.exit("publish: car JSON lacks usable_battery_level/charging_state/_read_at")
print(lvl, str(st).replace(" ", "_"), int(at))
EOF
)"
[ -n "$line" ] || exit 1

# write-then-rename on the host, so the phone can never fetch a half-written line
printf '%s\n' "$line" | ssh -o BatchMode=yes -o ConnectTimeout=15 "$KW_PUB_HOST" \
    "cat > $KW_PUB_DIR/.car.tmp && mv $KW_PUB_DIR/.car.tmp $KW_PUB_DIR/car-$KW_TOKEN.txt"
echo "publish: $line"

# The flower face, same name + .png. Best-effort: a render or upload failure must never cost the
# text line, which is already published above.
read -r lvl st _ <<<"$line"
png="$(mktemp --suffix=.png)"
if python3 "$HERE/flower.py" "$lvl" "$st" "$png" --size 384 --label "$LABEL" &&
   ssh -o BatchMode=yes -o ConnectTimeout=15 "$KW_PUB_HOST" \
       "cat > $KW_PUB_DIR/.car.png.tmp && mv $KW_PUB_DIR/.car.png.tmp $KW_PUB_DIR/car-$KW_TOKEN.png" < "$png"; then
    echo "publish: flower png ok"
else
    echo "publish: flower png FAILED (txt is fine)" >&2
fi
rm -f "$png"
