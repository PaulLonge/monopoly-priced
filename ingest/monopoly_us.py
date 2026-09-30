"""The American Monopoly board (Paul, 2026-09-29: "people have asked for a US version"), priced from real
home sales in Atlantic City, New Jersey, whose streets the original board is named after.

Layout 'monopoly-us': the London board's drawing (data/layouts/monopoly.json) with the US names. The two
editions share their prices, rents and cards square for square, so the board-mechanics measures (landing
chances, hotel income and payback) are copied across unchanged.

Sales: New Jersey's SR1A sales files (NJ Division of Taxation, public records), 2020 to 2026 year to
date, downloaded to downloads/njsales (not in the repo). Atlantic County (01); Atlantic
City (district 02), Margate City (16) and Ventnor City (22). Usable sales only (U-N-TYPE 'U', the
assessor's own judgement that a sale was at market), residential class 2 (houses and condominiums).
Prices are the verified sale price.

Which real street stands for each square is a judgement, stated here:
  every street except Marvin Gardens -> the avenue of that name in Atlantic City ("Pacific 1905", a
      condo unit, is Pacific Avenue; Boardwalk is written BDWK)
  Illinois Avenue  -> Dr Martin Luther King Jr Boulevard, its name since the 1980s
  Marvin Gardens   -> Marven Gardens, a neighbourhood on the Margate-Ventnor line (the board misspelt
                      it): sales on Brunswick and Fredericksburg Avenues in Margate and Ventnor
  St. Charles Place -> no longer exists: it was cleared for a casino hotel
A street needs MIN_SALES sales for a median; the rest are left without one, and the page says why.

    python ingest/monopoly_us.py
"""
import os, sys, re, json, copy, zipfile, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.formats import Measure, DATA

NJ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'downloads', 'njsales')
FILES = ['Sales2020.zip', 'Sales2021.zip', 'Sales2022.zip', 'Sales2023.zip', 'Sales2024.zip', 'Sales2025.zip',
         'YTDSR1A2026.zip']
MIN_SALES = 5
TOWNS = {'02': 'Atlantic City', '16': 'Margate City', '22': 'Ventnor City'}
# square id -> (US name, short label, (districts, normalised street names))
US = {
    's01': ('Mediterranean Avenue', 'Med', ('02', ['MEDITERRANEAN'])), 's03': ('Baltic Avenue', 'Bal', ('02', ['BALTIC'])),
    's05': ('Reading Railroad', 'Rdg', None), 's06': ('Oriental Avenue', 'Ori', ('02', ['ORIENTAL'])),
    's08': ('Vermont Avenue', 'Ver', ('02', ['VERMONT'])), 's09': ('Connecticut Avenue', 'Con', ('02', ['CONNECTICUT'])),
    's11': ('St. Charles Place', 'StC', ('02', ['ST CHARLES', 'SAINT CHARLES'])), 's12': ('Electric Company', 'Elec', None),
    's13': ('States Avenue', 'Sta', ('02', ['STATES'])), 's14': ('Virginia Avenue', 'Vir', ('02', ['VIRGINIA'])),
    's15': ('Pennsylvania Railroad', 'PRR', None), 's16': ('St. James Place', 'StJ', ('02', ['ST JAMES', 'SAINT JAMES'])),
    's18': ('Tennessee Avenue', 'Ten', ('02', ['TENNESSEE'])), 's19': ('New York Avenue', 'NY', ('02', ['NEW YORK'])),
    's21': ('Kentucky Avenue', 'Ken', ('02', ['KENTUCKY'])), 's23': ('Indiana Avenue', 'Ind', ('02', ['INDIANA'])),
    's24': ('Illinois Avenue', 'Ill', ('02', ['ILLINOIS', 'DR MARTIN LUTHER K', 'MARTIN LUTHER KING', 'MLK'])),
    's25': ('B. & O. Railroad', 'B&O', None), 's26': ('Atlantic Avenue', 'Atl', ('02', ['ATLANTIC'])),
    's27': ('Ventnor Avenue', 'Vtr', ('02', ['VENTNOR'])), 's28': ('Water Works', 'Wat', None),
    's29': ('Marvin Gardens', 'MG', ('16 22', ['BRUNSWICK', 'FREDERICKSBURG'])),
    's31': ('Pacific Avenue', 'Pac', ('02', ['PACIFIC'])), 's32': ('North Carolina Avenue', 'NC', ('02', ['NORTH CAROLINA'])),
    's34': ('Pennsylvania Avenue', 'Pen', ('02', ['PENNSYLVANIA'])), 's35': ('Short Line', 'SL', None),
    's37': ('Park Place', 'PkP', ('02', ['PARK PL', 'PARK PLACE'])), 's38': ('Luxury Tax', 'Tax', None),
    's39': ('Boardwalk', 'BW', ('02', ['BDWK', 'BOARDWALK'])),
}
LONDON_TEXT = ['COLLECT £200', 'Old Kent', 'Road', 'Whitechapel', 'Road', 'Income', 'Tax', '💷', "King's Cross", 'Station',
               'The Angel', 'Islington', 'Euston', 'Road', 'Pentonville', 'Road', 'Pall Mall', 'Whitehall', 'Northumber-',
               'land Avenue', 'Marylebone', 'Station', 'Bow', 'Street', 'Marlborough', 'Street', 'Vine', 'Street', 'Strand',
               'Fleet', 'Street', 'Trafalgar', 'Square', 'Fenchurch St', 'Station', 'Leicester', 'Square', 'Coventry',
               'Street', 'Piccadilly', 'Regent', 'Street', 'Oxford', 'Street', 'Bond', 'Street', 'Liverpool St', 'Station',
               'Park Lane', 'Super', 'Tax', '💷', 'Mayfair']
US_TEXT = ['COLLECT $200', 'Mediterr-', 'anean Ave', 'Baltic', 'Avenue', 'Income', 'Tax', '💵', 'Reading', 'Railroad',
           'Oriental', 'Avenue', 'Vermont', 'Avenue', 'Connecticut', 'Avenue', 'St. Charles Pl', 'States Ave', 'Virginia',
           'Avenue', 'Pennsylvania', 'Railroad', 'St. James', 'Place', 'Tennessee', 'Avenue', 'New York', 'Avenue',
           'Kentucky Ave', 'Indiana', 'Avenue', 'Illinois', 'Avenue', 'B. & O.', 'Railroad', 'Atlantic', 'Avenue', 'Ventnor',
           'Avenue', 'Marvin Gdns', 'Pacific', 'Avenue', 'N. Carolina', 'Avenue', 'Pennsyl-', 'vania Ave', 'Short Line',
           'Railroad', 'Park Place', 'Luxury', 'Tax', '💵', 'Boardwalk']
SUF = {'AVE': '', 'AVENUE': '', 'AV': '', 'PL': 'PL', 'PLACE': 'PL', 'BLVD': '', 'TERR': 'TER', 'TER': 'TER'}


def street(loc):
    """'3101 BDWK 1203' -> 'BDWK'; 'S NORTH CAROLINA AVE' -> 'NORTH CAROLINA'; 'PACIFIC 1905' -> 'PACIFIC'."""
    t = loc.replace('#', ' ').split()
    while t and re.search(r'\d', t[0]): t.pop(0)
    while t and (re.search(r'\d', t[-1]) or t[-1] in ('UNIT', 'APT', 'PH')): t.pop()
    if t and t[0] in ('N', 'S', 'NO', 'SO', 'E', 'W'): t.pop(0)
    if t and t[-1] in SUF:
        t[-1] = SUF[t[-1]]
    return ' '.join(x for x in t if x)


def sales():
    f = lambda l, a, b: l[a - 1:b].decode('latin-1').strip()
    out = []
    for name in FILES:
        z = zipfile.ZipFile(os.path.join(NJ, name))
        for l in z.open(z.namelist()[0]).read().splitlines():
            if f(l, 1, 2) != '01' or f(l, 3, 4) not in TOWNS or f(l, 34, 34) != 'U' or f(l, 627, 629) != '2':
                continue
            price = int(f(l, 47, 55) or 0) or int(f(l, 38, 46) or 0)
            if price < 10000:
                continue
            out.append({'d': f(l, 3, 4), 'street': street(f(l, 298, 322)), 'price': price,
                        'date': f(l, 339, 344), 'year_built': int(f(l, 653, 656) or 0), 'sqft': int(f(l, 657, 663) or 0)})
    return out


def main():
    S = sales()
    print(len(S), 'usable residential sales, 2020 to date')
    per = {}
    for sid, (_, _, where) in US.items():
        if not where:
            continue
        ds, names = where[0].split(), where[1]
        ps = [s for s in S if s['d'] in ds and any(s['street'] == n or s['street'].startswith(n + ' ') for n in names)]
        # 'NORTH CAROLINA' must not catch SOUTH CAROLINA, nor 'PARK PL' catch PARK PLACE TERRACE etc.
        per[sid] = ps
    agg = {}
    for sid, ps in per.items():
        prices = [p['price'] for p in ps]
        psf = [p['price'] / p['sqft'] for p in ps if p['sqft'] >= 300]
        yb = [p['year_built'] for p in ps if 1850 <= p['year_built'] <= 2026]
        agg[sid] = {'n': len(ps), 'median': statistics.median(prices) if prices else None,
                    'psf': statistics.median(psf) if len(psf) >= MIN_SALES else None,
                    'year_built': statistics.mean(yb) if len(yb) >= MIN_SALES else None}
        print(f'  {sid} {US[sid][0]:24} {len(ps):4} sales  median {agg[sid]["median"] or 0:>10,.0f}')
    json.dump({'_about': 'NJ SR1A usable residential sales 2020-2026 YTD, Atlantic City / Margate / Ventnor, by US '
                         'Monopoly square. Built by ingest/monopoly_us.py.', 'min_sales': MIN_SALES,
               'squares': {k: {**v, 'name': US[k][0]} for k, v in agg.items()}},
              open(os.path.join(DATA, 'raw', 'monopoly-us-sales.json'), 'w', encoding='utf-8'), indent=1)

    # The layout: London's drawing, American names.
    L = json.load(open(os.path.join(DATA, 'layouts', 'monopoly.json'), encoding='utf-8'))
    U = copy.deepcopy(L)
    U['id'], U['name'] = 'monopoly-us', 'Monopoly board (Atlantic City)'
    U['note'] = '40 squares, classic US edition (Atlantic City). GO bottom-right, play clockwise.'
    for r in U['regions']:
        if r['id'] in US:
            r['name'], r['label'] = US[r['id']][0], US[r['id']][1]
    texts = [m for m in U['marks'] if 'text' in m and m['text'] in set(LONDON_TEXT)]
    assert [m['text'] for m in texts] == LONDON_TEXT, [m['text'] for m in texts]
    for m, t in zip(texts, US_TEXT):
        m['text'] = t
    json.dump(U, open(os.path.join(DATA, 'layouts', 'monopoly-us.json'), 'w', encoding='utf-8'),
              separators=(',', ':'), ensure_ascii=False)
    print('layout -> data/layouts/monopoly-us.json')

    # Board mechanics: the same numbers on both editions.
    for mid in ('monopoly-landing', 'monopoly-hotel-income', 'monopoly-hotel-payback'):
        m = json.load(open(os.path.join(DATA, 'series', f'monopoly__{mid}.json'), encoding='utf-8'))
        Measure(id=mid.replace('monopoly-', 'monopoly-us-'), label=m['label'].replace('£', '$'), values=m['values'],
                unit=(m.get('unit') or '').replace('£', '$'), source=m['source'].replace('UK', 'US'),
                licence=m['licence'], layout='monopoly-us').save()
    src = ('New Jersey Division of Taxation SR1A sales files, 2020 to 2026: usable sales of homes in Atlantic City '
           '(Marvin Gardens: Margate and Ventnor); choices in ingest/monopoly_us.py')
    lic = 'Public record (State of New Jersey)'
    ok = {k: v for k, v in agg.items() if v['n'] >= MIN_SALES}
    for mid, label, unit, vals in [
        ('monopoly-us-house-price', 'median price of a home sold on the real street since 2020', ' dollars',
         {k: int(round(v['median'], -3)) for k, v in ok.items()}),
        ('monopoly-us-price-sqft', 'median price per square foot of a home sold on the real street since 2020', ' dollars',
         {k: round(v['psf'], 1) for k, v in ok.items() if v['psf']}),
        ('monopoly-us-year-built', 'average year the homes sold on the real street were built', '',
         {k: round(v['year_built'], 1) for k, v in ok.items() if v['year_built']}),
    ]:
        Measure(id=mid, label=label, values=vals, unit=unit, source=src, licence=lic, layout='monopoly-us').save()
        s = sorted(vals.items(), key=lambda kv: kv[1])
        print(f'{mid}: {len(vals)} values, {len(vals) - len(set(vals.values()))} ties; low {s[:2]} high {s[-2:]}')


if __name__ == '__main__':
    main()
