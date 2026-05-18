# QWERTY ANSI finger, row, and hand assignment maps.
#
# Finger encoding: 0=LP, 1=LR, 2=LM, 3=LI, 4=LT, 5=RT, 6=RI, 7=RM, 8=RR, 9=RP
# Row encoding:    0=number, 1=top, 2=home, 3=bottom
# Hand encoding:   "L" or "R"
#
# T and B are assigned to the left index finger (LI=3) by convention.
# G and H are assigned to left index (3) and right index (6) respectively.
# Space is excluded (thumb usage is not tracked in this labeler).

LP, LR, LM, LI, LT = 0, 1, 2, 3, 4
RT, RI, RM, RR, RP = 5, 6, 7, 8, 9

FINGER_MAP: dict[str, int] = {
    # Number row
    "`": LP, "~": LP,
    "1": LP, "!": LP,
    "2": LR, "@": LR,
    "3": LM, "#": LM,
    "4": LI, "$": LI,
    "5": LI, "%": LI,
    "6": RI, "^": RI,
    "7": RI, "&": RI,
    "8": RM, "*": RM,
    "9": RR, "(": RR,
    "0": RP, ")": RP,
    "-": RP, "_": RP,
    "=": RP, "+": RP,
    # Top row
    "q": LP, "w": LR, "e": LM, "r": LI, "t": LI,
    "y": RI, "u": RI, "i": RM, "o": RR, "p": RP,
    "[": RP, "{": RP,
    "]": RP, "}": RP,
    "\\": RP, "|": RP,
    # Home row
    "a": LP, "s": LR, "d": LM, "f": LI, "g": LI,
    "h": RI, "j": RI, "k": RM, "l": RR,
    ";": RP, ":": RP,
    "'": RP, '"': RP,
    # Bottom row
    "z": LP, "x": LR, "c": LM, "v": LI, "b": LI,
    "n": RI, "m": RI,
    ",": RM, "<": RM,
    ".": RR, ">": RR,
    "/": RP, "?": RP,
}

ROW_MAP: dict[str, int] = {
    # Number row
    "`": 0, "~": 0,
    "1": 0, "!": 0, "2": 0, "@": 0, "3": 0, "#": 0,
    "4": 0, "$": 0, "5": 0, "%": 0, "6": 0, "^": 0,
    "7": 0, "&": 0, "8": 0, "*": 0, "9": 0, "(": 0,
    "0": 0, ")": 0, "-": 0, "_": 0, "=": 0, "+": 0,
    # Top row
    "q": 1, "w": 1, "e": 1, "r": 1, "t": 1,
    "y": 1, "u": 1, "i": 1, "o": 1, "p": 1,
    "[": 1, "{": 1, "]": 1, "}": 1, "\\": 1, "|": 1,
    # Home row
    "a": 2, "s": 2, "d": 2, "f": 2, "g": 2,
    "h": 2, "j": 2, "k": 2, "l": 2,
    ";": 2, ":": 2, "'": 2, '"': 2,
    # Bottom row
    "z": 3, "x": 3, "c": 3, "v": 3, "b": 3,
    "n": 3, "m": 3, ",": 3, "<": 3,
    ".": 3, ">": 3, "/": 3, "?": 3,
}

HAND_MAP: dict[int, str] = {
    LP: "L", LR: "L", LM: "L", LI: "L", LT: "L",
    RT: "R", RI: "R", RM: "R", RR: "R", RP: "R",
}

# Keys excluded from bigram labeling. Callers should filter these before
# calling label_bigram — they are listed here for reference and validation.
EXCLUDED_KEYS: frozenset[str] = frozenset({
    "shift", "ctrl", "alt", "meta", "tab", "capslock", "escape",
    "backspace", "delete", "enter", "return",
    "arrowup", "arrowdown", "arrowleft", "arrowright",
    "home", "end", "pageup", "pagedown", "insert",
    "f1", "f2", "f3", "f4", "f5", "f6",
    "f7", "f8", "f9", "f10", "f11", "f12",
    " ", "space",
})
