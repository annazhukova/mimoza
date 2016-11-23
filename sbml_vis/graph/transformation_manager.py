__author__ = 'anna'


MARGIN = 16


def transform(dimensions, x_shift, y_shift, scale_factor):
    """
    Transform the given element's layout in the following manner:
        (1) scales the coordinates (x, y) by scale_factor and then shifts them by (x_shift, y_shift)
        in the top left direction;
        (2) scales the (w, h) by scale_factor.
    :param dimensions, ((x, y), (w, h)), coordinates, width and height to be transformed
    :param x_shift, x shift
    :param y_shift, y shift
    :param scale_factor, scale_factor
    :return: transformed layout: (x, y), (w, h).
    """
    ((x, y), (w, h)) = dimensions
    return shift(scale(convert_coordinates((x, y), (w, h)), scale_factor), x_shift, y_shift), scale((w, h),
                                                                                                    scale_factor)


def convert_coordinates(xy, wh):
    """
    Converts coordinates from the Tulip representation: (x, y) -- centre, (w, h) -- width and height
    to SBGN representation (x, y) -- top left corner, (w, h) -- width and height
    :param xy, (x, y), coordinates of the centre
    :param wh, (w, h), width and height
    :return: SBGN-compatible coordinates: (x, y)
    """
    w, h = wh
    return shift(xy, w / 2, h / 2)


def shift(xy, x_shift=0, y_shift=0):
    """
    Shifts coordinates (x, y) by (x_shift, y_shift) in the top left direction.
    :param xy, (x, y), coordinates
    :param x_shift, x shift
    :param y_shift, y shift
    :return: shifted coordinates: (x, y)
    """
    x, y = xy
    return x - x_shift, y - y_shift


def scale(xy, scale_factor=1):
    """
    Scales coordinates (x, y) by scale_factor.
    :param xy, (x, y), coordinates
    :param scale_factor, the scale_factor
    :return: scaled coordinates: (x, y)
    """
    x, y = xy
    return x * scale_factor, y * scale_factor


def get_layout_characteristics(n2lo):
    """
    Checks the layout values for all the elements and finds the coordinates of the top left corner,
    the width and the height or the area containing the graph and the height of the minimal element.
    :param n2lo: node layout as a dictionary    {node_id: ((x, y), (w, h)) if node is not ubiquitous
                                                else node_id : {r_ids: ((x, y), (w, h)) for r_ids of
                                                reactions using each duplicated metabolite}}
    :return: h_min, (x_min, y_min), (w, h): the height of the minimal element, the coordinates of the top left corner,
                                            the width and the height or the area containing the graph.
    """
    x_min, y_min, x_max, y_max, h_min = None, None, None, None, None
    for v in n2lo.values():
        if not isinstance(v, dict):
            v = {'': v}
        for ((x, y), (w, h)) in v.values():
            if x_min is None or x - w / 2 < x_min:
                x_min = x - w / 2
            if x_max is None or x + w / 2 > x_max:
                x_max = x + w / 2
            if y_min is None or y - h / 2 < y_min:
                y_min = y - h / 2
            if y_max is None or y + h / 2 > y_max:
                y_max = y + h / 2
            if h_min is None or h < h_min:
                h_min = h
    w, h = x_max - x_min, y_max - y_min
    return h_min, (x_min, y_min), (w, h)