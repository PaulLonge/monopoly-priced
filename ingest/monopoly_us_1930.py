"""Atlantic City in 1930, street by street, for the Monopoly page's "was it ever right?" (Paul, 2026-09-30).

Source: IPUMS USA, the 1930 1% and 5% samples together (us1930a + us1930b): about 6% of Atlantic City's households.
Street addresses (STREET) exist only in these samples; IPUMS's full 1930 and 1940 censuses do not carry them. The
extract (CITY = 0370 Atlantic City; STREET, VALUEH, RENT30, OWNERSHP) was made through the IPUMS API with Paul's
account and lives at downloads/ipums (not in the repo: IPUMS's terms forbid redistributing the
microdata). Only street aggregates are written, to data/raw/monopoly-us-1930.json.

Most Atlantic City households rented in 1930, so the measure is the median monthly rent of renting households on
the street (RENT30, dollars), with a street needing MIN renters. Owners' home values are too few to use.

Citation: Steven Ruggles, Sarah Flood, Matthew Sobek, Daniel Backman, Grace Cooper, Julia A. Rivera Drew, Stephanie Richards, Renae Rodgers, Jonathan Schroeder, and Kari C.W. Williams. IPUMS USA: Version 16.0 [dataset].
Minneapolis, MN: IPUMS, 2025. https://doi.org/10.18128/D010.V16.0

    python ingest/monopoly_us_1930.py
"""
import os, sys, csv, gzip, json, statistics, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import monopoly_us as mu

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'downloads', 'ipums', 'usa_00002.csv.gz')
MIN = 5


def street(s):
    s = s.strip().upper().split('&')[0]
    return mu.street(s.replace('AVENUE', 'AVE').replace('SAINT ', 'ST ').replace('PLACE', 'PL'))


def main():
    hh = {}
    for r in csv.DictReader(gzip.open(SRC, 'rt', encoding='utf-8', errors='replace')):
        hh[(r['SAMPLE'], r['SERIAL'])] = r
    by = collections.defaultdict(list)
    for r in hh.values():
        by[street(r['STREET'])].append(r)
    out = {}
    for sid, (name, _, where) in mu.US.items():
        if not where:
            continue
        names = [n.replace('SAINT ', 'ST ') for n in where[1]]
        hs = [r for k, v in by.items() for r in v if any(k == n or k.startswith(n + ' ') for n in names)]
        rent = [int(r['RENT30']) for r in hs if r['OWNERSHP'] == '2' and 0 < int(r['RENT30']) < 9998]
        out[sid] = {'name': name, 'households': len(hs), 'renters': len(rent),
                    'rent': statistics.median(rent) if len(rent) >= MIN else None}
        print(f"  {sid} {name:24} {len(hs):3} households, {len(rent):3} renters  {out[sid]['rent']}")
    json.dump({'_about': 'IPUMS USA 1930 1% + 5% samples, Atlantic City (CITY 0370): per US Monopoly street, households in '
                         'the sample and median monthly rent of renters (5+ renters). Aggregates only. '
                         'Built by ingest/monopoly_us_1930.py.',
               'citation': 'Steven Ruggles, Sarah Flood, Matthew Sobek, Daniel Backman, Grace Cooper, Julia A. Rivera Drew, Stephanie Richards, Renae Rodgers, Jonathan Schroeder, and Kari C.W. Williams. IPUMS USA: Version 16.0 [dataset]. '
                           'Minneapolis, MN: IPUMS, 2025. https://doi.org/10.18128/D010.V16.0',
               'households_in_sample': len(hh), 'min_renters': MIN, 'streets': out},
              open(os.path.join(ROOT, 'data', 'raw', 'monopoly-us-1930.json'), 'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main()
