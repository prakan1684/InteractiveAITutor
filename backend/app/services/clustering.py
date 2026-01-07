import math
from typing import List, Dict, Tuple, Optional
from app.mcp_servers.perception.schemas import (
    Box
)


def intersection_over_union(a: Box, b: Box) -> float:
    """
    Compute IOU between two boxes
    IOU = Intersection Area / Union Area
    return 0 if no overlap
    """

    inter_left = max(a.x, b.x)
    inter_right = min(a.right, b.right) 
    inter_top = max(a.y, b.y)
    inter_bottom = min(a.bottom, b.bottom) 

    inter_w = max(0, inter_right - inter_left)
    inter_h = max(0, inter_bottom - inter_top)
    inter_area = inter_w * inter_h

    area_a = a.w * a.h
    area_b = b.w * b.h
    union_area = area_a + area_b - inter_area
    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def should_merge(
    a: Box,
    b: Box,
    iou_threshold: float = 0.5,
    center_factor: float = 0.5
) -> bool:

    #check for overlap
    if intersection_over_union(a, b) >= iou_threshold:
        return True

    #check for center proximity

    cx_a, cy_a = a.center
    cx_b, cy_b = b.center

    dx = abs(cx_a - cx_b)
    dy = abs(cy_a - cy_b)
    dist = math.sqrt(dx**2 + dy**2)
    
    size = max(max(a.w, a.h), max(b.w, b.h))

    if dist < center_factor * size:
        return True

    return False


def rect_gap(a: Box, b: Box) -> float:
    x_gap = max(0.0, b.x - a.right, a.x - b.right)
    y_gap = max(0.0, b.y - a.bottom, a.y - b.bottom)
    return math.sqrt((x_gap * x_gap) + (y_gap * y_gap))


def stroke_to_box(stroke: Dict) -> Box:
    pts = stroke.get("points", []) or []
    if not pts:
        return Box(x=0.0, y=0.0, w=0.0, h=0.0)

    xs: List[float] = []
    ys: List[float] = []
    for p in pts:
        try:
            xs.append(float(p.get("x")))
            ys.append(float(p.get("y")))
        except Exception:
            continue

    if not xs or not ys:
        return Box(x=0.0, y=0.0, w=0.0, h=0.0)

    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    return Box(x=min_x, y=min_y, w=max(0.0, max_x - min_x), h=max(0.0, max_y - min_y))


def _stroke_endpoints(stroke: Dict) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
    pts = stroke.get("points", []) or []
    if len(pts) < 1:
        return None

    p0 = pts[0] or {}
    p1 = pts[-1] or {}
    try:
        a = (float(p0.get("x")), float(p0.get("y")))
        b = (float(p1.get("x")), float(p1.get("y")))
        return a, b
    except Exception:
        return None


def endpoint_distance(a: Dict, b: Dict) -> float:
    ea = _stroke_endpoints(a)
    eb = _stroke_endpoints(b)
    if ea is None or eb is None:
        return float("inf")

    (a0, a1) = ea
    (b0, b1) = eb
    pairs = [(a0, b0), (a0, b1), (a1, b0), (a1, b1)]
    best = float("inf")
    for (p, q) in pairs:
        dx = p[0] - q[0]
        dy = p[1] - q[1]
        d = math.sqrt((dx * dx) + (dy * dy))
        if d < best:
            best = d
    return best


def _stroke_time_window(stroke: Dict, fallback: float) -> Tuple[float, float]:
    start = stroke.get("startedAt", None)
    end = stroke.get("endedAt", None)

    if start is None and end is None:
        return float(fallback), float(fallback)
    if start is None:
        start = end
    if end is None:
        end = start
    try:
        return float(start), float(end)
    except Exception:
        return float(fallback), float(fallback)


def _time_gap_s(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    a_start, a_end = a
    b_start, b_end = b
    return min(abs(a_start - b_end), abs(b_start - a_end))


def should_merge_strokes(
    a_stroke: Dict,
    b_stroke: Dict,
    a_box: Box,
    b_box: Box,
    gap_threshold: float,
    endpoint_threshold: float,
    time_window_s: float,
    seq_window: int,
    a_time: Tuple[float, float],
    b_time: Tuple[float, float],
) -> bool:
    a_seq = a_stroke.get("sequenceIndex", None)
    b_seq = b_stroke.get("sequenceIndex", None)

    if a_seq is not None and b_seq is not None:
        try:
            if abs(int(a_seq) - int(b_seq)) > seq_window:
                return False
        except Exception:
            pass
    else:
        if _time_gap_s(a_time, b_time) > time_window_s:
            return False

    if rect_gap(a_box, b_box) <= gap_threshold:
        return True

    if endpoint_distance(a_stroke, b_stroke) <= endpoint_threshold:
        return True

    return False


def cluster_strokes(
    strokes: List[Dict],
    gap_threshold: float = 0.02,
    endpoint_threshold: float = 0.03,
    time_window_s: float = 0.6,
    seq_window: int = 2,
    max_forward_neighbors: int = 25,
) -> Tuple[List[List[int]], List[Box], List[Box]]:
    n = len(strokes)
    if n == 0:
        return [], [], []

    boxes = [stroke_to_box(s) for s in strokes]
    times = [_stroke_time_window(s, float(i)) for i, s in enumerate(strokes)]

    order = sorted(range(n), key=lambda i: times[i][0])

    adj: List[List[int]] = [[] for _ in range(n)]

    for oi, i in enumerate(order):
        i_end = times[i][1]
        checked = 0
        for oj in range(oi + 1, len(order)):
            j = order[oj]
            if times[j][0] - i_end > time_window_s and strokes[i].get("sequenceIndex", None) is None:
                break
            checked += 1
            if checked > max_forward_neighbors:
                break

            if should_merge_strokes(
                a_stroke=strokes[i],
                b_stroke=strokes[j],
                a_box=boxes[i],
                b_box=boxes[j],
                gap_threshold=gap_threshold,
                endpoint_threshold=endpoint_threshold,
                time_window_s=time_window_s,
                seq_window=seq_window,
                a_time=times[i],
                b_time=times[j],
            ):
                adj[i].append(j)
                adj[j].append(i)

    visited = [False] * n
    clusters: List[List[int]] = []

    for i in range(n):
        if visited[i]:
            continue
        stack = [i]
        visited[i] = True
        comp: List[int] = []
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nxt in adj[cur]:
                if visited[nxt]:
                    continue
                visited[nxt] = True
                stack.append(nxt)
        clusters.append(comp)

    symbol_boxes = [merge_clusters(boxes, indices) for indices in clusters]
    return clusters, symbol_boxes, boxes


def cluster_boxes(
    boxes: List[Box]
) -> List[List[int]]:
    """
    groups boxes into clusters based on IOU and center proximity


    Args:
        boxes (List[Box]): List of boxes to cluster

    Returns:
        List[List[Box]]: List of clusters
    
    Using a graph based approach. Eeach box is a node and edges are added between nodes if they should be merged
    Then, we use connected components to find the clusters

    """

    n = len(boxes)
    visited = [False] * n
    clusters: List[List[int]] = []
    

    def dfs(i: int, current: List[int]):
        visited[i] = True
        current.append(i)
        for j in range(n):
            if not visited[j] and should_merge(boxes[i], boxes[j]):
                dfs(j, current)
    

    for i in range(n):
        if not visited[i]:
            component: List[int] = []
            dfs(i, component)
            clusters.append(component)
    return clusters



def merge_clusters(
    boxes: List[Box],
    indices: List[int]
) -> Box:
    """
    Given a list of indices belonging to one symbol, return a single Box
    that tightly contains all of them.
    """
    xs = [boxes[i].x for i in indices]
    ys = [boxes[i].y for i in indices]
    rights = [boxes[i].right for i in indices]
    bottoms = [boxes[i].bottom for i in indices]

    x_min = min(xs)
    y_min = min(ys)
    x_max = max(rights)
    y_max = max(bottoms)

    return Box(
        x=x_min,
        y=y_min,
        w=x_max - x_min,
        h=y_max - y_min,
    )

def build_symbol_boxes(
    boxes: List[Box],
    clusters: List[List[int]]
) -> List[Box]:
    """
    Given a list of clusters, return a list of symbol boxes.
    """
    return [merge_clusters(boxes, indices) for indices in clusters]