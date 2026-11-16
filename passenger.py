from config import SHAPE_COLORS
from render import draw_shape


class Passenger:
    def __init__(self, destination_shape):
        self.destination_shape = destination_shape
        # Station where the passenger plans to change lines (None = ride to destination).
        self.target_station = None
        # Route the passenger was dropped off by, so trains on it do not pick them back up.
        self.last_route = None

    def draw(self, surface, position, size=5, color=None):
        draw_shape(surface, self.destination_shape, position, size, color or SHAPE_COLORS[self.destination_shape])
