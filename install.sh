#!/usr/bin/env bash
# Session Kit's installer, the fast track:
#
#   curl -fsSL https://sessionkit.ai/install.sh | bash
#   bash install.sh [--yes] [--dry-run] [--no-speech] [--check] [--help]
#
# It checks this Mac, lists what it will install, in order, and asks before it
# installs anything. With --check it is the kit's doctor: it runs the same
# checks, prints the command that adds each missing thing, installs nothing
# and asks nothing. The question reads /dev/tty, never stdin: under
# `curl | bash`, stdin is the rest of this script. With no terminal it refuses
# unless --yes is given. It never runs sudo: Homebrew's own installer is the one
# step that asks for a password, and it runs first, after the yes.
#
# Written for the bash a fresh Mac has (3.2): no associative arrays.
# The whole script is functions, and its last line calls main, so a download
# cut off part-way runs nothing.
#
# shellcheck disable=SC2329 # each install_STEP runs by name, from run_step

set -o pipefail

# --- Each decision is one constant ------------------------------------------

# What Enter means at the question: yes continues, as Homebrew's installer does.
CONFIRM_DEFAULT=yes
# The speech server and the ears are in the list unless --no-speech is given.
SPEECH_DEFAULT=yes
# The arguments to `ears` that install the speech server and the ears: the
# speech server, the mouth, the keeper and the mail job, with the seat that
# speaking wakes. One place, so a change to the command is one line.
SPEECH_ARGV=(services install --agent claude)
SPEECH_PORT=8890
# --check asks the speech server itself, on its port: the check
# docs/troubleshooting.md gives a reader.
SPEECH_PROBE_URL=http://127.0.0.1:$SPEECH_PORT/v1/models
# `sessionkit setup` exits 4 when the operator is set and mail steps are left
# for you. For this installer that is a success: the end screen names them.
SETUP_STEPS_LEFT=4
# The mail hooks are sessionmail's setting, so sessionmail's own verb turns
# them on: the installer never writes that file itself. The verb is
# there when `pager settings --help` lists a `hooks` command; an older pager
# lists only install and migrate, and then the end screen names HOOKS_BY_HAND.
HOOKS_ARGV=(settings hooks on)
HOOKS_BY_HAND='set "hooks": true in ~/.sessionkit/mail/settings/mail.json, and change no other key'
KIT_PYTHON=3.14
MARKETPLACE=sessionkit/sessionkit
PLUGIN=sessionkit@sessionkit
BREW_SET=(tmux ffmpeg notmuch)
# Where Homebrew lives: Apple silicon first, then Intel.
BREW_PATHS=(/opt/homebrew/bin/brew /usr/local/bin/brew)
# The whole list took about 9.9 GB on a fresh 16 GB Mac.
DISK_NEED_GB=10

SCRIPT_URL=https://sessionkit.ai/install.sh
# The step-by-step guide is INSTALL.md at the top of this repository.
REPO_URL=https://github.com/sessionkit/sessionkit
BREW_INSTALLER_URL=https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh
UV_INSTALLER_URL=https://astral.sh/uv/install.sh
CLAUDE_INSTALLER_URL=https://claude.ai/install.sh

# Exits.
EXIT_OK=0
EXIT_FAILED=1
EXIT_USAGE=2
EXIT_REFUSED=3
EXIT_DECLINED=4
# --check: something is missing. The same number as a failed step.
EXIT_MISSING=1

# --- Output -------------------------------------------------------------------

setup_colors() {
    if [[ -n "${NO_COLOR:-}" || ! -t 1 ]]; then
        BOLD="" GREEN="" YELLOW="" RED="" RESET=""
    else
        BOLD=$'\033[1m' GREEN=$'\033[32m' YELLOW=$'\033[33m'
        RED=$'\033[31m' RESET=$'\033[0m'
    fi
}

say() { printf '%s\n' "$*"; }
found() { printf '%s' "${GREEN}$*${RESET}"; }
missing() { printf '%s' "${YELLOW}$*${RESET}"; }

# A path as the user writes it: ~/x for a path under HOME.
tildify() {
    # shellcheck disable=SC2088 # the user reads this ~; nothing expands it
    case "$1" in
        "$HOME"/*) printf '~/%s' "${1#"$HOME"/}" ;;
        *) printf '%s' "$1" ;;
    esac
}

# "a", "a and b", "a, b and c"
join_and() {
    local out="" i n=$#
    for ((i = 1; i <= n; i++)); do
        if ((i == 1)); then
            out="${!i}"
        elif ((i == n)); then
            out="$out and ${!i}"
        else
            out="$out, ${!i}"
        fi
    done
    printf '%s' "$out"
}

duration() {
    local s=$1
    if ((s >= 60)); then
        printf '%d min %d s' $((s / 60)) $((s % 60))
    else
        printf '%d s' "$s"
    fi
}

usage() {
    cat <<EOF
Session Kit's installer: it checks this Mac, lists what it will install, and
asks before it installs anything.

Usage:
    curl -fsSL $SCRIPT_URL | bash
    curl -fsSL $SCRIPT_URL | bash -s -- [OPTIONS]
    bash install.sh [OPTIONS]

Options:
    -y, --yes      install without the question (the list is still printed)
    --dry-run      print the checks and the list, install nothing
    --no-speech    leave the speech server and the ears out of the list
    --check        check this Mac: what is missing, and the command that adds
                   each one. It installs nothing and asks nothing:
                   curl -fsSL $SCRIPT_URL | bash -s -- --check
    -h, --help     this help

Exits: 0 installed, nothing to do, or a dry run; 1 a step failed; 2 usage;
3 refused before installing; 4 you said no.
With --check: 0 nothing is missing; 1 something is missing; 2 usage;
3 this Mac cannot be checked (not macOS, or run as root).

Step by step instead: INSTALL.md, at $REPO_URL
EOF
}

# --- Flags ----------------------------------------------------------------------

parse_args() {
    YES=no
    DRY_RUN=no
    CHECK=no
    SPEECH=$SPEECH_DEFAULT
    while (($#)); do
        case "$1" in
            -y | --yes) YES=yes ;;
            --dry-run) DRY_RUN=yes ;;
            --no-speech) SPEECH=no ;;
            --check) CHECK=yes ;;
            -h | --help)
                usage
                exit "$EXIT_OK"
                ;;
            *)
                say "install.sh: unknown option: $1" >&2
                say "Run it with --help for the options." >&2
                exit "$EXIT_USAGE"
                ;;
        esac
        shift
    done
    if [[ "$CHECK" == yes && "$YES" == yes ]]; then
        say "install.sh: --check installs nothing, so --yes does not go with it." >&2
        say "Run it with --help for the options." >&2
        exit "$EXIT_USAGE"
    fi
}

# --- Small probes ---------------------------------------------------------------

tty_available() { (exec </dev/tty) 2>/dev/null; }

on_path() {
    case ":$PATH:" in
        *":$1:"*) return 0 ;;
        *) return 1 ;;
    esac
}

# The command NAME: on PATH, else under ~/.local/bin, else empty.
find_tool() {
    local p
    p=$(command -v "$1" 2>/dev/null) && { printf '%s' "$p"; return 0; }
    [[ -x "$HOME/.local/bin/$1" ]] && { printf '%s' "$HOME/.local/bin/$1"; return 0; }
    return 1
}

zprofile_path() { printf '%s' "${ZDOTDIR:-$HOME}/.zprofile"; }

zprofile_has_brew() {
    local f
    f=$(zprofile_path)
    [[ -f "$f" ]] && grep -q 'brew shellenv' "$f"
}

# The shell files uv's installer adds its line to, on this Mac. None when
# ~/.local/bin is already on PATH: then uv writes no env file and no line.
uv_rc_files() {
    UV_RC=()
    on_path "$HOME/.local/bin" && return 0
    local zdir=${ZDOTDIR:-$HOME} f
    if [[ -f "$zdir/.zshrc" ]]; then
        UV_RC+=("$zdir/.zshrc")
    elif [[ -f "$zdir/.zshenv" ]]; then
        UV_RC+=("$zdir/.zshenv")
    else
        UV_RC+=("$zdir/.zshrc")
    fi
    UV_RC+=("$HOME/.profile")
    for f in .bashrc .bash_profile .bash_login; do
        [[ -f "$HOME/$f" ]] && UV_RC+=("$HOME/$f")
    done
    return 0
}

# --- Refusals before the checks ----------------------------------------------

refuse_early() {
    if [[ "$(uname -s 2>/dev/null)" != Darwin ]]; then
        say "🛑 Session Kit's installer is for macOS. On Linux, which is untested, go step by step with INSTALL.md, at:"
        say "    $REPO_URL"
        exit "$EXIT_REFUSED"
    fi
    if [[ "$(id -u 2>/dev/null)" == 0 || -n "${SUDO_USER:-}" ]]; then
        say "🛑 Run this as yourself, without sudo. Homebrew asks for your password itself."
        exit "$EXIT_REFUSED"
    fi
}

# --- The checks: each is read-only, and none installs -----------------------

check_all() {
    MISSING_ROWS=0
    [[ "$CHECK" == yes ]] || say "🔍 ${BOLD}Checking this Mac${RESET}"

    local ver arch
    ver=$(sw_vers -productVersion 2>/dev/null)
    arch=$(uname -m 2>/dev/null)
    if [[ "$arch" == arm64 ]]; then
        ARCH_WORDS="Apple silicon"
    else
        ARCH_WORDS="Intel"
    fi
    say "🍎 macOS: ${ver:-unknown} on $ARCH_WORDS"

    if id -Gn 2>/dev/null | tr ' ' '\n' | grep -qx admin; then
        ADMIN=yes
    else
        ADMIN=no
    fi
    say "👤 Administrator: $ADMIN (Homebrew's installer needs one)"

    # Homebrew
    local p
    BREW="" BREW_STATE=missing
    if p=$(command -v brew 2>/dev/null); then
        BREW=$p BREW_STATE=found
    else
        for p in "${BREW_PATHS[@]}"; do
            if [[ -x "$p" ]]; then
                BREW=$p BREW_STATE=offpath
                break
            fi
        done
    fi
    case "$BREW_STATE" in
        found) say "🍺 Homebrew: $(found found)$(version_of brew)" ;;
        offpath) say "🍺 Homebrew: $(found found), $(missing "not on your PATH")" ;;
        *) say "🍺 Homebrew: $(missing missing)" ;;
    esac
    check_row homebrew
    check_row brewpath

    UV=$(find_tool uv) || UV=""
    if [[ -n "$UV" ]]; then
        say "🐍 uv: $(found found)$(version_of uv)"
    else
        say "🐍 uv: $(missing missing)"
    fi
    check_row uv

    CLAUDE=$(find_tool claude) || CLAUDE=""
    if [[ -n "$CLAUDE" ]]; then
        say "🤖 Claude Code: $(found found)$(version_of claude)"
    else
        say "🤖 Claude Code: $(missing missing)"
    fi
    check_row claude

    # tmux, ffmpeg and notmuch: Homebrew's own answer first, then the PATH.
    # Read brew's output, not its exit: it can print the version and still
    # exit 1 when it cannot write its own cache.
    # HOMEBREW_NO_INSTALL_FROM_API=1 keeps this read local: without it, a
    # Homebrew with no cache yet downloads its package list from the
    # internet first, and takes a lock under its own prefix (measured on
    # macOS 27). Every read in the checks carries it, one command at a time
    # (version_of's `brew --version` too); `brew install` never does.
    local name icon out
    MISSING_SET=()
    for name in "${BREW_SET[@]}"; do
        case "$name" in
            tmux) icon="🖥️" ;;
            ffmpeg) icon="🎞️" ;;
            *) icon="📨" ;;
        esac
        out=""
        [[ -n "$BREW" ]] && out=$(HOMEBREW_NO_INSTALL_FROM_API=1 "$BREW" list --versions "$name" 2>/dev/null </dev/null)
        if [[ "$out" == "$name "* ]]; then
            say "$icon $name: $(found found), ${out#"$name "}"
        elif command -v "$name" >/dev/null 2>&1; then
            say "$icon $name: $(found found)"
        else
            say "$icon $name: $(missing missing)"
            MISSING_SET+=("$name")
            # One row each, so each gets the brew line for its own name.
            if [[ "$CHECK" == yes ]]; then
                MISSING_ROWS=$((MISSING_ROWS + 1))
                remedy brewset "$name"
            fi
        fi
    done

    KIT=no
    if [[ -n "$UV" ]]; then
        out=$("$UV" tool list 2>/dev/null </dev/null | grep '^sessionkit v' | head -1)
        if [[ -n "$out" ]]; then
            KIT=yes
            say "📦 Session Kit: $(found found), ${out#sessionkit v}"
        fi
    fi
    [[ "$KIT" == yes ]] || say "📦 Session Kit: $(missing missing)"
    check_row kit

    # Setup is done when its dry run exits 0. Any other exit puts it in the list.
    SETUP=no
    SK=$(find_tool sessionkit) || SK=""
    local rc=1
    if [[ "$KIT" == yes && -n "$SK" ]]; then
        "$SK" setup --dry-run >/dev/null 2>&1 </dev/null
        rc=$?
    fi
    SETUP_RC=$rc
    if ((rc == 0)); then
        SETUP=yes
        say "⚙️ Session Kit setup (your mail box, you as operator): $(found "done")"
    elif ((rc == SETUP_STEPS_LEFT)); then
        say "⚙️ Session Kit setup (your mail box, you as operator): $(missing "not done, mail steps left")"
    else
        say "⚙️ Session Kit setup (your mail box, you as operator): $(missing "not done")"
    fi
    check_row setup
    check_hooks

    PLUGINS=no
    if [[ -n "$CLAUDE" ]] && "$CLAUDE" plugin list 2>/dev/null </dev/null | grep -q "$PLUGIN"; then
        PLUGINS=yes
    fi
    if [[ "$PLUGINS" == yes ]]; then
        say "🧩 Claude Code plugins: $(found found)"
    else
        say "🧩 Claude Code plugins: $(missing missing)"
    fi
    check_row plugins

    # Ask the tool, not the path, so a move of its model folder does not break this.
    EARS=$(find_tool ears) || EARS=""
    EARS_MODEL=no
    if [[ -n "$EARS" ]] && "$EARS" backends 2>/dev/null </dev/null | grep -qE '^silero +ok'; then
        EARS_MODEL=yes
    fi
    if [[ "$EARS_MODEL" == yes ]]; then
        say "🎙️ Ears voice model: $(found found)"
    else
        say "🎙️ Ears voice model: $(missing missing)"
    fi
    check_row ears

    check_speech
    check_port
    say ""
}

# Whether the pager at $1 has mail's hooks verb: its help lists a `hooks` command. Read the
# help text, never a bare exit: a bare `pager settings hooks` exits 2 for a
# usage error and for a refusal alike.
hooks_verb() {
    local help
    help=$("$1" settings --help 2>/dev/null </dev/null)
    grep -qE '^[[:space:]]+hooks([[:space:]]|$)' <<<"$help"
}

# The mail hooks, read by sessionmail's own verb: bare, it writes nothing and
# exits 0 for on, 3 for off. Not under --check: there the doctor's hooks row,
# read by sessionmail's own settings reader, is the one row for them.
check_hooks() {
    HOOKS=unchecked HOOKS_LEFT=no HOOKS_WHY=""
    [[ "$CHECK" == yes ]] && return 0
    # Never the name PAGER: that is the user's, which git and man read, and
    # every step after the checks would inherit what was put in it.
    local what="📬 Mail hooks (so a seat hears mail while idle)" rc mail_pager
    HOOKS=nopager
    mail_pager=$(find_tool pager) || mail_pager=""
    if [[ -n "$mail_pager" ]] && hooks_verb "$mail_pager"; then
        "$mail_pager" settings hooks >/dev/null 2>&1 </dev/null
        rc=$?
        case "$rc" in
            0) HOOKS=on ;;
            3) HOOKS=off ;;
            *) HOOKS=fault ;;
        esac
    elif [[ -n "$mail_pager" ]]; then
        HOOKS=noverb HOOKS_LEFT=yes HOOKS_WHY="this pager has no hooks verb yet"
    fi
    case "$HOOKS" in
        on) say "$what: $(found on)" ;;
        off) say "$what: $(missing off)" ;;
        fault) say "$what: $(missing "off by mistake") (pager settings hooks says why)" ;;
        noverb) say "$what: not checked ($HOOKS_WHY)" ;;
        *) say "$what: $(missing "not checked yet") (the kit brings the pager that turns them on)" ;;
    esac
}

version_of() {
    local v=""
    case "$1" in
        # A check's read: kept local, as the brew list reads in check_all are.
        # So kept, brew prints a second line; the first is read here, not
        # through `head -1`, whose early close fails the pipe (pipefail).
        brew) v=$(HOMEBREW_NO_INSTALL_FROM_API=1 "$BREW" --version 2>/dev/null </dev/null) && v=${v%%$'\n'*} && v=${v#Homebrew } ;;
        uv) v=$("$UV" --version 2>/dev/null </dev/null) && v=${v#uv } && v=${v%% *} ;;
        claude) v=$("$CLAUDE" --version 2>/dev/null </dev/null) && v=${v%% *} ;;
    esac
    [[ -n "$v" ]] && printf ', %s' "$v"
    return 0
}

# The speech server and the ears are here when `ears services status` shows the
# mouth, the keeper and the mail job installed, and mlx-audio serving the port.
check_speech() {
    SPEECH_HERE=no
    local out
    if [[ -n "$EARS" ]]; then
        out=$("$EARS" services status 2>/dev/null </dev/null)
        if printf '%s\n' "$out" | grep -qE '^mouth ' &&
            printf '%s\n' "$out" | grep -qE '^keeper ' &&
            printf '%s\n' "$out" | grep -qE '^mail ' &&
            ! printf '%s\n' "$out" | grep -qE '^(mouth|keeper|mail) +not installed' &&
            printf '%s\n' "$out" | grep -qE '^speech +mlx-audio on'; then
            SPEECH_HERE=yes
        fi
    fi
    if [[ "$CHECK" == yes ]]; then
        check_speech_rows
        return 0
    fi
    if [[ "$SPEECH_HERE" == yes ]]; then
        say "👂 Speech server and ears: $(found found)"
    elif [[ "$SPEECH" == no ]]; then
        say "👂 Speech server and ears: $(missing missing) (left out: --no-speech)"
    else
        say "👂 Speech server and ears: $(missing missing)"
    fi
}

# Under --check the one row is two. The ears services row is SPEECH_HERE, the
# installer's own answer, so it is missing exactly when the speech step would
# be listed. The speech server row asks the server itself.
check_speech_rows() {
    local what="👂 Ears services (mouth, keeper, mail, the speech job)"
    if [[ "$SPEECH_HERE" == yes ]]; then
        say "$what: $(found found)"
    elif [[ "$SPEECH" == no ]]; then
        say "$what: $(missing missing) (left out: --no-speech)"
    else
        say "$what: $(missing missing)"
    fi
    check_row speech
    check_speech_server
}

# Row 14, --check only: does the speech server answer on its port? It asks the
# server, never the stt line of `ears services status`: a release test found that
# line saying "not installed" while the server served. --noproxy keeps an
# http_proxy in the environment from sending the probe off this Mac.
#
# This row is the one exception to "a row is missing exactly when the
# installer's plan() lists its step". The jobs can be installed and the server
# still not answer (it is loading its model, or it crashed): plan() is empty,
# so the installer has nothing to do, and --check still exits 1. Those are two
# questions, and each answers its own honestly.
check_speech_server() {
    SERVER_MISSING=no
    local what="🗣️ Speech server on port $SPEECH_PORT" code=""
    if [[ "$SPEECH" == no ]]; then
        say "$what: not checked (left out: --no-speech)"
        return 0
    fi
    if ! command -v curl >/dev/null 2>&1; then
        say "$what: not checked (no curl)"
        return 0
    fi
    code=$(curl -fsS --noproxy 127.0.0.1 -m 3 -o /dev/null -w '%{http_code}' "$SPEECH_PROBE_URL" 2>/dev/null </dev/null)
    if [[ "$code" == 200 ]]; then
        say "$what: $(found serving)"
        return 0
    fi
    SERVER_MISSING=yes
    MISSING_ROWS=$((MISSING_ROWS + 1))
    say "$what: $(missing "not answering")"
    if step_needed speech; then
        remedy speech
    else
        say "${REMEDY}ears services status"
        say "${REMEDY_MORE}it names the speech job and what it is doing; a server loading its model answers in a minute or two"
    fi
}

# Who listens on the speech server's port, read-only. The speech step adopts an
# mlx-audio server there, and stops if it is something else. lsof names the
# holder only when it runs as this account: another account's server is
# invisible to it, so a connection is tried as well before the port is "free".
check_port() {
    PORT_HOLDER=""
    local out="" name pid
    if command -v lsof >/dev/null 2>&1; then
        out=$(lsof -nP -iTCP:"$SPEECH_PORT" -sTCP:LISTEN 2>/dev/null </dev/null | awk 'NR == 2 {print $1, $2}')
    fi
    if [[ -n "$out" ]]; then
        name=${out% *} pid=${out##* }
        PORT_HOLDER="$(full_command_name "$name" "$pid") (pid $pid)"
    elif command -v nc >/dev/null 2>&1 && nc -z 127.0.0.1 "$SPEECH_PORT" </dev/null >/dev/null 2>&1; then
        PORT_HOLDER="a server lsof does not show (another account's)"
    elif ! command -v lsof >/dev/null 2>&1 && ! command -v nc >/dev/null 2>&1; then
        say "🔌 Port $SPEECH_PORT (the speech server's): not checked (no lsof, no nc)"
        return 0
    fi
    if [[ -n "$PORT_HOLDER" ]]; then
        say "🔌 Port $SPEECH_PORT (the speech server's): held by $PORT_HOLDER"
    else
        say "🔌 Port $SPEECH_PORT (the speech server's): free"
    fi
}

# lsof cuts a command name at 9 characters: python3.12 reads "python3.1". ps
# gives the whole name. It is used only when it starts with lsof's, so a pid
# reused in between, or a name lsof escaped, keeps lsof's.
full_command_name() {
    local full
    full=$(ps -o comm= -p "$2" 2>/dev/null | head -1)
    full=${full##*/}
    if [[ -n "$full" && "$full" == "$1"* ]]; then
        printf '%s' "$full"
    else
        printf '%s' "$1"
    fi
}

# --- The plan ---------------------------------------------------------------

# The steps, in the order they run. Setup runs after everything it reads is in
# place, and the mail hooks after setup, last.
STEP_ORDER=(homebrew brewpath uv claude brewset kit plugins ears speech setup hooks)

# Whether STEP is still to do on this Mac. plan() lists exactly these, and
# --check reads a row as missing exactly when its step is here, so the doctor
# and the installer cannot disagree (row 14, check_speech_server, aside). The
# hooks step is never a --check row: the doctor's hooks row is (check_hooks).
step_needed() {
    case "$1" in
        homebrew) [[ "$BREW_STATE" == missing ]] ;;
        brewpath) [[ "$BREW_STATE" == offpath ]] && ! zprofile_has_brew ;;
        uv) [[ -z "$UV" ]] ;;
        claude) [[ -z "$CLAUDE" ]] ;;
        brewset) ((${#MISSING_SET[@]})) ;;
        kit) [[ "$KIT" == no ]] ;;
        plugins) [[ "$PLUGINS" == no ]] ;;
        ears) [[ "$EARS_MODEL" == no ]] ;;
        speech) [[ "$SPEECH" == yes && "$SPEECH_HERE" == no ]] ;;
        setup) [[ "$SETUP" == no ]] ;;
        # Not with a pager that has no verb: then there is nothing to run,
        # and the end screen names the step instead.
        hooks) [[ "$HOOKS" == off || "$HOOKS" == fault || "$HOOKS" == nopager ]] ;;
        *) return 1 ;;
    esac
}

plan() {
    local s
    STEPS=()
    for s in "${STEP_ORDER[@]}"; do
        step_needed "$s" && STEPS+=("$s")
    done
    return 0
}

has_step() {
    local s
    for s in "${STEPS[@]}"; do
        [[ "$s" == "$1" ]] && return 0
    done
    return 1
}

# Where a fresh Homebrew lands on this Mac.
new_brew_path() {
    if [[ "$ARCH_WORDS" == "Apple silicon" ]]; then
        printf '%s' "${BREW_PATHS[0]}"
    else
        printf '%s' "${BREW_PATHS[1]}"
    fi
}

EDIT="✏️ "
INDENT="         "

list_step() {
    local f files=()
    case "$1" in
        homebrew)
            say "🍺 Homebrew, with its own installer from brew.sh (it installs Apple's Command Line Tools)"
            say "${INDENT}🔐 asks for your Mac password, and its own [Enter]"
            if zprofile_has_brew; then
                say "${INDENT}${EDIT} $(tildify "$(zprofile_path)") already runs brew shellenv"
            else
                say "${INDENT}${EDIT} adds 1 line to $(tildify "$(zprofile_path)"): eval \"\$($(new_brew_path) shellenv)\""
                SHELL_EDITS=yes
            fi
            ;;
        brewpath)
            say "🍺 Homebrew on your PATH, for new terminals"
            say "${INDENT}${EDIT} adds 1 line to $(tildify "$(zprofile_path)"): eval \"\$($BREW shellenv)\""
            SHELL_EDITS=yes
            ;;
        uv)
            say "🐍 uv, with astral.sh's installer"
            uv_rc_files
            if ((${#UV_RC[@]} == 0)); then
                say "${INDENT}${EDIT} none: ~/.local/bin is on your PATH already, so it changes no shell file"
            else
                for f in "${UV_RC[@]}"; do files+=("$(tildify "$f")"); done
                if ((${#files[@]} == 2)); then
                    say "${INDENT}${EDIT} adds 1 line to ${files[0]} and to ${files[1]}: . \"\$HOME/.local/bin/env\""
                else
                    say "${INDENT}${EDIT} adds 1 line to each of $(join_and "${files[@]}"): . \"\$HOME/.local/bin/env\""
                fi
                say "${INDENT}${EDIT} writes ~/.local/bin/env, ~/.local/bin/env.fish and ~/.config/fish/conf.d/uv.env.fish (for fish)"
                SHELL_EDITS=yes
            fi
            ;;
        claude) say "🤖 Claude Code, with claude.ai's installer" ;;
        brewset) say "🍻 $(join_and "${MISSING_SET[@]}"), from Homebrew: brew install ${MISSING_SET[*]}" ;;
        kit) say "📦 Session Kit: uv tool install --python $KIT_PYTHON sessionkit" ;;
        plugins) say "🧩 the plugins: claude plugin marketplace add, then claude plugin install" ;;
        ears) say "🎙️ ears install: the voice-activity model (2.3 MB)" ;;
        speech)
            say "👂 the speech server and the ears: calls and hearing you (about 2.9 GB, plus its 1.2 GB venv; the microphone asks once)"
            say "${INDENT}to skip it: --no-speech"
            if [[ -n "$PORT_HOLDER" ]]; then
                say "${INDENT}port $SPEECH_PORT is held by $PORT_HOLDER: used if it is mlx-audio, else this step stops"
            fi
            ;;
        setup) say "⚙️ sessionkit setup: your mail box, and you as operator" ;;
        hooks)
            say "📬 turn on the mail hooks (so a seat hears mail while idle): pager ${HOOKS_ARGV[*]}"
            if [[ "$HOOKS" == nopager ]]; then
                say "${INDENT}if the kit's pager has no hooks verb yet, the end screen names the one setting instead"
            fi
            ;;
    esac
}

# --check: the command that adds what STEP adds, under the missing row. Each is
# built from the constants its install_STEP runs, so the two cannot drift.
REMEDY="    → "
REMEDY_MORE="      "

remedy() {
    case "$1" in
        homebrew)
            say "${REMEDY}/bin/bash -c \"\$(curl -fsSL $BREW_INSTALLER_URL)\""
            if [[ "$ADMIN" != yes ]]; then
                say "${REMEDY_MORE}Homebrew's installer needs an administrator account: ask one to run it"
            fi
            ;;
        brewpath) say "${REMEDY}echo 'eval \"\$($BREW shellenv)\"' >> $(tildify "$(zprofile_path)")" ;;
        uv) say "${REMEDY}curl -LsSf $UV_INSTALLER_URL | sh" ;;
        claude) say "${REMEDY}curl -fsSL $CLAUDE_INSTALLER_URL | bash" ;;
        brewset)
            if [[ -n "${2:-}" ]]; then
                say "${REMEDY}brew install $2"
            else
                say "${REMEDY}brew install ${MISSING_SET[*]}"
            fi
            ;;
        kit) say "${REMEDY}uv tool install --python $KIT_PYTHON sessionkit" ;;
        plugins)
            # As install_plugins: the marketplace is added only when it is not there.
            if [[ -z "$CLAUDE" ]] || ! "$CLAUDE" plugin marketplace list 2>/dev/null </dev/null | grep -q "${MARKETPLACE%%/*}"; then
                say "${REMEDY}claude plugin marketplace add $MARKETPLACE"
            fi
            say "${REMEDY}claude plugin install $PLUGIN"
            ;;
        ears) say "${REMEDY}ears install" ;;
        speech) say "${REMEDY}ears ${SPEECH_ARGV[*]}" ;;
        setup)
            if ((SETUP_RC == SETUP_STEPS_LEFT)); then
                say "${REMEDY}sessionkit setup --dry-run"
                say "${REMEDY_MORE}it names the mail steps left; do them, then run sessionkit setup again"
            else
                say "${REMEDY}sessionkit setup"
            fi
            ;;
    esac
}

# --check: a row whose step is still to do is missing, and its remedy follows.
check_row() {
    [[ "$CHECK" == yes ]] || return 0
    step_needed "$1" || return 0
    MISSING_ROWS=$((MISSING_ROWS + 1))
    remedy "$1"
}

print_list() {
    local n=${#STEPS[@]} i=0 s
    if ((n == 1)); then
        say "📋 ${BOLD}It will install this 1:${RESET}"
    else
        say "📋 ${BOLD}It will install these $n, in this order:${RESET}"
    fi
    SHELL_EDITS=no
    for s in "${STEPS[@]}"; do
        i=$((i + 1))
        printf '%4d. ' "$i"
        list_step "$s"
    done
    local edits password
    if [[ "$SHELL_EDITS" == yes ]]; then edits="No other shell file changes"; else edits="No shell file changes"; fi
    if has_step homebrew; then password="no other password"; else password="no password"; fi
    say "   Disk: up to about $DISK_NEED_GB GB (the whole list took about 9.9 GB on a fresh Mac). $edits, and $password."
    say ""
}

# Said after the list when --no-speech leaves the speech server out.
print_speech_later() {
    say "To hear you and take phone calls later, install the speech server and the ears (about 4.1 GB):"
    say "    ears ${SPEECH_ARGV[*]}"
}

warnings() {
    warn_intel
    warn_disk
}

warn_intel() {
    if [[ "$ARCH_WORDS" != "Apple silicon" ]]; then
        say "⚠️ An Intel Mac: Session Kit is tested on Apple silicon."
    fi
}

warn_disk() {
    local free_kb free_gb
    free_kb=$(df -k "$HOME" 2>/dev/null | awk 'NR == 2 {print $4}')
    if [[ "$free_kb" =~ ^[0-9]+$ ]]; then
        free_gb=$((free_kb / 1048576))
        if ((free_gb < DISK_NEED_GB)); then
            say "⚠️ Free disk: $free_gb GB, and the list needs up to about $DISK_NEED_GB GB. A fresh Mac also downloads about 8 GB of its own."
        fi
    fi
}

# --- Refusals after the checks, before the question --------------------------

refuse_late() {
    if has_step homebrew && [[ "$ADMIN" != yes ]]; then
        say "🛑 Homebrew's installer needs an administrator account: ask one to install Homebrew, then run this again."
        return "$EXIT_REFUSED"
    fi
    if has_step homebrew && [[ "$YES" == yes ]] && ! tty_available; then
        say "🛑 Homebrew asks for your password at a terminal: run this in Terminal, or install Homebrew first."
        return "$EXIT_REFUSED"
    fi
    return 0
}

# --- The question -------------------------------------------------------------

confirm() {
    local n=${#STEPS[@]} q hint answer
    if ((n == 1)); then q="Install this one?"; else q="Install these $n?"; fi
    if [[ "$YES" == yes ]]; then
        say "❓ $q yes (--yes)"
        return 0
    fi
    if ! tty_available; then
        say "🛑 No terminal to ask on, so nothing was installed. To install without the question, add --yes:"
        say "    curl -fsSL $SCRIPT_URL | bash -s -- --yes"
        return "$EXIT_REFUSED"
    fi
    if [[ "$CONFIRM_DEFAULT" == yes ]]; then hint="[Y/n]"; else hint="[y/N]"; fi
    while true; do
        printf '❓ %s %s ' "$q" "$hint"
        if ! IFS= read -r answer </dev/tty; then
            say ""
            say "🛑 No answer, so nothing was installed."
            return "$EXIT_REFUSED"
        fi
        answer=$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')
        [[ -z "$answer" ]] && answer=$CONFIRM_DEFAULT
        case "$answer" in
            y | yes) answer=yes ;;
            n | no) answer=no ;;
            *)
                say "   Type y for yes or n for no."
                continue
                ;;
        esac
        # The question's line ends as a record of the answer.
        if [[ -t 1 ]]; then
            printf '\033[1A\r\033[2K❓ %s %s\n' "$q" "$answer"
        fi
        [[ "$answer" == yes ]] && return 0
        say "👋 Nothing was installed."
        return "$EXIT_DECLINED"
    done
}

# --- The steps, in their order ---------------------------------------------

# Homebrew's installer is the one child that reads the terminal: it asks for the
# password and its own Enter there. Every other child gets /dev/null.
install_homebrew() {
    local script p
    script=$(curl -fsSL "$BREW_INSTALLER_URL" </dev/null) || return 1
    [[ -n "$script" ]] || return 1
    /bin/bash -c "$script" </dev/tty || return $?
    BREW=""
    for p in "${BREW_PATHS[@]}"; do
        if [[ -x "$p" ]]; then BREW=$p; break; fi
    done
    [[ -n "$BREW" ]] || return 1
    brew_on_path
}

# Puts brew on this run's PATH, and writes the line new terminals need once.
brew_on_path() {
    eval "$("$BREW" shellenv)" || return 1
    if ! zprofile_has_brew; then
        local f
        f=$(zprofile_path)
        # shellcheck disable=SC2016 # the line is written as text, for zsh to run later
        printf '\neval "$(%s shellenv)"\n' "$BREW" >>"$f" || return 1
        say "${EDIT} added Homebrew to $(tildify "$f") (Homebrew's next steps are done)"
    fi
}

install_brewpath() { brew_on_path; }

# uv's installer runs with ~/.local/bin off this run's PATH: when the folder is
# already there, it writes no env file and no shell line, and a new terminal
# would lack uv. The folder joins the PATH only after it has run.
install_uv() {
    curl -LsSf "$UV_INSTALLER_URL" </dev/null | sh || return $?
    on_path "$HOME/.local/bin" || export PATH="$HOME/.local/bin:$PATH"
}

install_claude() {
    curl -fsSL "$CLAUDE_INSTALLER_URL" </dev/null | bash
}

install_brewset() {
    brew install "${MISSING_SET[@]}" </dev/null
}

install_kit() {
    uv tool install --python "$KIT_PYTHON" sessionkit </dev/null
}

install_plugins() {
    if ! claude plugin marketplace list 2>/dev/null </dev/null | grep -q "${MARKETPLACE%%/*}"; then
        claude plugin marketplace add "$MARKETPLACE" </dev/null || return $?
    fi
    claude plugin install "$PLUGIN" </dev/null
}

install_ears() {
    ears install </dev/null
}

install_speech() {
    ears "${SPEECH_ARGV[@]}" </dev/null
}

install_setup() {
    sessionkit setup </dev/null
}

# After setup. It never fails the install: setup succeeded, so a pager with no
# verb, or one that refuses, leaves the step to the end screen (HOOKS_LEFT).
# The verb's own line goes to the screen; its stderr is kept, to be named.
install_hooks() {
    local err rc mail_pager
    HOOKS_LEFT=yes
    mail_pager=$(find_tool pager) || mail_pager=""
    if [[ -z "$mail_pager" ]]; then
        HOOKS_WHY="no pager on the PATH"
        return 0
    fi
    if ! hooks_verb "$mail_pager"; then
        HOOKS_WHY="this pager has no hooks verb yet"
        return 0
    fi
    { err=$("$mail_pager" "${HOOKS_ARGV[@]}" 2>&1 1>&3 3>&-); } 3>&1 </dev/null
    rc=$?
    if ((rc == 0)); then
        HOOKS_LEFT=no HOOKS_WHY=""
        return 0
    fi
    err=${err%%$'\n'*}
    HOOKS_WHY="pager ${HOOKS_ARGV[*]} refused (exit $rc)${err:+: $err}"
    return 0
}

step_label() {
    case "$1" in
        homebrew) say "🍺|Homebrew|installing (it asks for your password)|1. Prerequisites" ;;
        brewpath) say "🍺|Homebrew on your PATH|adding the line|1. Prerequisites" ;;
        uv) say "🐍|uv|installing|1. Prerequisites" ;;
        claude) say "🤖|Claude Code|installing|1. Prerequisites" ;;
        brewset) say "🍻|$(join_and "${MISSING_SET[@]}")|installing|1. Prerequisites" ;;
        kit) say "📦|Session Kit|installing|2. Install the kit" ;;
        plugins) say "🧩|the plugins|installing|3. Install the plugins" ;;
        ears) say "🎙️|ears install|fetching the model|2. Install the kit" ;;
        speech) say "👂|the speech server and the ears|installing|5. Hearing and speaking" ;;
        setup) say "⚙️|sessionkit setup|running|2. Install the kit" ;;
        hooks) say "📬|the mail hooks|turning on|4. First checks" ;;
    esac
}

run_step() {
    local step=$1 label icon name doing section start rc
    label=$(step_label "$step")
    IFS='|' read -r icon name doing section <<<"$label"
    say "$icon $name: ${doing}…"
    start=$SECONDS
    "install_$step"
    rc=$?
    if [[ "$step" == hooks && "$HOOKS_LEFT" == yes ]]; then
        say "$icon $name: $(missing "left for you"): $HOOKS_WHY ($(duration $((SECONDS - start))))"
        return 0
    fi
    if ((rc == 0)); then
        say "$icon $name: $(found "done") ($(duration $((SECONDS - start))))"
        return 0
    fi
    if [[ "$step" == setup ]] && ((rc == SETUP_STEPS_LEFT)); then
        SETUP_LEFT=yes
        say "$icon $name: $(found "done"), $(missing "mail steps left for you") ($(duration $((SECONDS - start))))"
        return 0
    fi
    if [[ "$step" == setup ]]; then
        setup_failed "$rc"
    else
        say ""
        say "🛑 ${RED}$name failed (exit $rc).${RESET} Nothing after it was installed."
        say "What was installed stays: run this again and it picks up from here."
        say "To do this step by hand, see INSTALL.md section $section, at:"
        say "    $REPO_URL"
    fi
    return "$EXIT_FAILED"
}

# Setup fails loudly: whatever it left is named, and there is no success screen.
# Its exit 4 is not a failure: run_step takes it, and the end screen names the steps.
setup_failed() {
    say ""
    say "🛑 ${RED}sessionkit setup did not finish (exit $1). Session Kit is not ready yet.${RESET}"
    say "What its dry run says is left:"
    sessionkit setup --dry-run </dev/null 2>&1 | sed 's/^/    /'
    say "Fix what it names, then run this again; it picks up from here. Step by step, INSTALL.md section 2, at:"
    say "    $REPO_URL"
}

install_all() {
    # A tool found under ~/.local/bin but off the PATH: uv's installer will not
    # run, so the folder joins this run's PATH now.
    if ! has_step uv && ! on_path "$HOME/.local/bin" && [[ -d "$HOME/.local/bin" ]]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
    # Homebrew on disk but off the PATH: this run needs it either way.
    if [[ "$BREW_STATE" == offpath ]] && ! has_step brewpath; then
        eval "$("$BREW" shellenv)"
    fi
    local s
    SETUP_LEFT=no
    say ""
    for s in "${STEPS[@]}"; do
        run_step "$s" || return "$EXIT_FAILED"
    done
    return 0
}

# --- Endings ------------------------------------------------------------------

end_screen() {
    say ""
    say "✅ ${BOLD}Session Kit is installed.${RESET}"
    say ""
    say "Left for you:"
    say "- Open a new terminal, so the new commands are on your PATH."
    say "- Start Claude Code once and sign in with /login:"
    say "    claude"
    say "- Quit Claude Code, every window, before your first session: plugins load at start."
    say "- Then start your first session in a project folder:"
    say "    mkdir -p ~/work && cd ~/work"
    say "    session start"
    if [[ "$SPEECH" == no && "$SPEECH_HERE" == no ]]; then
        say "- To hear you and take phone calls, install the speech server and the ears (about 4.1 GB):"
        say "    ears ${SPEECH_ARGV[*]}"
    fi
    if [[ "$SETUP_LEFT" == yes ]]; then
        say "- sessionkit setup set you as operator and left mail steps for you. Its dry run names them:"
        sessionkit setup --dry-run </dev/null 2>&1 | sed 's/^/    /'
        say "  Do them, then run it again; it keeps the operator it wrote (INSTALL.md section 2):"
        say "    sessionkit setup"
    fi
    if [[ "$HOOKS_LEFT" == yes ]]; then
        say "- Turn the mail hooks on, so a seat hears mail while idle ($HOOKS_WHY):"
        print_hooks_by_hand
    fi
    if [[ -n "$PORT_HOLDER" ]]; then
        say "- Port $SPEECH_PORT was held by $PORT_HOLDER before this ran. Check what serves it:"
        say "    ears services status"
    fi
}

nothing_to_do() {
    say "✅ ${BOLD}Nothing to install: Session Kit is all here.${RESET}"
    say "To upgrade the kit:"
    say "    uv tool upgrade sessionkit"
    if [[ "$SPEECH" == no && "$SPEECH_HERE" == no ]]; then
        print_speech_later
    fi
    if [[ "$HOOKS_LEFT" == yes ]]; then
        say "The mail hooks were not checked ($HOOKS_WHY). If they are not on yet, so a seat hears mail while idle:"
        print_hooks_by_hand
    fi
}

# The hooks by hand: the doctor's own remedy, word for word.
print_hooks_by_hand() {
    say "    $HOOKS_BY_HAND"
    say "  The README's Installation, \"The mail hooks start off\", has the lines to paste."
}

front() {
    say "✨ ${BOLD}Let's install Session Kit!${RESET} ✨"
    say ""
    say "This is the fast track. It checks this Mac, lists what it will install, and"
    say "asks you before it installs anything. To run it without the question:"
    say "    curl -fsSL $SCRIPT_URL | bash -s -- --yes"
    say "To do it step by step instead, by hand: INSTALL.md, at $REPO_URL"
    say "Press [Ctrl-C] at any time to stop."
    say ""
}

on_interrupt() {
    say ""
    if [[ "$CHECK" == yes ]]; then
        say "🛑 Stopped. Nothing was installed."
    else
        say "🛑 Stopped. What was installed stays: run this again and it picks up from there."
    fi
    exit 130
}

# --- --check: the doctor --------------------------------------------------------

check_front() {
    say "🩺 ${BOLD}Checking this Mac (read-only): nothing is installed${RESET}"
    say ""
}

# The verdict. It skips print_list, confirm and install_all, and never reads
# /dev/tty: under `curl | bash -s -- --check` there may be no terminal at all.
check_end() {
    plan
    if ((${#STEPS[@]})); then
        warnings
    else
        warn_intel
    fi
    if ((${#STEPS[@]} == 0)) && [[ "$SERVER_MISSING" != yes ]]; then
        say "✅ ${BOLD}Nothing is missing: Session Kit is all here.${RESET}"
        if [[ "$SPEECH" == no && "$SPEECH_HERE" == no ]]; then
            print_speech_later
        fi
        return "$EXIT_OK"
    fi
    if ((MISSING_ROWS == 1)); then
        say "🩺 ${BOLD}1 row above is missing:${RESET} the → line under it says what to run."
    else
        say "🩺 ${BOLD}$MISSING_ROWS rows above are missing:${RESET} the → lines under each say what to run."
    fi
    if ((${#STEPS[@]})); then
        say "Or let the installer add them, in order, after one question:"
        say "    curl -fsSL $SCRIPT_URL | bash"
    fi
    return "$EXIT_MISSING"
}

main() {
    parse_args "$@"
    setup_colors
    trap on_interrupt INT
    if [[ "$CHECK" == yes ]]; then
        check_front
        refuse_early
        check_all
        check_end
        exit $?
    fi
    front
    refuse_early
    check_all
    plan
    if ((${#STEPS[@]} == 0)); then
        nothing_to_do
        exit "$EXIT_OK"
    fi
    print_list
    [[ "$SPEECH" == no && "$SPEECH_HERE" == no ]] && { print_speech_later; say ""; }
    warnings
    local rc
    if [[ "$DRY_RUN" == yes ]]; then
        refuse_late
        say "🧪 Dry run: nothing was installed."
        exit "$EXIT_OK"
    fi
    refuse_late || exit $?
    confirm
    rc=$?
    ((rc == 0)) || exit "$rc"
    install_all || exit "$EXIT_FAILED"
    end_screen
    exit "$EXIT_OK"
}

main "$@"
