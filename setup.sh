#!/bin/bash
# ─── SK GROK IMAGE GEN — Termux Auto-Setup ───────────────────────────────────
echo -e "\033[92m[*] Updating Termux packages...\033[0m"
pkg update -y && pkg upgrade -y

echo -e "\033[92m[*] Installing Python and git...\033[0m"
pkg install -y python git

echo -e "\033[92m[*] Installing Python dependencies...\033[0m"
pip install websockets

echo -e "\033[92m[*] Creating images folder...\033[0m"
mkdir -p ~/images

echo -e "\033[92m[+] Setup complete! Run with: python sk-coder.py\033[0m"
