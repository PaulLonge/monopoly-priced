"""Booth's poverty map, annotated with the London Monopoly board (Paul, 2026-09-29: "could you annotate Booth's diagram").

Two panels from the sheets that hold most of the board (6, West Central; 7, the West End), each Monopoly street
pinned at its reading point (ingest/monopoly_booth.py) in its Monopoly colour and labelled with its name, its
board price and Booth's class; and one strip of insets for the five squares on other sheets. Written to
site/monopoly/booth/annotated-*.jpg. The map is LSE Library's scan (public domain).

    python ingest/monopoly_booth_annotate.py
"""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import monopoly_booth as mb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'site', 'monopoly', 'booth')
FONT = os.environ.get('FONT', r'C:\Windows\Fonts\arialbd.ttf')   # any bold TrueType font
GROUP = {'brown': '#8B5A2B', 'lightblue': '#8FC9EA', 'pink': '#D6479B', 'orange': '#F08A24', 'red': '#E03A31',
         'yellow': '#F2C230', 'green': '#2E9E5B', 'darkblue': '#2D4FA1'}
SHORT = {'middle': 'middle class', 'wealthy': 'wealthy', 'mixed': 'mixed', 'uncoloured': 'not classed',
         'comfortable': 'fairly comfortable', 'poor': 'poor', 'very-poor': 'very poor', 'lowest': 'lowest class'}
D = json.load(open(os.path.join(ROOT, 'site', 'monopoly', 'data.json'), encoding='utf-8'))['london']
R = json.load(open(os.path.join(ROOT, 'data', 'raw', 'monopoly-booth.json'), encoding='utf-8'))['streets']
# Where each label sits relative to its pin, in output pixels, so neighbours don't collide.
NUDGE = {'s26': (30, -60), 's27': (-250, -70), 's29': (-150, 40), 's19': (-290, 10), 's31': (-270, -40), 's18': (20, -60),
         's24': (-240, 30), 's14': (30, 30), 's13': (-210, 40), 's21': (30, -40), 's11': (-60, 40), 's16': (30, -40),
         's23': (-120, -60), 's08': (20, -50), 's32': (20, -60), 's34': (30, 0), 's37': (-240, 0), 's39': (30, 20)}


def font(n):
    return ImageFont.truetype(FONT, n)


def pin(dr, x, y, sid, big=True, nudge=None):
    r = D[sid]; b = R[sid]
    col = GROUP[r['group']]
    rad = 13 if big else 11
    dr.ellipse((x - rad - 3, y - rad - 3, x + rad + 3, y + rad + 3), fill='#FFFBF2')
    dr.ellipse((x - rad, y - rad, x + rad, y + rad), fill=col, outline='#2B1A0C', width=3)
    name = r['name'].replace('The Angel, Islington', 'The Angel')
    line1 = f"{name}  £{r['board']}"
    line2 = f"Booth: {SHORT[b['class']]}{' (unclear)' if b['confidence'] == 'unclear' else ''}"
    f1, f2 = font(22 if big else 20), font(17 if big else 16)
    dx, dy = nudge or NUDGE.get(sid, (24, -22))
    w = max(dr.textlength(line1, font=f1), dr.textlength(line2, font=f2)) + 18
    W = dr.im.size[0]
    tx, ty = min(max(8, x + dx), W - w - 8), y + dy          # labels stay inside the frame
    dr.line((x, y, tx + (0 if dx >= 0 else w), ty + 22), fill='#2B1A0C', width=2)
    dr.rounded_rectangle((tx, ty, tx + w, ty + 50), radius=8, fill='#FFFBF2', outline=col, width=3)
    dr.text((tx + 9, ty + 4), line1, font=f1, fill='#2B1A0C')
    dr.text((tx + 9, ty + 28), line2, font=f2, fill='#6A4A22')


def panel(sheet, sids, box, scale, title, out):
    im = mb.sheet(sheet).crop(box)
    im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    top = 70
    canvas = Image.new('RGB', (im.width, im.height + top), '#FAF0DB')
    canvas.paste(im, (0, top))
    dr = ImageDraw.Draw(canvas)
    dr.text((20, 16), title, font=font(30), fill='#2B1A0C')
    for sid in sids:
        x, y = R[sid]['point']
        pin(dr, (x - box[0]) * scale, (y - box[1]) * scale + top, sid)
    canvas.save(os.path.join(OUT, out), quality=84)
    print(out, canvas.size)


def insets(sids, out):
    S, T = 520, 360
    canvas = Image.new('RGB', (S * len(sids) + 20 * (len(sids) - 1), T + 70), '#FAF0DB')
    dr = ImageDraw.Draw(canvas)
    dr.text((10, 14), "Further out, on Booth's other sheets", font=font(28), fill='#2B1A0C')
    for i, sid in enumerate(sids):
        b = R[sid]; x, y = b['point']
        c = mb.sheet(b['sheet']).crop((x - 520, y - 360, x + 520, y + 360)).resize((S, T), Image.LANCZOS)
        X = i * (S + 20)
        canvas.paste(c, (X, 60))
        pin(ImageDraw.Draw(canvas), X + S / 2, 60 + T / 2, sid, big=False, nudge=(-110, 60))
    canvas.save(os.path.join(OUT, out), quality=84)
    print(out, canvas.size)


def main():
    west = [k for k, v in R.items() if v['sheet'] == 6]
    panel(6, west, (700, 2200, 4500, 6100), 0.42,
          "Booth's map, 1898-9: the West End and the Strand, with the Monopoly board pinned on", 'annotated-west-central.jpg')
    panel(7, [k for k, v in R.items() if v['sheet'] == 7], (5200, 1800, 7500, 3700), 0.62,
          "Mayfair, Park Lane, Oxford and Bond Streets", 'annotated-mayfair.jpg')
    insets([k for k, v in R.items() if v['sheet'] in (3, 5, 9)], 'annotated-outer.jpg')


if __name__ == '__main__':
    main()
