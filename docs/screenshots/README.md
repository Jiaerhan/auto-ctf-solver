# Screenshots

This directory contains terminal/web screenshots captured during CTF solve sessions.

## How to Capture

### Terminal Screenshot (Linux with Docker)
```bash
# Inside the ctf-tools Docker container (requires Xvfb + scrot)
docker exec ctf-tools-agent2 bash -c "DISPLAY=:99 scrot /tmp/screenshot.png"
docker cp ctf-tools-agent2:/tmp/screenshot.png docs/screenshots/terminal_solve.png
```

### Terminal Screenshot (Windows)
```powershell
# Use Snipping Tool (Win+Shift+S) or:
# PowerShell screenshot:
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Screen]::AllScreens[0].Bounds | 
  ForEach-Object { (New-Object System.Drawing.Bitmap $_.Width, $_.Height).Save("docs/screenshots/terminal_solve.png") }
```

### Web Screenshot (for Web challenges)
```bash
# Inside the ctf-tools Docker container (requires CutyCapt)
docker exec ctf-tools-agent2 cutycapt --url=http://target:3000 --out=/tmp/web.png
docker cp ctf-tools-agent2:/tmp/web.png docs/screenshots/web_solve.png
```

### Using the built-in ScreenshotManager
```python
from auto_ctf.tools.screenshot import ScreenshotManager
sm = ScreenshotManager()
sm.capture_terminal("solve_step1")
sm.capture_web("http://localhost:3000", "dashboard")
```

## Current Contents

| File | Description |
|---|---|
| `terminal_solve.png` | Terminal output from `ctf-solve solve` demo run |
