"""Data for axisless.com/monopoly (Paul, 2026-09-29, after the Reddit post): both boards, every street's
real price and where it came from, and London in 1995-97 ("was it ever right?").

London, today: data/raw/monopoly-prices.json (ingest/monopoly_prices.py: the street, or its postcode
sector, since 2020). A square with too few sales there (the greens, Fleet Street, Trafalgar Square...) is
now ESTIMATED from every home sale since 2020 in the postcode districts its street runs through, and
marked as an estimate: most of those streets have almost no homes, so the page hatches them.

London, 1995-97: the same street / sector / district ladder over sales from 1995 to 1997, the first
three years of the Land Registry's records.

Atlantic City: data/raw/monopoly-us-sales.json (ingest/monopoly_us.py).

Writes site/monopoly/data.json.

    python ingest/monopoly_page.py
"""
import os, sys, json, statistics
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.formats import DATA
import monopoly_prices as mp
import monopoly_us as mu

ROOT = os.path.dirname(DATA)
MIN = mp.MIN_SALES
# Board price of every street, both editions share them.
PRICE = {'s01': 60, 's03': 60, 's06': 100, 's08': 100, 's09': 120, 's11': 140, 's13': 140, 's14': 160,
         's16': 180, 's18': 180, 's19': 200, 's21': 220, 's23': 220, 's24': 240, 's26': 260, 's27': 260,
         's29': 280, 's31': 300, 's32': 300, 's34': 320, 's37': 350, 's39': 400}
GROUP = {'s01': 'brown', 's03': 'brown', 's06': 'lightblue', 's08': 'lightblue', 's09': 'lightblue',
         's11': 'pink', 's13': 'pink', 's14': 'pink', 's16': 'orange', 's18': 'orange', 's19': 'orange',
         's21': 'red', 's23': 'red', 's24': 'red', 's26': 'yellow', 's27': 'yellow', 's29': 'yellow',
         's31': 'green', 's32': 'green', 's34': 'green', 's37': 'darkblue', 's39': 'darkblue'}


def query(where, since, until):
    return mp.sparql(f"""SELECT ?tx ?price WHERE {{ {where}
      ?tx lrppi:propertyAddress ?addr ; lrppi:pricePaid ?price ; lrppi:transactionDate ?d .{mp.HOMES}
      FILTER (?d >= "{since}"^^xsd:date && ?d < "{until}"^^xsd:date) }}""")


def on_street(names, districts, since, until):
    f = ' || '.join(f'STRSTARTS(?pc, "{p} ")' for p in districts)
    return [p for n in names for p in query(f'?addr lrcommon:street "{n}" ; lrcommon:town "LONDON" ; '
                                            f'lrcommon:postcode ?pc . FILTER ({f})', since, until)]


def in_area(prefixes, since, until):
    f = ' || '.join(f'STRSTARTS(?pc, "{p if " " in p else p + " "}")' for p in prefixes)
    return query(f'?addr lrcommon:town "LONDON" ; lrcommon:postcode ?pc . FILTER ({f})', since, until)


def ladder(sid, sector, since, until):
    """Street, then postcode sector, then the street's districts (an estimate). Mayfair is its districts."""
    if sid == mp.MAYFAIR[0]:
        return in_area(mp.MAYFAIR[1], since, until), 'district', 'W1K and W1J (Mayfair)'
    names, pcs = mp.STREETS[sid]
    ps = on_street(names, pcs, since, until)
    if len(ps) >= MIN:
        return ps, 'street', 'the street itself'
    if sector:
        ps = in_area([sector], since, until)
        if len(ps) >= MIN:
            return ps, 'sector', f'postcode sector {sector}'
    return in_area(pcs, since, until), 'estimate', 'postcode districts ' + ', '.join(pcs)


def main():
    L = {r['id']: r['name'] for r in json.load(open(os.path.join(DATA, 'layouts', 'monopoly.json'), encoding='utf-8'))['regions']}
    places = json.load(open(os.path.join(DATA, 'raw', 'monopoly-places.json'), encoding='utf-8'))
    sector = {L_id: mp.sector_of(places[name][2]) for L_id, name in L.items() if name in places}
    now = json.load(open(os.path.join(DATA, 'raw', 'monopoly-prices.json'), encoding='utf-8'))
    london = {}
    for sid in PRICE:
        cur = now[sid]['prices']
        how, where = ('street', 'the street itself') if now[sid]['how'] == 'street' else \
                     ('district', 'W1K and W1J (Mayfair)') if sid == 's39' else ('sector', 'postcode ' + now[sid]['how'])
        if len(cur) < MIN:
            cur, how, where = ladder(sid, None, '2020-01-01', '2030-01-01')
            how, where = 'estimate', where
        old, how95, where95 = ladder(sid, sector.get(sid), '1995-01-01', '1998-01-01')
        london[sid] = {'name': L[sid], 'board': PRICE[sid], 'group': GROUP[sid],
                       'median': round(statistics.median(cur), -3) if len(cur) >= MIN else None, 'n': len(cur),
                       'how': how, 'where': where,
                       'median95': round(statistics.median(old), -3) if len(old) >= MIN else None, 'n95': len(old),
                       'how95': how95, 'where95': where95}
        print(f"  {sid} {L[sid][:22]:22} {how:8} {london[sid]['median'] or 0:>11,.0f} ({len(cur)})   1995-97 {how95:8} "
              f"{london[sid]['median95'] or 0:>9,.0f} ({len(old)})")
    us_raw = json.load(open(os.path.join(DATA, 'raw', 'monopoly-us-sales.json'), encoding='utf-8'))['squares']
    us = {}
    for sid in PRICE:
        r = us_raw.get(sid, {'n': 0, 'median': None})
        us[sid] = {'name': mu.US[sid][0], 'board': PRICE[sid], 'group': GROUP[sid], 'n': r['n'],
                   'median': round(r['median'], -3) if r['n'] >= mu.MIN_SALES and r['median'] else None,
                   'how': 'street' if r['n'] >= mu.MIN_SALES else 'none'}
    # Atlantic City in 1930 (ingest/monopoly_us_1930.py): median rent and how many households it rests on.
    y30 = os.path.join(DATA, 'raw', 'monopoly-us-1930.json')
    if os.path.exists(y30):
        r30 = json.load(open(y30, encoding='utf-8'))['streets']
        for sid, v in us.items():
            x = r30.get(sid, {})
            v.update(rent1930=x.get('rent'), renters1930=x.get('renters', 0), hh1930=x.get('households', 0))
    os.makedirs(os.path.join(ROOT, 'site', 'monopoly'), exist_ok=True)
    json.dump({'london': london, 'us': us}, open(os.path.join(ROOT, 'site', 'monopoly', 'data.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('-> site/monopoly/data.json')


if __name__ == '__main__':
    main()
