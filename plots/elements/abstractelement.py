from plots.utils import Direction

class AbstractElement():
    """Functionality shared by both Element and ElementList
    """
    def __init__(self, parent):
        self.parent = parent

    def contains_device_point(self, x, y):
        return self.top_left[0] <= x <= self.bottom_right[0] and \
            self.top_left[1] <= y <= self.bottom_right[1]

    def half_containing(self, x, y):
        x_mid = (self.bottom_right[0] + self.top_left[0])/2
        if x < x_mid:
            return Direction.LEFT
        else:
            return Direction.RIGHT

    @property
    def height(self):
        return self.ascent + self.descent

    def draw(self, ctx, cursor, widget_transform):
        self.top_left = widget_transform.transform_point(
            *ctx.user_to_device(-self.h_spacing, -self.ascent))
        self.bottom_right = widget_transform.transform_point(
            *ctx.user_to_device(self.width + self.h_spacing, self.descent))
