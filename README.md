FTCAD - Minimal AutoCAD-like app (PySide6)

Run:

```bash
python -m pip install -r requirements.txt
python main.py
```

Features implemented (minimal prototype):
- UI layout separated from drawing core
- Menu area, toolbar tabs, canvas area, command input/display, mode toggles
- Command parser supports: `line x1 y1 x2 y2`, `circle cx cy r`, `clear`
- Grid display toggle

Notes:
- This is a starting scaffold. Many CAD features are placeholders.
- Next: implement interactive mouse-based drawing, more commands, layers, modify tools.
