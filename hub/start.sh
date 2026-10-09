#!/usr/bin/env bash
# Sino hub (D6): bring up the whole hub with one command and print the health light.
#
#   hub/start.sh          start each part that is not answering, keep the AI model warm,
#                         then print the health light
#   hub/start.sh status   only print the health light (starts nothing)
#   hub/start.sh stop     stop only what this script started (the PID files in RUN_DIR)
#
# Anyone on the team can run it. It never turns the firewall on or off.
# Don't press Ctrl+C while it starts things: that would also stop what it just started.
# Docs: docs/sino/architecture.md, "Running the hub server".
set -u

# ---- Settings. Each one can be overridden, e.g. PORT=8001 hub/start.sh ----
PY="${PY:-$HOME/sino/hub-venv/bin/python}"
WHISPER_DIR="${WHISPER_DIR:-$HOME/sino/whisper.cpp}"
WHISPER_MODEL="${WHISPER_MODEL:-models/ggml-small.bin}"   # relative to WHISPER_DIR
VAD_MODEL="${VAD_MODEL:-models/ggml-silero-v6.2.0.bin}"   # relative to WHISPER_DIR; skipped if missing
VAD_PAD_MS="${VAD_PAD_MS:-200}"   # audio kept around speech; Whisper's default 30 ms cut "Tulong" off Donita's real clip, 200 kept it (docs/NOTES.md, Sat ~6:55 AM)
CERT="${CERT:-$HOME/sino/certs/hub.pem}"
KEY="${KEY:-$HOME/sino/certs/hub-key.pem}"
PORT="${PORT:-8000}"
ALWAYS_LISTEN="${ALWAYS_LISTEN:-0}"   # 1 = the hub mic listens all the time (hub/always.py)
RUN_DIR="${RUN_DIR:-$HOME/sino/run}"    # PID files of what this script started
LOG_DIR="${LOG_DIR:-$HOME/sino/logs}"   # one log file per part

# Fixed: brain/server.py and hub/listen.py expect these addresses. Both stay on this Mac.
OLLAMA_URL="http://127.0.0.1:11434"
WHISPER_URL="http://127.0.0.1:8080"
HUB="https://localhost:$PORT"
WAIT_SECONDS=60   # total time to wait for the parts to answer after starting them
WARM_EVERY=60     # keep-warm: seconds between tiny model requests
# A tiny request that runs the whole model once and keeps it loaded (keep_alive -1 = never unload).
WARM='{"model":"qwen2.5:3b","prompt":"hi","stream":false,"keep_alive":-1,"options":{"num_predict":1}}'

SCRIPT="$(cd "$(dirname "$0")" && pwd)/start.sh"
ROOT="$(dirname "$(dirname "$SCRIPT")")"   # the repo (this file is in hub/)
FAILED=""

say() { printf '%s\n' "$*"; }

# Remember a part that did not come up; printed again at the end.
fail() {  # fail PART MESSAGE
  FAILED="${FAILED}  - $1: $2"$'\n'
  say "  FAILED $1: $2"
}

# The hub uses an mkcert certificate: check it against mkcert's root CA, like a phone does.
setup_tls() {
  local ca
  ca="$(mkcert -CAROOT 2>/dev/null)/rootCA.pem"
  if command -v mkcert >/dev/null 2>&1 && [ -f "$ca" ]; then
    TLS=(--cacert "$ca")
  else
    TLS=(-k)
    say "Note: mkcert not found, so the hub's certificate is not checked (curl -k)."
  fi
}

# True when the address gives any HTTP answer within 3 s.
answers() { curl -s -o /dev/null -m 3 "$@"; }
ollama_up() { answers "$OLLAMA_URL/api/version"; }
whisper_up() { answers "$WHISPER_URL/"; }
hub_up() { answers "${TLS[@]}" "$HUB/health"; }

# What each part's command line contains, so a reused PID (after a reboot) is never ours.
pattern() {
  case "$1" in
    ollama) echo "ollama serve" ;;
    whisper) echo "whisper-server" ;;
    server) echo "brain/server.py" ;;
    keep-warm) echo "start.sh keep-warm" ;;
  esac
}

# Print the PID from RUN_DIR/<part>.pid if that process is alive and is still that part.
running_pid() {  # running_pid PART
  local pid
  pid="$(cat "$RUN_DIR/$1.pid" 2>/dev/null)"
  case "$pid" in '' | *[!0-9]*) return 1 ;; esac
  kill -0 "$pid" 2>/dev/null || return 1
  case "$(ps -p "$pid" -o command= 2>/dev/null)" in
    *"$(pattern "$1")"*) echo "$pid" ;;
    *) return 1 ;;
  esac
}

# Start a command in the background: it survives closing the terminal, its output is
# appended to LOG_DIR/<part>.log, and its PID goes to RUN_DIR/<part>.pid.
launch() {  # launch PART COMMAND...
  local part="$1"
  shift
  nohup "$@" >>"$LOG_DIR/$part.log" 2>&1 </dev/null &
  echo "$!" >"$RUN_DIR/$part.pid"
  say "  $part: started (pid $!, log $LOG_DIR/$part.log)"
}

# Wait (until the shared deadline) for a part we started to answer.
wait_for() {  # wait_for LABEL CHECK PART
  case "$FAILED" in *"- $1:"*) return 1 ;; esac   # already failed to start
  until "$2"; do
    if ! running_pid "$3" >/dev/null; then
      fail "$1" "is not running. Log: $LOG_DIR/$3.log"
      return 1
    elif [ "$SECONDS" -ge "$DEADLINE" ]; then
      fail "$1" "did not answer within $WAIT_SECONDS s. Log: $LOG_DIR/$3.log"
      return 1
    fi
    sleep 1
  done
}

# Internal ("hub/start.sh keep-warm", started by start): one tiny model request every minute.
# Why: on this 8 GB hub the first request after ~35 min idle took 9.00 s because macOS had
# swapped the model out; warm it took 1.17 s (docs/NOTES.md, model smoke test).
keep_warm() {
  while sleep "$WARM_EVERY"; do
    curl -sf -o /dev/null -m 30 "$OLLAMA_URL/api/generate" -d "$WARM" \
      || say "$(date '+%Y-%m-%d %H:%M:%S') keep-warm: no answer from Ollama"
  done
}

do_start() {
  local pid took
  mkdir -p "$RUN_DIR" "$LOG_DIR" || exit 1
  RUN_DIR="$(cd "$RUN_DIR" && pwd)"
  LOG_DIR="$(cd "$LOG_DIR" && pwd)"
  say "Starting the Sino hub (parts that already answer are left alone)"

  # 1. Ollama, the AI model runtime. It listens on 127.0.0.1 only.
  if ollama_up; then
    say "  ollama: already running"
  elif ! command -v ollama >/dev/null 2>&1; then
    fail "Ollama" "the ollama command is not installed"
  else
    launch ollama env OLLAMA_KEEP_ALIVE=-1 ollama serve
  fi

  # 2. Whisper (speech to text), with voice detection when its model file is there.
  if whisper_up; then
    say "  whisper: already running"
  elif [ ! -x "$WHISPER_DIR/build/bin/whisper-server" ]; then
    fail "Whisper" "no $WHISPER_DIR/build/bin/whisper-server"
  else
    (
      cd "$WHISPER_DIR" || exit 1
      if [ -f "$VAD_MODEL" ]; then
        launch whisper ./build/bin/whisper-server -m "$WHISPER_MODEL" -l tl --vad -vm "$VAD_MODEL" \
          --vad-speech-pad-ms "$VAD_PAD_MS" --host 127.0.0.1 --port 8080 --convert
      else
        say "  whisper: no $VAD_MODEL, starting without --vad"
        launch whisper ./build/bin/whisper-server -m "$WHISPER_MODEL" -l tl \
          --host 127.0.0.1 --port 8080 --convert
      fi
    )
  fi

  # 3. The hub server. main() in brain/server.py points at the hub's questions and opens the mic.
  if hub_up; then
    say "  server: already running"
  elif [ ! -x "$PY" ]; then
    fail "Hub server" "no Python at $PY"
  elif [ ! -f "$CERT" ] || [ ! -f "$KEY" ]; then
    fail "Hub server" "certificate missing ($CERT, $KEY)"
  else
    (cd "$ROOT" && launch server env HOST=0.0.0.0 PORT="$PORT" SINO_MODEL=ollama \
      ALWAYS_LISTEN="$ALWAYS_LISTEN" HUB_URL="$OLLAMA_URL" CERT="$CERT" KEY="$KEY" "$PY" brain/server.py)
  fi

  # 4. Wait for each part to answer (WAIT_SECONDS in total, not per part).
  DEADLINE=$((SECONDS + WAIT_SECONDS))
  wait_for "Ollama" ollama_up ollama
  wait_for "Whisper" whisper_up whisper
  wait_for "Hub server" hub_up server

  # 5. Load qwen2.5:3b now so the first real question does not wait for it.
  if ollama_up; then
    if took="$(curl -sf -o /dev/null -m 60 -w '%{time_total}' "$OLLAMA_URL/api/generate" -d "$WARM")"; then
      say "  AI model qwen2.5:3b: loaded (warm-up request took $took s)"
    else
      fail "AI model" "qwen2.5:3b did not answer (is it pulled? ollama list). Log: $LOG_DIR/ollama.log"
    fi
  fi

  # 6. Keep-warm loop, unless one is already running.
  if pid="$(running_pid keep-warm)"; then
    say "  keep-warm: already running (pid $pid)"
  else
    launch keep-warm bash "$SCRIPT" keep-warm
  fi

  say ""
  do_status
  if [ -n "$FAILED" ]; then
    say ""
    say "NOT everything came up:"
    printf '%s' "$FAILED"
    exit 1
  fi
}

# One health-light line from the hub's /health JSON: OK when it has "<key>":true.
light() {  # light KEY LABEL
  case "$HEALTH" in
    *"\"$1\":true"*) say "  OK    $2" ;;
    *) say "  DOWN  $2"; return 1 ;;
  esac
}

# One line from a direct check (used when the hub server is down).
direct() {  # direct CHECK LABEL
  if "$1"; then say "  OK    $2"; else say "  DOWN  $2"; return 1; fi
}

do_status() {
  local mode ip sans pid down=0
  HEALTH="$(curl -s -m 5 "${TLS[@]}" "$HUB/health")"
  say "Sino hub health light:"
  if [ -n "$HEALTH" ]; then
    mode="$(printf '%s' "$HEALTH" | sed -n 's/.*"model":"\([a-z]*\)".*/\1/p')"
    light whisper "Whisper (speech to text)" || down=1
    light ollama "AI model (Ollama)" || down=1
    light server "Hub server, $HUB (decisions: ${mode:-unknown})" || down=1
    light mic "Microphone"
    light offline "Offline (internet blocked)"
  else
    direct whisper_up "Whisper (speech to text)" || down=1
    direct ollama_up "AI model (Ollama)" || down=1
    say "  DOWN  Hub server, $HUB"
    say "  ?     Microphone (unknown while the hub server is down)"
    say "  ?     Offline (unknown while the hub server is down)"
    down=1
  fi
  if [ "$ALWAYS_LISTEN" = "1" ]; then
    say "  Always-listening: ON"
  else
    say "  Always-listening: OFF (set ALWAYS_LISTEN=1 and restart to turn on)"
  fi
  if pid="$(running_pid keep-warm)"; then
    say "  OK    Keep-warm loop (pid $pid)"
  else
    say "  DOWN  Keep-warm loop (only hub/start.sh starts it)"
  fi

  ip="$(ipconfig getifaddr en0 2>/dev/null)"
  if [ -z "$ip" ]; then
    say "Hub URL: unknown, en0 has no IP (is the hub on the hotspot Wi-Fi?)"
  else
    say "Hub URL for the iPad and phone: https://$ip:$PORT"
    # Phones refuse the hub if its certificate does not name this IP.
    sans="$(openssl x509 -noout -text -in "$CERT" 2>/dev/null | grep 'IP Address:')"
    case "$sans," in
      *"IP Address:$ip,"*) ;;
      *) say "WARNING: $CERT does not include $ip. Make a new one, then restart the hub server:"
         say "  mkcert -cert-file \"$CERT\" -key-file \"$KEY\" $ip localhost" ;;
    esac
  fi
  say "Firewall: NOT turned on by this script. To block the internet:"
  say "  sudo pfctl -f /etc/pf.sino.conf -e   (docs/sino/DONITA-SETUP.md, section 5)"
  return "$down"
}

do_stop() {
  local part pid left=0
  say "Stopping only what hub/start.sh started (PID files in $RUN_DIR)"
  for part in keep-warm server whisper ollama; do
    if [ ! -f "$RUN_DIR/$part.pid" ]; then
      say "  $part: no PID file, left alone"
    elif pid="$(running_pid "$part")"; then
      kill "$pid"
      # Give it up to 10 s to shut down cleanly (Ollama also stops its model runner).
      for _ in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
      if kill -0 "$pid" 2>/dev/null; then
        say "  $part: still running after 10 s (pid $pid). PID file kept; run stop again"
        left=1
      else
        rm -f "$RUN_DIR/$part.pid"
        say "  $part: stopped (pid $pid)"
      fi
    else
      rm -f "$RUN_DIR/$part.pid"
      say "  $part: not running, or that PID is no longer ours (old PID file removed), nothing killed"
    fi
  done
  return "$left"
}

case "${1:-start}" in
  start) setup_tls; do_start ;;
  status) setup_tls; do_status ;;
  stop) do_stop ;;
  keep-warm) keep_warm ;;
  *) say "Usage: hub/start.sh [start|status|stop]"; exit 2 ;;
esac
