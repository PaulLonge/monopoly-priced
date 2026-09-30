"""Monopoly x real London house prices — the pairing Paul called the best one (2026-09-27).

For every street on the London board: the median price paid for a home on the real
street, 2020 to date, from HM Land Registry Price Paid Data (Open Government Licence
v3.0) through its public SPARQL endpoint. The board's own order is its prices, so the
question is whether the real street still agrees with 1935.

Which real street stands for each square is a judgement, stated here:
  The Angel, Islington -> Islington High Street (the Angel is its top end)
  Marlborough Street   -> Great Marlborough Street (the Monopoly square's street)
  Bond Street          -> Old Bond Street + New Bond Street
  Mayfair              -> an area, not a street: every sale in postcode districts W1K
                          and W1J, which are Mayfair
Only standard sales of homes count, on the street in its own postcode districts.
Streets with fewer than MIN_SALES sales stay grey rather than showing a median of three
flats. Stations, utilities and the corners have no value.

    python ingest/monopoly_prices.py
"""
import sys, os, re, json, statistics, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.formats import Measure, DATA

SINCE, MIN_SALES = '2020-01-01', 8
ENDPOINT = 'https://landregistry.data.gov.uk/landregistry/query'
# (real street names, the postcode districts the Monopoly street is actually in). The
# first run had no postcode filter and found the wrong Park Lane (N17, 380,000) and the
# wrong Oxford Street: London has several of each.
STREETS = {
    's01': (['OLD KENT ROAD'], ['SE1', 'SE15']), 's03': (['WHITECHAPEL ROAD'], ['E1']),
    's06': (['ISLINGTON HIGH STREET'], ['N1']), 's08': (['EUSTON ROAD'], ['NW1', 'N1']),
    's09': (['PENTONVILLE ROAD'], ['N1']), 's11': (['PALL MALL'], ['SW1Y']),
    's13': (['WHITEHALL'], ['SW1A']), 's14': (['NORTHUMBERLAND AVENUE'], ['WC2N']),
    's16': (['BOW STREET'], ['WC2E']), 's18': (['GREAT MARLBOROUGH STREET'], ['W1F']),
    's19': (['VINE STREET'], ['W1B', 'W1J']), 's21': (['STRAND'], ['WC2R', 'WC2N', 'WC2E']),
    's23': (['FLEET STREET'], ['EC4A', 'EC4Y']), 's24': (['TRAFALGAR SQUARE'], ['WC2N']),
    's26': (['LEICESTER SQUARE'], ['WC2H']), 's27': (['COVENTRY STREET'], ['W1D', 'W1J']),
    's29': (['PICCADILLY'], ['W1J', 'W1V', 'W1B']), 's31': (['REGENT STREET'], ['W1B', 'SW1Y', 'W1S']),
    's32': (['OXFORD STREET'], ['W1C', 'W1D', 'W1G', 'W1W']),
    's34': (['OLD BOND STREET', 'NEW BOND STREET'], ['W1S', 'W1K', 'W1J']),
    's37': (['PARK LANE'], ['W1K', 'W1J']),
}
MAYFAIR = ('s39', ['W1K', 'W1J'])
# Standard (category A) sales of a home only: category B and "other" property types are
# where shop freeholds and bulk sales live — Bond Street came out at 32.8 million.
HOMES = """
      ?tx lrppi:transactionCategory lrppi:standardPricePaidTransaction ; lrppi:propertyType ?pt .
      FILTER (?pt != lrcommon:otherPropertyType)"""
PFX = """PREFIX lrppi: <http://landregistry.data.gov.uk/def/ppi/>
PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""


def sparql(q):
    url = ENDPOINT + '?' + urllib.parse.urlencode({'query': PFX + q, 'output': 'json'})
    req = urllib.request.Request(url, headers={'Accept': 'application/sparql-results+json',
                                               'User-Agent': 'axisless-ingest'})
    rows = json.load(urllib.request.urlopen(req, timeout=300))['results']['bindings']
    return [int(r['price']['value']) for r in rows]


def street(name, districts):
    f = ' || '.join(f'STRSTARTS(?pc, "{p} ")' for p in districts)
    return sparql(f"""SELECT ?tx ?price WHERE {{
      ?addr lrcommon:street "{name}" ; lrcommon:town "LONDON" ; lrcommon:postcode ?pc .
      FILTER ({f})
      ?tx lrppi:propertyAddress ?addr ; lrppi:pricePaid ?price ; lrppi:transactionDate ?d .{HOMES}
      FILTER (?d >= "{SINCE}"^^xsd:date) }}""")


def district(prefixes):
    # A district ("W1K") needs its trailing space or it would also match W1KA; a
    # sector ("SE1 5") already ends where the unit letters begin.
    f = ' || '.join(f'STRSTARTS(?pc, "{p if " " in p else p + " "}")' for p in prefixes)
    return sparql(f"""SELECT ?tx ?price WHERE {{
      ?addr lrcommon:town "LONDON" ; lrcommon:postcode ?pc .
      FILTER ({f})
      ?tx lrppi:propertyAddress ?addr ; lrppi:pricePaid ?price ; lrppi:transactionDate ?d .{HOMES}
      FILTER (?d >= "{SINCE}"^^xsd:date) }}""")


def sector_of(address):
    """'..., SE1 5XG, United Kingdom' -> 'SE1 5' (the postcode sector)."""
    m = re.search(r'\b([A-Z]{1,2}\d[A-Z\d]?) (\d)[A-Z]{2}\b', address)
    return f'{m.group(1)} {m.group(2)}' if m else None


def main():
    """Street-level where the street itself has MIN_SALES home sales; otherwise the
    postcode sector around the square's geocoded point (data/raw/monopoly-places.json).
    Central London's famous streets are mostly shops, offices and landmarks — Leicester
    Square has had no home sold on it since 2020 — so on the street alone only 6 of 22
    squares had a value. Stations get their sector. Mayfair is its two districts."""
    board = {r['name']: r['id'] for r in json.load(open(os.path.join(DATA, 'layouts',
                                                                   'monopoly.json'), encoding='utf-8'))['regions']}
    places = json.load(open(os.path.join(DATA, 'raw', 'monopoly-places.json'), encoding='utf-8'))
    sales, how = {}, {}
    for name, (lat, lon, addr) in places.items():
        sid = board[name]
        ps = []
        if sid in STREETS:
            names, pcs = STREETS[sid]
            ps = [p for n in names for p in street(n, pcs)]
            how[sid] = 'street'
        if sid == MAYFAIR[0]:
            ps, how[sid] = district(MAYFAIR[1]), 'W1K + W1J'
        elif len(ps) < MIN_SALES:
            sec = sector_of(addr)
            ps, how[sid] = district([sec]) if sec else [], f'sector {sec}'
        sales[sid] = ps
    raw = os.path.join(DATA, 'raw', 'monopoly-prices.json')
    json.dump({k: {'how': how[k], 'prices': v} for k, v in sales.items()}, open(raw, 'w'),
              separators=(',', ':'))
    vals = {}
    for sid, ps in sorted(sales.items()):
        ok = len(ps) >= MIN_SALES
        if ok:
            vals[sid] = round(statistics.median(ps) / 1000) * 1000
        print(f'  {sid} {how[sid]:14} {len(ps):5} sales  median {statistics.median(ps) if ps else 0:>12,.0f}'
              f'{"" if ok else "   (too few: grey)"}')
    Measure(id='monopoly-house-price', label='what a home on or near the real street sells for (median)',
            values=vals, unit='', source=f'HM Land Registry Price Paid Data, standard sales of homes '
            f'since {SINCE}, median: on the street itself where it has {MIN_SALES}+ sales, '
            'otherwise its postcode sector (Mayfair: districts W1K and W1J); choices in '
            'ingest/monopoly_prices.py',
            licence='Open Government Licence v3.0 (contains HM Land Registry data, Crown '
                    'copyright and database right)', layout='monopoly').save()
    print(f'{len(vals)} of {len(sales)} squares have a value')


if __name__ == '__main__':
    main()
