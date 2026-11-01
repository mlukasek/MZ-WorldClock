"""World map rasteriser for the modern look (standard library only).

Reads Natural Earth GeoJSON (public domain, https://www.naturalearthdata.com; files from
https://github.com/nvkelso/natural-earth-vector/tree/master/geojson, kept locally in input/naturalearth/) and
rasterises polygons into a 1-bit mask in an equirectangular projection with a chosen left edge, so the map can
have the Pacific (the period map) or the Atlantic (key M) in the middle.

    from worldmap import Projection, load_polygons, rasterise
    proj = Projection(width=320, height=144, lon_left=-25.0, lat_top=78.0, lat_bottom=-62.0)
    land = rasterise(load_polygons('input/naturalearth/ne_50m_land.geojson'), proj)
"""
import json
import math


class Projection:
    """Equirectangular: x grows with longitude from lon_left (wrapping), y with latitude from lat_top down."""

    def __init__(self, width, height, lon_left, lat_top, lat_bottom):
        self.width, self.height = width, height
        self.lon_left, self.lat_top, self.lat_bottom = lon_left, lat_top, lat_bottom

    def x(self, lon):
        return ((lon - self.lon_left) % 360.0) * self.width / 360.0

    def y(self, lat):
        return (self.lat_top - lat) * self.height / (self.lat_top - self.lat_bottom)

    def lon(self, x):
        """Longitude of the centre of pixel column x (-180..180)."""
        return (self.lon_left + (x + 0.5) * 360.0 / self.width + 180.0) % 360.0 - 180.0

    def lat(self, y):
        return self.lat_top - (y + 0.5) * (self.lat_top - self.lat_bottom) / self.height


def load_polygons(path, keep=None):
    """[(properties, [ring, ...])] where a ring is a list of (lon, lat); keep(properties) filters features."""
    out = []
    for f in json.load(open(path, encoding='utf-8'))['features']:
        if keep and not keep(f['properties']):
            continue
        g = f['geometry']
        polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates'] if g['type'] == 'MultiPolygon' else []
        for p in polys:
            out.append((f['properties'], [[(pt[0], pt[1]) for pt in ring] for ring in p]))
    return out


def rasterise(polygons, proj):
    """1-bit mask (list of rows of 0/1) of the union of the polygons; even-odd per polygon, pixel centres.
    Each polygon is drawn in longitude 'unwrapped' around its own first point and repeated at +-360, so polygons
    crossing the map's edge appear on both sides."""
    w, h = proj.width, proj.height
    mask = [bytearray(w) for _ in range(h)]
    for _, rings in polygons:
        edges = []                                   # (y0, y1, x0, x1) in pixels, unwrapped
        ref = rings[0][0][0]
        for ring in rings:
            pts = []
            prev = None
            for lon, lat in ring:
                if prev is None:
                    lon_u = ref + ((lon - ref + 180.0) % 360.0 - 180.0)
                else:
                    lon_u = prev + ((lon - prev + 180.0) % 360.0 - 180.0)
                prev = lon_u
                pts.append(((lon_u - proj.lon_left) * w / 360.0, proj.y(lat)))
            for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
                if y0 != y1:
                    edges.append((y0, y1, x0, x1))
        if not edges:
            continue
        ymin = max(0, int(math.floor(min(min(e[0], e[1]) for e in edges))))
        ymax = min(h - 1, int(math.ceil(max(max(e[0], e[1]) for e in edges))))
        for y in range(ymin, ymax + 1):
            yc = y + 0.5
            xs = []
            for y0, y1, x0, x1 in edges:
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            row = mask[y]
            for a, b in zip(xs[0::2], xs[1::2]):
                for shift in (-w, 0, w):
                    lo = max(0, int(math.ceil(a + shift - 0.5)))
                    hi = min(w - 1, int(math.floor(b + shift - 0.5)))
                    for x in range(lo, hi + 1):
                        row[x] ^= 1
    # even-odd per polygon was applied with XOR across all polygons; land polygons of Natural Earth do not
    # overlap, so the XOR is their union
    return mask


def sun(utc):
    """Subsolar point (lat, lon) in degrees for a datetime in UTC (NOAA approximations, ~0.1 degree)."""
    d = utc.timetuple().tm_yday
    hours = utc.hour + utc.minute / 60.0 + utc.second / 3600.0
    g = 2.0 * math.pi / 365.0 * (d - 1 + (hours - 12) / 24.0)
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g)
                       - 0.040849 * math.sin(2 * g))
    lon = -15.0 * (hours - 12.0 + eqtime / 60.0)
    return math.degrees(decl), (lon + 180.0) % 360.0 - 180.0


def is_night(lat, lon, sun_lat, sun_lon):
    phi, dec = math.radians(lat), math.radians(sun_lat)
    return math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(math.radians(lon - sun_lon)) < 0
