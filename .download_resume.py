#!/usr/bin/env python3
"""Resume downloading missing files from GitHub."""
import os, json, urllib.request, urllib.parse, subprocess, time

target_dir = "/opt/text-to-cad"
repo = "MountainClimberJiwen/text-to-cad"
base_url = f"https://raw.githubusercontent.com/{repo}/main/"

# Fetch tree
url = f"https://api.github.com/repos/{repo}/git/trees/main?recursive=1"
req = urllib.request.Request(url, headers={"User-Agent": "agentrl"})
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read().decode())

tree = [item for item in data.get("tree", []) if item["type"] == "blob"]
small_files = [(item["path"], item.get("size", 0)) for item in tree if item.get("size", 0) <= 200 * 1024]

missing = []
for path, size in small_files:
    local = os.path.join(target_dir, path)
    if not os.path.exists(local) or os.path.getsize(local) == 0:
        missing.append((path, size))

print(f"Missing files: {len(missing)} / {len(small_files)}")

success = 0
for path, size in missing:
    encoded_path = urllib.parse.quote(path)
    url = base_url + encoded_path
    local_path = os.path.join(target_dir, path)
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "agentrl"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        with open(local_path, "wb") as f:
            f.write(data)
        success += 1
    except Exception as e:
        print(f"  FAIL: {path}: {e}")

print(f"Downloaded: {success}/{len(missing)}")

# Init git if not already
if not os.path.isdir(os.path.join(target_dir, ".git")):
    os.chdir(target_dir)
    subprocess.run(["git", "init"], capture_output=True)
    subprocess.run(["git", "add", "-A"], capture_output=True)
    subprocess.run(["git", "commit", "-m", "init: text-to-cad from GitHub"], capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", f"git@github.com:{repo}.git"], capture_output=True)
    print("Git repo initialized")

print("DONE")
