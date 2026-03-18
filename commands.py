import shlex


class CommandProcessor:
    def __init__(self, canvas):
        self.canvas = canvas

    def process(self, text: str):
        # simple tokenizer
        parts = shlex.split(text)
        if not parts:
            return ""
        cmd = parts[0].lower()
        args = parts[1:]
        if cmd in ("line",):
            if len(args) == 4:
                x1, y1, x2, y2 = map(float, args)
                self.canvas.add_line(x1, y1, x2, y2)
                return f"Line added: ({x1},{y1})-({x2},{y2})"
            else:
                return "Usage: line x1 y1 x2 y2"
        if cmd in ("c", "circle"):
            if len(args) == 3:
                cx, cy, r = map(float, args)
                self.canvas.add_circle(cx, cy, r)
                return f"Circle added: center=({cx},{cy}) r={r}"
            else:
                return "Usage: circle cx cy r"
        if cmd in ("clear",):
            self.canvas.clear()
            return "Canvas cleared"
        if cmd in ("help", "?"):
            return "Commands: line x1 y1 x2 y2 | circle cx cy r | clear"
        return f"Unknown command: {cmd}"
