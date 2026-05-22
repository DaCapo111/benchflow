# releases/

This folder is the local staging area for release-ready distribution files.

Build scripts copy finished artifacts here automatically:

| File | Created by |
|------|-----------|
| `BenchFlow-<version>-mac.dmg` | `build_mac.sh` or `build.py` |
| `BenchFlow-<version>-windows.zip` | `build_windows.bat` or `build.py` |

## Contents are git-ignored

The actual `.dmg` and `.zip` files are excluded from version control
(they are binary, large, and rebuilt on every release).  
Only this README is tracked.

## How to create a GitHub Release

1. **Build locally:**
   ```bash
   # macOS
   ./build_mac.sh

   # Windows
   build_windows.bat
   ```
   Both scripts copy the final file into this folder.

2. **Or let GitHub Actions build it automatically:**
   Push a version tag to trigger an automatic release:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
   The `build.yml` workflow will build for both platforms,
   create a GitHub Release, and attach `.dmg` and `.zip` as assets.

3. **Manual upload:**
   Go to **github.com → Releases → Draft a new release**,
   attach the files from this folder.
