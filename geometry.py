# geometry.py
import math

def cross(ax, ay, bx, by):
    return ax*by - ay*bx

def edges_of(loop):
    return [ (loop[i], loop[(i+1) % len(loop)]) for i in range(len(loop)) ]

def point_distance(a, b):
    return math.hypot(b[0]-a[0], b[1]-a[1])

def area_polygon(poly):
    area = 0.0
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i+1) % len(poly)]
        area += x1*y2 - x2*y1
    return area / 2.0

def is_convex_polygon(poly):
    if len(poly) < 3: return False
    sign = 0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i+1) % n]
        x3, y3 = poly[(i+2) % n]
        z = cross(x2-x1, y2-y1, x3-x2, y3-y2)
        if z != 0:
            if sign == 0:
                sign = 1 if z > 0 else -1
            else:
                if sign == 1 and z < 0: return False
                if sign == -1 and z > 0: return False
    return True

def snap(p, grid_size):
    return (round(p[0]/grid_size)*grid_size, round(p[1]/grid_size)*grid_size)

def snap_to_grid(x, y, grid):
    """
    Arredonda as coordenadas (x, y) para o ponto mais próximo da grade.
    
    Ex: Se grid=10, (53, 67) -> (50, 70)
    """
    # A função round() é usada para arredondar para o múltiplo mais próximo
    # x // grid * grid: Arredonda para baixo (truncado)
    # round(x / grid) * grid: Arredonda para o múltiplo mais próximo.
    
    # Arredondamento para o múltiplo mais próximo de 'grid'
    snapped_x = round(x / grid) * grid
    snapped_y = round(y / grid) * grid
    
    return snapped_x, snapped_y

def normalize_edge(a, b, ndp=3):
    ax = round(a[0], ndp); ay = round(a[1], ndp)
    bx = round(b[0], ndp); by = round(b[1], ndp)

    v1 = (ax, ay)
    v2 = (bx, by)
    
    if v1 < v2:
        return(v1, v2)
    return (v2, v1)

def point_on_segment(pt, a, b, tol=1.0):
    (x, y), (x1, y1), (x2, y2) = pt, a, b
    if min(x1, x2)-tol <= x <= max(x1, x2)+tol and min(y1, y2)-tol <= y <= max(y1, y2)+tol:
        return abs(cross(x2-x1, y2-y1, x-x1, y-y1)) <= tol
    return False

def point_in_poly(pt, poly):
    if len(poly) < 3: return False
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i+1) % n]
        if point_on_segment(pt, (x1,y1), (x2,y2)):
            return True
        if ((y1 > y) != (y2 > y)):
            xinters = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1
            if x < xinters:
                inside = not inside
    return inside

def point_line_distance(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    c1 = vx*wx + vy*wy
    c2 = vx*vx + vy*vy + 1e-9
    t = max(0.0, min(1.0, c1 / c2))
    projx, projy = ax + t*vx, ay + t*vy
    return math.hypot(projx - px, projy - py)

def segments_intersect(a1, a2, b1, b2):
    def orient(p, q, r):
        return cross(q[0]-p[0], q[1]-p[1], r[0]-p[0], r[1]-p[1])
    o1 = orient(a1, a2, b1)
    o2 = orient(a1, a2, b2)
    o3 = orient(b1, b2, a1)
    o4 = orient(b1, b2, a2)
    if (o1 == 0 and point_on_segment(b1, a1, a2)) or \
       (o2 == 0 and point_on_segment(b2, a1, a2)) or \
       (o3 == 0 and point_on_segment(a1, b1, b2)) or \
       (o4 == 0 and point_on_segment(a2, b1, b2)):
        return True
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)

def polys_intersect(polyA, polyB):
    for a1, a2 in edges_of(polyA):
        for b1, b2 in edges_of(polyB):
            if segments_intersect(a1, a2, b1, b2):
                return True
    return False

def almost_colinear(a1, a2, b1, b2, eps=1.0):
    ax, ay = a2[0]-a1[0], a2[1]-a1[1]
    bx, by = b2[0]-b1[0], b2[1]-b1[1]
    crossv = abs(cross(ax, ay, bx, by))
    if crossv > eps * (point_distance(a1,a2)+point_distance(b1,b2)+1.0):
        return False
    return point_line_distance(b1, a1, a2) <= eps and point_line_distance(b2, a1, a2) <= eps

def overlap_on_line(a1, a2, b1, b2, tol=1.5):
    if not almost_colinear(a1, a2, b1, b2, eps=tol):
        return False
    ax = abs(a2[0]-a1[0]); ay = abs(a2[1]-a1[1])
    use_x = ax >= ay
    def proj(p): return p[0] if use_x else p[1]
    minA, maxA = sorted([proj(a1), proj(a2)])
    minB, maxB = sorted([proj(b1), proj(b2)])
    return not (maxA < minB - tol or maxB < minA - tol)

# Funções da BSP (split_segment, split_segments, point_side, segment_length, etc.)
def point_side(p, line):
    (x1, y1), (x2, y2) = line
    (px, py) = p
    return (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)

def point_side_label(p, line, eps=1e-6):
    val = point_side(p, line)
    if val > eps:
        return "front"
    elif val < -eps:
        return "back"
    else:
        return "collinear"

def classify_segment(seg, splitter, eps=1e-6):
    a, b = seg
    sa = point_side(a, splitter)
    sb = point_side(b, splitter)

    if sa > eps and sb > eps:
        return "front"
    if sa < -eps and sb < -eps:
        return "back"
    if abs(sa) <= eps and abs(sb) <= eps:
        return "collinear"
    return "spanning"

def split_segment(seg, splitter, eps=1e-6):
    a, b = seg
    p1, p2 = splitter

    ax, ay = a
    bx, by = b
    x1, y1 = p1
    x2, y2 = p2

    # Vetores
    dx1, dy1 = bx - ax, by - ay
    dx2, dy2 = x2 - x1, y2 - y1

    denom = dx1 * dy2 - dy1 * dx2
    if abs(denom) < eps:
        return [seg]

    # Resolve interseção
    t = ((x1 - ax) * dy2 - (y1 - ay) * dx2) / denom
    if 0 <= t <= 1:
        ix = ax + t * dx1
        iy = ay + t * dy1
        return [(a, (ix, iy)), ((ix, iy), b)]
    else:
        return [seg]

def split_segments(segments, splitter):
    front, back, collinear = [], [], []
    for s in segments:
        cls = classify_segment(s, splitter)
        if cls == "front":
            front.append(s)
        elif cls == "back":
            back.append(s)
        elif cls == "collinear":
            collinear.append(s)
        elif cls == "spanning":
            parts = split_segment(s, splitter)
            for p in parts:
                side = classify_segment(p, splitter)
                if side == "front":
                    front.append(p)
                elif side == "back":
                    back.append(p)
                else:
                    collinear.append(p)
    return front, back, collinear

def segment_length(seg):
    (x1, y1), (x2, y2) = seg
    return math.hypot(x2-x1, y2-y1)

def all_collinear(segments, eps=1e-6):
    if len(segments) < 2:
        return True

    (x1, y1), (x2, y2) = segments[0]
    dx, dy = x2 - x1, y2 - y1

    for (a, b) in segments[1:]:
        dax, day = b[0] - a[0], b[1] - a[1]
        if abs(dx * day - dy * dax) > eps:
            return False
    return True