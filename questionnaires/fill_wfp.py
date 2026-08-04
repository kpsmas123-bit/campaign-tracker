#!/usr/bin/env python3
"""Fill the CA WFP 2026 questionnaire PDF, leaving every field editable.

The output keeps live AcroForm fields (no flattening) so it can still be edited
in Preview. Appearance streams are generated here rather than relying on
/NeedAppearances, because Preview does not reliably honour that flag.

Page 2's field names are shifted by one -- Acrobat named each box after the
label *below* it -- so page-2 fields are addressed by name via CONTACT/ROLES
with the true meaning noted, not by trusting the name.
"""
import sys
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    NameObject, TextStringObject, DictionaryObject, ArrayObject,
    NumberObject, FloatObject, DecodedStreamObject, BooleanObject,
)

# Adobe Helvetica AFM advance widths (units/1000 em) for the characters that
# actually occur in these answers, so no font library is required.
_W = {}
for _chars, _w in [
    (" !I|lij", 250), ("'`", 200), ('"', 355), ("#$0123456789+<=>?LcksvxyzE", 556),
    ("%", 889), ("&CGOQ", 722), ("()[]{}\\^", 333), ("*", 389), (",.:;/", 278),
    ("-", 333), ("@", 1015), ("ABDHKNRSTUVXYZ", 700), ("FJP", 600), ("M", 833),
    ("W", 944), ("_", 556), ("abdeghnopqu", 556), ("f t r", 300), ("m", 833),
    ("w", 722), ("~", 584), ("—", 1000), ("–", 556),
    ("‘’", 222), ("“”", 333),
]:
    for _ch in _chars:
        _W[_ch] = _w
_W.update({  # exact values where the grouping above is only approximate
    "I": 278, "i": 222, "j": 222, "l": 222, "|": 260, "c": 500, "k": 500,
    "s": 500, "v": 500, "x": 500, "y": 500, "z": 500, "E": 667, "L": 556,
    "A": 667, "B": 667, "D": 722, "H": 722, "K": 667, "N": 722, "R": 722,
    "S": 667, "T": 611, "U": 722, "V": 667, "X": 667, "Y": 667, "Z": 611,
    "F": 611, "J": 500, "P": 667, "f": 278, "t": 278, "r": 333, " ": 278,
    "'": 191, "`": 333, "^": 469, "*": 389,
})


def stringWidth(text, _font, size):
    return sum(_W.get(ch, 556) for ch in text) * size / 1000.0


FONT = "Helvetica"
PAD = 2.5
MIN_SIZE, MAX_SIZE = 6.0, 10.5


def wrap(text, size, width):
    """Word-wrap to `width` points, honouring explicit newlines."""
    lines = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        cur = ""
        for word in para.split(" "):
            trial = f"{cur} {word}".strip()
            if cur and stringWidth(trial, FONT, size) > width:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        lines.append(cur)
    return lines


def fit(text, w, h, multiline):
    """Largest font size (and its wrapped lines) that fits the box."""
    aw, ah = w - 2 * PAD, h - 2 * PAD
    size = MAX_SIZE
    while size >= MIN_SIZE:
        if multiline:
            lines = wrap(text, size, aw)
            if len(lines) * (size * 1.16) <= ah:
                return size, lines, True
        else:
            if stringWidth(text, FONT, size) <= aw:
                return size, [text], True
        size -= 0.25
    # Doesn't fit even at the minimum: caller reports the overflow.
    lines = wrap(text, MIN_SIZE, aw) if multiline else [text]
    return MIN_SIZE, lines, False


def escape(s):
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def appearance(writer, text, w, h, multiline):
    size, lines, ok = fit(text, w, h, multiline)
    leading = size * 1.16
    if multiline:
        y = h - PAD - size
    else:
        y = (h - size * 0.72) / 2  # vertically centre a single line

    ops = ["/Tx BMC", "q", f"1 1 {w - 2:.2f} {h - 2:.2f} re W n",
           "BT", f"/Helv {size:.2f} Tf", "0 g", f"{leading:.2f} TL",
           f"1 0 0 1 {PAD:.2f} {y:.2f} Tm"]
    for i, line in enumerate(lines):
        if i:
            ops.append("T*")
        ops.append(f"({escape(line)}) Tj")
    ops += ["ET", "Q", "EMC"]

    stream = DecodedStreamObject()
    stream.set_data("\n".join(ops).encode("cp1252", "replace"))
    stream[NameObject("/Type")] = NameObject("/XObject")
    stream[NameObject("/Subtype")] = NameObject("/Form")
    stream[NameObject("/FormType")] = NumberObject(1)
    stream[NameObject("/BBox")] = ArrayObject(
        [FloatObject(0), FloatObject(0), FloatObject(w), FloatObject(h)])

    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    font[NameObject("/Encoding")] = NameObject("/WinAnsiEncoding")
    fonts = DictionaryObject()
    fonts[NameObject("/Helv")] = writer._add_object(font)
    res = DictionaryObject()
    res[NameObject("/Font")] = fonts
    stream[NameObject("/Resources")] = res

    return writer._add_object(stream), ok, size


def field_name(obj):
    node = obj
    while node is not None:
        if node.get("/T"):
            return str(node["/T"])
        node = node.get("/Parent")
        node = node.get_object() if node else None
    return None


def fill(src, dst, text_values, button_values):
    reader = PdfReader(src)
    writer = PdfWriter(clone_from=src)  # clone_from preserves all 81 fields

    warnings, filled_text, filled_btn = [], 0, 0
    for page in writer.pages:
        for ref in (page.get("/Annots") or []):
            obj = ref.get_object()
            parent = obj.get("/Parent")
            parent = parent.get_object() if parent else None
            ftype = str(obj.get("/FT") or (parent.get("/FT") if parent else "") or "")
            name = field_name(obj)

            if ftype == "/Tx" and name in text_values:
                value = text_values[name]
                if not value:
                    continue
                x0, y0, x1, y1 = [float(v) for v in obj["/Rect"]]
                w, h = abs(x1 - x0), abs(y1 - y0)
                multiline = bool(int(obj.get("/Ff", 0)) & (1 << 12))
                ap, ok, size = appearance(writer, value, w, h, multiline)
                obj[NameObject("/V")] = TextStringObject(value)
                nap = DictionaryObject()
                nap[NameObject("/N")] = ap
                obj[NameObject("/AP")] = nap
                # Pin the size: the form ships "/Helv 0 Tf" (auto), which makes
                # every viewer re-shrink the text and ignore the layout above.
                obj[NameObject("/DA")] = TextStringObject(f"/Helv {size:.2f} Tf 0 g")
                if not ok:
                    warnings.append(
                        f"OVERFLOW {name}: {len(value)} chars will not all be "
                        f"visible at {size:.2f}pt in a {w:.0f}x{h:.0f}pt box")
                filled_text += 1

            elif ftype == "/Btn":
                states = [k for k in (obj.get("/AP", {}).get("/N", {}) or {})
                          if k != "/Off"]
                if not states:
                    continue
                state = states[0]
                on = button_values.get(state if parent else name) == state
                target = parent if parent else obj
                if on:
                    target[NameObject("/V")] = NameObject(state)
                    obj[NameObject("/AS")] = NameObject(state)
                    filled_btn += 1
                else:
                    obj[NameObject("/AS")] = NameObject("/Off")

    # Mirror onto /AcroForm/Fields: this PDF stores some widgets twice.
    acro = writer._root_object.get("/AcroForm")
    acro = acro.get_object() if acro is not None else None
    if acro is not None:
        # False on purpose: the appearance streams written above are correct,
        # and NeedAppearances would make viewers discard them and auto-shrink.
        # Fields stay editable either way -- viewers rebuild on user edit.
        acro[NameObject("/NeedAppearances")] = BooleanObject(False)

    writer.write(dst)
    return filled_text, filled_btn, warnings, len(reader.pages)


if __name__ == "__main__":
    import answers_wfp as A
    t, b, warns, pages = fill(sys.argv[1], sys.argv[2], A.TEXT, A.BUTTONS)
    print(f"filled {t} text fields, {b} checkboxes across {pages} pages")
    for w in warns:
        print("  !", w)
