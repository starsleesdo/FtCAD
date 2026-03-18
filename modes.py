class ModeState:
    def __init__(self):
        self.grid = False
        self.snap = True
        self.ortho = False
        self.polar = False
        self.object_snap = True
        self.object_track = False
        self.lineweight = False
        self.dynamic_input = False
        self.quick_properties = False
        self.magnifier = False
        self.symmetry = False

    def set_flag(self, name, value):
        setattr(self, name, bool(value))

    def flag(self, name):
        return bool(getattr(self, name, False))
