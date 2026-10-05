#!/usr/bin/env bash
# Optional: make the phone's widgets redraw NOW (after kw_publish.py or a new reading) instead of
# waiting for the hourly run or a tap. Needs the "KW kick" profile (Intent Received KW_REFRESH) and
# a shell on the phone: here Termux's sshd, reachable as $KW_PHONE_HOST (see kw.env.example).
# "Broadcast sent" proves it was SENT, not that Tasker ran. The proof is your host's access log:
# a fetch of kw-<tok>.json with a Tasker user agent.
set -euo pipefail
: "${KW_PHONE_HOST:?set KW_PHONE_HOST (an ssh host alias for the phone)}"
ssh -o BatchMode=yes -o ConnectTimeout=8 "$KW_PHONE_HOST" 'am broadcast -a kw.KW_REFRESH' | grep -m1 'Broadcast sent'
