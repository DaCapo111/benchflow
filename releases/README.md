# releases/

This folder is a **local staging area** for release-ready distribution files.

Build scripts copy finished artifacts here automatically:

| File | Created by |
|------|-----------|
| `BenchFlow-v<ver>-macOS.dmg` | `./build_mac.sh` or `python3 build.py` |
| `BenchFlow-v<ver>-Windows.zip` | `build_windows.bat` or `python3 build.py` |

---

## Binary files are NOT committed to git

`.dmg`, `.zip`, and `.exe` files are excluded from version control  
(they are large binaries rebuilt on every release).

Only this `README.md` is tracked.  
Do **not** commit `dist/` either — it is git-ignored.

---

## How releases are published

### Automatic (recommended) — GitHub Actions

Push a version tag:

```bash
# 1. Update the version
echo "0.2.0" > VERSION

# 2. Update CHANGELOG.md

# 3. Commit
git add VERSION CHANGELOG.md
git commit -m "Release v0.2.0"

# 4. Tag and push
git tag v0.2.0
git push origin main
git push origin v0.2.0
```

GitHub Actions will:
1. Build `BenchFlow.app` + `BenchFlow-v0.2.0-macOS.dmg` on macOS
2. Build `BenchFlow.exe` + `BenchFlow-v0.2.0-Windows.zip` on Windows
3. Generate `checksums.txt` (SHA-256 for all assets)
4. Create a **GitHub Release** at `github.com/.../releases/tag/v0.2.0`
5. Attach `.dmg`, `.zip`, and `checksums.txt` as downloadable assets

### Manual upload

1. Build locally:
   ```bash
   ./build_mac.sh         # macOS
   build_windows.bat      # Windows
   ```
2. Files land here in `releases/`.
3. Go to **GitHub → Releases → Draft a new release**.
4. Attach the files.

---

## dist/ is also git-ignored

`dist/mac/` and `dist/windows/` are the raw PyInstaller output directories.  
They should **never** be committed. Use GitHub Releases for distribution.
