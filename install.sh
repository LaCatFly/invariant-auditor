#!/usr/bin/env bash
# install.sh — Universal installer for Invariant Auditor
# Supports: Antigravity IDE, Claude Code, Cursor, Windsurf, or custom directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Available skills
SKILLS=(
  "invariant-auditor"
  "recon-triage"
  "transaction-tracer"
  "boundary-sensitivity"
  "poc-engine"
)

TARGET_DIR=""
SELECTED_SKILL=""
USE_SYMLINK=false
AUTO_DETECT=true

print_usage() {
  cat <<EOF
Invariant Auditor Installer

Usage:
  ./install.sh [options]

Options:
  --all                 Install all 5 audit skills (default)
  -s, --skill <name>    Install a specific skill only
  -t, --target <path>   Explicit destination directory for skills
  --agent <agent>       Target specific agent: 'antigravity', 'claude', 'claude-workspace', or 'workspace'
  --claude-md [dir]     Copy CLAUDE.md to target workspace root (default: current directory)
  -l, --link            Create symlinks instead of copying files (for developers)
  -h, --help            Show this help message

Examples:
  ./install.sh                                 # Auto-detects agent and installs all skills
  ./install.sh --skill recon-triage            # Installs only the recon & triage skill
  ./install.sh --agent claude                  # Installs to ~/.claude/skills/
  ./install.sh --agent claude-workspace        # Installs to ./.claude/skills/ and sets CLAUDE.md
  ./install.sh --agent antigravity             # Installs to ~/.gemini/config/skills/
  ./install.sh --target /path/to/.agents/skills
EOF
}

INSTALL_CLAUDE_MD=false
CLAUDE_MD_DEST="$(pwd)"

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      SELECTED_SKILL=""
      shift
      ;;
    -s|--skill)
      SELECTED_SKILL="$2"
      # Normalize legacy skill names
      case "$SELECTED_SKILL" in
        smart-contract-audit|smart-contract-audit-suite)
          SELECTED_SKILL="invariant-auditor"
          ;;
        audit-*)
          SELECTED_SKILL="${SELECTED_SKILL#audit-}"
          ;;
      esac
      shift 2
      ;;
    -t|--target)
      TARGET_DIR="$2"
      AUTO_DETECT=false
      shift 2
      ;;
    --claude-md)
      INSTALL_CLAUDE_MD=true
      if [[ $# -gt 1 && ! "$2" =~ ^- ]]; then
        CLAUDE_MD_DEST="$2"
        shift 2
      else
        shift 1
      fi
      ;;
    --agent)
      AGENT="$2"
      AUTO_DETECT=false
      case "$AGENT" in
        antigravity|agy|gemini)
          TARGET_DIR="$HOME/.gemini/config/skills"
          ;;
        claude|claude-code)
          TARGET_DIR="$HOME/.claude/skills"
          ;;
        claude-workspace)
          TARGET_DIR="$(pwd)/.claude/skills"
          INSTALL_CLAUDE_MD=true
          ;;
        workspace)
          TARGET_DIR="$(pwd)/.agents/skills"
          ;;
        *)
          echo "Unknown agent '$AGENT'. Use 'antigravity', 'claude', 'claude-workspace', or 'workspace'."
          exit 1
          ;;
      esac
      shift 2
      ;;
    -l|--link)
      USE_SYMLINK=true
      shift
      ;;
    -h|--help)
      print_usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      print_usage
      exit 1
      ;;
  esac
done

# Pre-flight environment check
echo "============================================================"
echo "  Invariant Auditor — Installer"
echo "============================================================"

if ! command -v python3 &>/dev/null; then
  echo "[-] Warning: python3 is not found. Bundled analysis scripts require Python 3.8+."
fi

# Auto-detect target directory if not explicitly set
if [[ "$AUTO_DETECT" == true && -z "$TARGET_DIR" ]]; then
  if [[ -d "$HOME/.gemini/config/skills" ]]; then
    TARGET_DIR="$HOME/.gemini/config/skills"
    echo "[*] Detected Antigravity IDE global config: $TARGET_DIR"
  elif [[ -d "$HOME/.claude/skills" ]]; then
    TARGET_DIR="$HOME/.claude/skills"
    echo "[*] Detected Claude Code skills directory: $TARGET_DIR"
  elif [[ -d "$(pwd)/.agents" ]]; then
    TARGET_DIR="$(pwd)/.agents/skills"
    echo "[*] Detected workspace .agents directory: $TARGET_DIR"
  else
    # Default to global Antigravity / Gemini skills directory
    TARGET_DIR="$HOME/.gemini/config/skills"
    echo "[*] Defaulting to Antigravity global skills directory: $TARGET_DIR"
  fi
fi

mkdir -p "$TARGET_DIR"

install_skill() {
  local skill="$1"
  local dest="$TARGET_DIR/$skill"

  if [[ "$skill" == "invariant-auditor" ]]; then
    if [[ -d "$dest" || -L "$dest" ]]; then
      echo "[*] Updating existing: $dest"
      rm -rf "$dest"
    fi
    mkdir -p "$dest"
    if [[ "$USE_SYMLINK" == true ]]; then
      ln -s "$SCRIPT_DIR/SKILL.md" "$dest/SKILL.md"
      ln -s "$SCRIPT_DIR/references" "$dest/references"
      ln -s "$SCRIPT_DIR/scripts" "$dest/scripts"
      echo "[+] Symlinked: invariant-auditor -> $dest"
    else
      cp "$SCRIPT_DIR/SKILL.md" "$dest/SKILL.md"
      cp -R "$SCRIPT_DIR/references" "$dest/references"
      cp -R "$SCRIPT_DIR/scripts" "$dest/scripts"
      echo "[+] Installed: invariant-auditor -> $dest"
    fi
    if [[ -d "$dest/scripts" ]]; then
      chmod +x "$dest"/scripts/*.py 2>/dev/null || true
    fi
    return 0
  fi

  local src="$SCRIPT_DIR/$skill"

  if [[ ! -d "$src" ]]; then
    echo "[-] Error: Skill '$skill' not found in $SCRIPT_DIR"
    return 1
  fi

  if [[ -d "$dest" || -L "$dest" ]]; then
    echo "[*] Updating existing: $dest"
    rm -rf "$dest"
  fi

  if [[ "$USE_SYMLINK" == true ]]; then
    ln -s "$src" "$dest"
    echo "[+] Symlinked: $skill -> $dest"
  else
    cp -R "$src" "$dest"
    echo "[+] Installed: $skill -> $dest"
  fi

  # Ensure scripts are executable
  if [[ -d "$dest/scripts" ]]; then
    chmod +x "$dest"/scripts/*.py 2>/dev/null || true
  fi
}

# Execute installation
if [[ -n "$SELECTED_SKILL" ]]; then
  echo "[*] Installing selected skill: $SELECTED_SKILL"
  install_skill "$SELECTED_SKILL"
else
  echo "[*] Installing all 5 skills for Invariant Auditor..."
  for skill in "${SKILLS[@]}"; do
    install_skill "$skill"
  done
fi

if [[ "$INSTALL_CLAUDE_MD" == true ]]; then
  mkdir -p "$CLAUDE_MD_DEST"
  for directive in CLAUDE.md AGENTS.md GEMINI.md CODEX.md; do
    if [[ "$USE_SYMLINK" == true ]]; then
      ln -sf "$SCRIPT_DIR/$directive" "$CLAUDE_MD_DEST/$directive"
      echo "[+] Symlinked: $directive -> $CLAUDE_MD_DEST/$directive"
    else
      cp -P "$SCRIPT_DIR/$directive" "$CLAUDE_MD_DEST/$directive"
      echo "[+] Copied: $directive -> $CLAUDE_MD_DEST/$directive"
    fi
  done
fi

echo "============================================================"
echo "[✓] Installation complete!"
echo "    Destination: $TARGET_DIR"
if [[ "$INSTALL_CLAUDE_MD" == true ]]; then
  echo "    Directives:  $CLAUDE_MD_DEST/{CLAUDE.md, AGENTS.md, GEMINI.md, CODEX.md}"
fi
echo "    Installed skills are immediately available to your AI agent."
echo "============================================================"
