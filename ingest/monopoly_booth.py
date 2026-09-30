"""London's Monopoly streets on Charles Booth's poverty map, 1898-99: what the board's streets were like a
generation before the game (Paul, 2026-09-29: "was it ever right?", and "save the methodology").

The Map Descriptive of London Poverty, 1898-9 (12 sheets; LSE Library, Public Domain Mark), downloaded from
booth.lse.ac.uk/learn-more/download-maps to downloads/booth (not in the repo). Booth coloured
each street by the condition of the people living on it, from black (lowest class) to yellow (wealthy).
Streets of offices, clubs, hotels and ministries are left uncoloured.

Method, so anyone can check it:
  1. Each street found on its sheet and a point placed on it, in the scan's own pixels (POINTS below).
  2. The colour of the street's own frontages read by eye from a close-up and recorded in READING, with a
     confidence: 'clear', or 'unclear' where the street is tiny, split between classes, or hard to pick out.
  3. A crop of the scan around the point, marked, saved to site/monopoly/booth/<square>.jpg, so every
     reading can be checked against the map itself.
Tried and dropped: matching pixels automatically to the printed legend. The fine hatching the map is printed
with, and the colour differences between sheets, swamped it: a first version measured the white road
surface, a second counted the dark hatch strokes of unclassified buildings as "very poor".

    python ingest/monopoly_booth.py
"""
import os, sys, json, statistics
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'downloads', 'booth')
OUT = os.path.join(ROOT, 'site', 'monopoly', 'booth')
R = 70
# The readings: (class, confidence, note).
READING = {
    's01': ('middle', 'clear', 'Old Kent Road: a shopping main road, coloured middle class; many streets behind it poor or very poor'),
    's03': ('middle', 'clear', 'Whitechapel Road: a shopping main road, coloured middle class; very poor streets on both sides'),
    's06': ('middle', 'unclear', 'Islington High Street at the Angel: red, a shade toward mixed'),
    's08': ('middle', 'unclear', 'Euston Road: red frontage in parts, stations and uncoloured blocks in others'),
    's09': ('mixed', 'unclear', 'Pentonville Road: the darker "mixed" red, poor streets to the south'),
    's11': ('uncoloured', 'clear', "Pall Mall: gentlemen's clubs, left uncoloured; wealthy houses behind"),
    's13': ('uncoloured', 'clear', 'Whitehall: government offices; only Whitehall Court, a block of flats, is yellow'),
    's14': ('uncoloured', 'clear', 'Northumberland Avenue: hotels, left uncoloured'),
    's16': ('mixed', 'unclear', 'Bow Street: the police court and opera house; the few homes mixed'),
    's18': ('middle', 'clear', 'Great Marlborough Street: red'),
    's19': ('middle', 'unclear', 'Vine Street: a tiny street; its neighbours are red'),
    's21': ('middle', 'clear', 'Strand: red'),
    's23': ('uncoloured', 'clear', "Fleet Street: newspaper offices and the Temple, left uncoloured"),
    's24': ('uncoloured', 'clear', 'Trafalgar Square: no homes'),
    's26': ('middle', 'unclear', 'Leicester Square: red on two sides, theatres uncoloured'),
    's27': ('middle', 'clear', 'Coventry Street: red'),
    's29': ('middle', 'clear', 'Piccadilly: red east of the Albany'),
    's31': ('middle', 'clear', 'Regent Street: red'),
    's32': ('middle', 'clear', 'Oxford Street: red'),
    's34': ('middle', 'clear', 'New and Old Bond Street: red'),
    's37': ('wealthy', 'clear', 'Park Lane: yellow, the top class'),
    's39': ('wealthy', 'clear', 'Mayfair: almost all yellow'),
}
# Booth's classes, lowest to highest, with a point inside each legend swatch on sheet 9.
CLASSES = [('lowest', 'Lowest class. Vicious, semi-criminal', (2684, 5770)),
           ('very-poor', 'Very poor, casual. Chronic want', (3428, 5770)),
           ('poor', 'Poor. 18s. to 21s. a week for a moderate family', (4160, 5770)),
           ('mixed', 'Mixed. Some comfortable, others poor', (4881, 5770)),
           ('comfortable', 'Fairly comfortable. Good ordinary earnings', (5782, 5770)),
           ('middle', 'Middle class. Well-to-do', (6583, 5770)),
           ('wealthy', 'Upper-middle and upper classes. Wealthy', (7193, 5770))]
UNCOLOURED = (9, (5985, 697))          # the map's grey ground: buildings Booth did not classify
PAPER = (246, 220, 186)                # the cream of the paper: roads, squares, parks
INK = (40, 30, 25)                     # printed names and outlines
# square id -> (sheet, (x, y) on the street, what the point is)
POINTS = {
    's01': (9, (5811, 4244), 'Old Kent Road, south of the Bricklayers Arms'),
    's03': (5, (1614, 4067), 'Whitechapel Road, by the London Hospital'),
    's06': (3, (4136, 6095), 'Islington High Street at the Angel'),
    's08': (6, (1767, 2439), 'Euston Road, by Euston Square'),
    's09': (3, (3095, 6211), 'Pentonville Road'),
    's11': (6, (1259, 5800), 'Pall Mall'),
    's13': (6, (2386, 5760), 'Whitehall'),
    's14': (6, (2599, 5562), 'Northumberland Avenue'),
    's16': (6, (2949, 4632), 'Bow Street, Covent Garden'),
    's18': (6, (1151, 4363), 'Great Marlborough Street'),
    's19': (6, (1386, 5123), 'Vine Street, off Piccadilly'),
    's21': (6, (2599, 5257), 'Strand'),
    's23': (6, (4214, 4587), 'Fleet Street'),
    's24': (6, (2294, 5318), 'Trafalgar Square'),
    's26': (6, (2101, 4993), 'Leicester Square'),
    's27': (6, (1921, 5003), 'Coventry Street'),
    's29': (6, (1331, 5233), 'Piccadilly'),
    's31': (6, (1121, 4593), 'Regent Street'),
    's32': (7, (6644, 2159), 'Oxford Street'),
    's34': (7, (6864, 2639), 'New Bond Street'),
    's37': (7, (5898, 3289), 'Park Lane'),
    's39': (7, (6544, 3039), 'Mayfair (Hill Street)'),
}
_cache = {}


def sheet(n):
    if n not in _cache:
        _cache[n] = Image.open(os.path.join(SHEETS, f'sheet{n}.jpg')).convert('RGB')
    return _cache[n]


def colour(n, xy, r=R):
    im = sheet(n)
    px = [im.getpixel((x, y)) for x in range(xy[0] - r, xy[0] + r + 1) for y in range(xy[1] - r, xy[1] + r + 1)]
    return tuple(int(statistics.median(p[k] for p in px)) for k in range(3))


def main():
    os.makedirs(OUT, exist_ok=True)
    order = [k for k, _, _ in CLASSES]
    labels = dict((k, l) for k, l, _ in CLASSES) | {'uncoloured': 'Not classified: offices, clubs, hotels, ministries'}
    out = {}
    for sid, (n, xy, what) in POINTS.items():
        cls, conf, note = READING[sid]
        out[sid] = {'sheet': n, 'point': list(xy), 'what': what, 'class': cls, 'label': labels[cls],
                    'confidence': conf, 'note': note, 'rank': order.index(cls) + 1 if cls in order else None}
        im = sheet(n); S = 420
        crop = im.crop((xy[0] - S, xy[1] - S, xy[0] + S, xy[1] + S)).resize((420, 420), Image.LANCZOS)
        dr = ImageDraw.Draw(crop)
        dr.ellipse((190, 190, 230, 230), outline=(20, 20, 20), width=3)
        dr.ellipse((187, 187, 233, 233), outline=(255, 250, 240), width=2)
        crop.save(os.path.join(OUT, f'{sid}.jpg'), quality=82)
        print(f'  {sid} {what:44} {cls:11} {conf}')
    ref = [(k, l, None) for k, l in labels.items()]
    json.dump({'_about': 'Charles Booth, Map Descriptive of London Poverty 1898-9 (LSE Library, Public Domain Mark): each '
                         'London Monopoly street read by ingest/monopoly_booth.py', 'classes': [[k, l] for k, l, _ in ref],
               'streets': out}, open(os.path.join(ROOT, 'data', 'raw', 'monopoly-booth.json'), 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main()
