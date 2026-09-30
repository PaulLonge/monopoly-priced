"""The internal format. Everything upstream normalises into this; everything
downstream assumes it.

The recurring lesson from the prototypes: the hard part of ingest is not fetching,
it's normalising. Sources disagree on granularity, scope, missing-data convention
and identifiers. Define the format once, write thin adapters into it, and every
filter, scorer and renderer works regardless of origin.
"""
from __future__ import annotations
import json, os, re
from dataclasses import dataclass, field, asdict

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

GEO, GRID, RING, FLOW = 'geo', 'grid', 'ring', 'flow'


@dataclass
class Region:
    id: str
    name: str
    # geo
    rings: list | None = None          # [[ [lon,lat], ... ], ...]
    # grid
    x: int | None = None
    y: int | None = None
    label: str | None = None           # short text drawn in the cell, e.g. "He"
    # ring
    start: float | None = None         # degrees
    end: float | None = None


@dataclass
class Layout:
    id: str
    name: str
    kind: str                          # GEO | GRID | RING
    regions: list
    intrinsic_order: list | None = None   # region ids, in the layout's own order
    note: str = ''
    # Optional axis tick labels for grid layouts: {'cols': [...], 'rows': [...]}.
    # The periodic table doesn't need them — every cell says "Fe". A 366-cell calendar
    # does, or the player cannot find the day being asked about.
    axes: dict | None = None
    # Optional text drawn at fixed layout coordinates, for geo layouts: [{x, y, text}].
    # Not regions — nothing is measured there. The numbers round a dartboard are the
    # first case: a board without them is a pie chart, and the order they run in is half
    # of what a player knows.
    marks: list | None = None
    # Flow layouts only: {'left': [{id, name, glyph?}], 'right': [...], 'heads': [l, r]}. Each
    # region is a ribbon {id, name, a, b} from a left node to a right one.
    nodes: dict | None = None

    def region_ids(self):
        return [r['id'] if isinstance(r, dict) else r.id for r in self.regions]

    def save(self):
        p = os.path.join(DATA, 'layouts', self.id + '.json')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        out = asdict(self) if not isinstance(self.regions[0], dict) else {
            'id': self.id, 'name': self.name, 'kind': self.kind,
            'regions': self.regions, 'intrinsic_order': self.intrinsic_order,
            'note': self.note, 'axes': self.axes, 'marks': self.marks, 'nodes': self.nodes}
        for k in ('axes', 'marks', 'nodes'):
            if out.get(k) is None:
                out.pop(k, None)
        # drop nulls so the files stay readable and small
        out['regions'] = [{k: v for k, v in r.items() if v is not None}
                          if isinstance(r, dict) else
                          {k: v for k, v in asdict(r).items() if v is not None}
                          for r in self.regions]
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(out, f, separators=(',', ':'))
        return p

    @staticmethod
    def load(layout_id):
        with open(os.path.join(DATA, 'layouts', layout_id + '.json'), encoding='utf-8') as f:
            d = json.load(f)
        return Layout(d['id'], d['name'], d['kind'], d['regions'],
                      d.get('intrinsic_order'), d.get('note', ''), d.get('axes'),
                      d.get('marks'), d.get('nodes'))


@dataclass
class Measure:
    id: str
    label: str            # plain English, as shown to the player
    values: dict          # region id -> number
    unit: str = ''
    source: str = ''
    licence: str = ''     # PER MEASURE, never per source
    layout: str = ''
    note: str = ''

    def save(self):
        # House-style wording wins over whatever an ingest script wrote, so re-running
        # one can't bring back a label the wording pass fixed (data/labels.py).
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location('labels', os.path.join(DATA, 'labels.py'))
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            if self.id in mod.LABELS:
                lab, unit = mod.LABELS[self.id]
                self.label = lab
                if unit is not None: self.unit = unit
        except FileNotFoundError:
            pass
        p = os.path.join(DATA, 'series', f'{self.layout}__{self.id}.json')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, separators=(',', ':'))
        return p

    @staticmethod
    def load_all(layout_id=None):
        d = os.path.join(DATA, 'series')
        if not os.path.isdir(d): return []
        out = []
        for fn in sorted(os.listdir(d)):
            if not fn.endswith('.json'): continue
            if layout_id and not fn.startswith(layout_id + '__'): continue
            with open(os.path.join(d, fn), encoding='utf-8') as f:
                out.append(Measure(**json.load(f)))
        return out


def slug(s):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')[:60]
