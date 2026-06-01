#!/usr/bin/env bash
set -e

REPO="https://github.com/gabrielmayer32/whoopxgarmin.git"
INSTALL_DIR="$HOME/whoop-garmin"
APP_PORT=8765
LOG_DIR="$HOME/Library/Logs/whoop-garmin"
DATA_DIR="$HOME/Library/Application Support/whoop-garmin"
LAUNCH_AGENT_APP="$HOME/Library/LaunchAgents/com.gabrielmayer.whoopxgarmin.plist"
LAUNCH_AGENT_UPDATER="$HOME/Library/LaunchAgents/com.gabrielmayer.whoopxgarmin-updater.plist"
DESKTOP_APP="$HOME/Desktop/Whoop x Garmin.app"

echo ""
echo "╔════════════════════════════════════════╗"
echo "║     Whoop x Garmin Dashboard Setup     ║"
echo "╚════════════════════════════════════════╝"
echo ""

# ── Prerequisites ─────────────────────────────────────────────────────────────

if ! command -v git &>/dev/null; then
    echo "ERROR: git is not installed. Please install Xcode Command Line Tools:"
    echo "  xcode-select --install"
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 is not installed. Please install it from https://python.org"
    exit 1
fi

if ! command -v node &>/dev/null; then
    echo "Installing Node.js via Homebrew..."
    if ! command -v brew &>/dev/null; then
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || eval "$(/usr/local/bin/brew shellenv)" 2>/dev/null
    fi
    brew install node
fi

# ── Credentials ───────────────────────────────────────────────────────────────

echo "── Step 1: Garmin credentials ───────────────────────────────────────────"
echo ""
read -p "  Garmin email:    " GARMIN_EMAIL
read -sp "  Garmin password: " GARMIN_PASSWORD
echo ""
echo ""

echo "── Step 2: Whoop API credentials ────────────────────────────────────────"
echo ""
echo "  You need a free Whoop developer app to connect your Whoop account."
echo "  This takes about 2 minutes:"
echo ""
echo "  1. Go to: https://developer.whoop.com"
echo "  2. Sign in with your Whoop account"
echo "  3. Click \"Create New Application\""
echo "  4. Fill in:"
echo "       Name:         Whoop x Garmin Dashboard"
echo "       Redirect URI: http://localhost:${APP_PORT}/whoop/callback"
echo "  5. Copy the Client ID and Client Secret shown after creation"
echo ""
echo "  Once you have them, come back here and paste them below."
echo "  (Leave blank to skip Whoop and use Garmin only)"
echo ""
read -p "  Whoop Client ID:     " WHOOP_CLIENT_ID
if [ -n "$WHOOP_CLIENT_ID" ]; then
    read -sp "  Whoop Client Secret: " WHOOP_CLIENT_SECRET
    echo ""
fi
echo ""

# ── Clone / update repo ───────────────────────────────────────────────────────

mkdir -p "$LOG_DIR" "$DATA_DIR"

if [ -d "$INSTALL_DIR/.git" ]; then
    echo "==> Updating existing installation..."
    git -C "$INSTALL_DIR" pull --ff-only
else
    echo "==> Downloading app..."
    git clone "$REPO" "$INSTALL_DIR"
fi

# ── Write .env ────────────────────────────────────────────────────────────────

cat > "$INSTALL_DIR/.env" <<EOF
GARMIN_EMAIL=$GARMIN_EMAIL
GARMIN_PASSWORD=$GARMIN_PASSWORD
WHOOP_CLIENT_ID=${WHOOP_CLIENT_ID:-}
WHOOP_CLIENT_SECRET=${WHOOP_CLIENT_SECRET:-}
WHOOP_REDIRECT_URI=http://localhost:${APP_PORT}/whoop/callback
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DATABASE_DIR=$DATA_DIR
EOF

# ── Python venv ───────────────────────────────────────────────────────────────

echo "==> Installing Python dependencies..."
cd "$INSTALL_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r backend/requirements.txt

# ── Build frontend ────────────────────────────────────────────────────────────

echo "==> Building frontend..."
cd "$INSTALL_DIR/frontend"
npm install --silent
npm run build

# ── Desktop .app shortcut ─────────────────────────────────────────────────────

mkdir -p "$DESKTOP_APP/Contents/MacOS"
cat > "$DESKTOP_APP/Contents/MacOS/launch" <<'EOF'
#!/usr/bin/env bash
open "http://localhost:8765"
EOF
chmod +x "$DESKTOP_APP/Contents/MacOS/launch"

cat > "$DESKTOP_APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Whoop x Garmin</string>
    <key>CFBundleDisplayName</key>
    <string>Whoop x Garmin</string>
    <key>CFBundleIdentifier</key>
    <string>com.gabrielmayer.whoopxgarmin</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleExecutable</key>
    <string>launch</string>
</dict>
</plist>
EOF

# ── LaunchAgent: app ──────────────────────────────────────────────────────────

cat > "$LAUNCH_AGENT_APP" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gabrielmayer.whoopxgarmin</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/deploy.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/launchagent.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/launchagent.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>$HOME</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# ── LaunchAgent: auto-updater ─────────────────────────────────────────────────

cat > "$INSTALL_DIR/updater.sh" <<'UPDATER'
#!/usr/bin/env bash
set -e

INSTALL_DIR="$HOME/whoop-garmin"
LOG_DIR="$HOME/Library/Logs/whoop-garmin"

cd "$INSTALL_DIR"
LOCAL=$(git rev-parse HEAD)
git fetch origin main --quiet
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "[$(date)] New version detected, updating..." >> "$LOG_DIR/updater.log"
    git pull --ff-only origin main >> "$LOG_DIR/updater.log" 2>&1
    bash deploy.sh >> "$LOG_DIR/updater.log" 2>&1
    echo "[$(date)] Update complete." >> "$LOG_DIR/updater.log"
fi
UPDATER
chmod +x "$INSTALL_DIR/updater.sh"

cat > "$LAUNCH_AGENT_UPDATER" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gabrielmayer.whoopxgarmin-updater</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$INSTALL_DIR/updater.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/updater.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/updater.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>$HOME</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# ── Load LaunchAgents ─────────────────────────────────────────────────────────

launchctl unload "$LAUNCH_AGENT_APP" 2>/dev/null || true
launchctl load "$LAUNCH_AGENT_APP"

launchctl unload "$LAUNCH_AGENT_UPDATER" 2>/dev/null || true
launchctl load "$LAUNCH_AGENT_UPDATER"

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "╔════════════════════════════════════════╗"
echo "║           Setup complete! ✓            ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "  • App is starting at http://localhost:8765"
echo "  • Desktop shortcut: \"Whoop x Garmin\" on your Desktop"
echo "  • App starts automatically when you log in"
echo "  • Updates install automatically every hour"
echo ""
echo "  Double-click the desktop icon to open the dashboard."
echo ""
