"""Plan a stable square crop from observed head bounds, without face reshaping."""
import math
from statistics import median
from .production_audit import number
from .storage import WorkflowError


def plan_crop(value):
    width, height = value.get('width'), value.get('height')
    if any(type(n) is not int or n < 2 for n in (width, height)):
        raise WorkflowError('Source width/height must be positive pixel dimensions')
    boxes = value.get('head_bounds')
    if not isinstance(boxes, list) or not boxes:
        raise WorkflowError('Supply observed head_bounds across representative poses')
    for box in boxes:
        if not isinstance(box, list) or len(box) != 4:
            raise WorkflowError('head_bounds requires [x, y, width, height] in source pixels')
        x, y, w, h = (number(n, 'head bound') for n in box)
        if w <= 0 or h <= 0 or x+w > width or y+h > height:
            raise WorkflowError('Head bounds extend beyond source')
    fraction = number(value.get('subject_fraction', .62), 'subject_fraction', .3)
    anchor_y = number(value.get('anchor_y', .44), 'anchor_y', .2)
    if fraction > .85 or anchor_y > .8:
        raise WorkflowError('Crop fraction/anchor would leave insufficient headroom')
    left = min(b[0] for b in boxes); right = max(b[0]+b[2] for b in boxes)
    top = min(b[1] for b in boxes); bottom = max(b[1]+b[3] for b in boxes)
    side = math.ceil(max(right-left, bottom-top) / fraction / 2) * 2
    if side > min(width, height):
        raise WorkflowError('A stable square cannot retain all poses; change framing or use reviewed tracking')
    centers = [b[0]+b[2]/2 for b in boxes]
    cx = median(centers); cy = median(b[1]+b[3]/2 for b in boxes)
    # Clamp within the frame AND the entire observed subject envelope.
    xmin, xmax = max(0, right-side), min(left, width-side)
    ymin, ymax = max(0, bottom-side), min(top, height-side)
    x = max(xmin, min(xmax, cx-side/2)); y = max(ymin, min(ymax, cy-side*anchor_y))
    x, y = round(x), round(y)
    if x > left or y > top or x+side < right or y+side < bottom:
        raise WorkflowError('Pixel rounding would cut a sampled head; enlarge framing')
    output = value.get('output_size', 520)
    if type(output) is not int or output < 2 or output % 2:
        raise WorkflowError('output_size must be a positive even integer')
    drift = (max(centers)-min(centers))/side
    return {'crop': {'x': x, 'y': y, 'width': side, 'height': side},
            'ffmpeg_filter': f'crop={side}:{side}:{x}:{y},scale={output}:{output}:flags=lanczos,setsar=1',
            'head_center_normalized': [(cx-x)/side, (cy-y)/side],
            'horizontal_motion_fraction': round(drift, 4), 'retime': False,
            'warnings': ['Review tracking or a looser crop; large head movement'] if drift > .18 else [],
            'required_next': 'Render the square proxy; compare frame count/fps/duration and inspect poses inside the actual circle'}
