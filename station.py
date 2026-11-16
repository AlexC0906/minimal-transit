import math
import random

import pygame

from config import (
    HEIGHT,
    MAX_WAITING_PASSENGERS,
    MUTED_TEXT_COLOR,
    SHAPE_COLORS,
    STATION_FILL,
    STATION_RADIUS,
    WARNING_COLOR,
    WIDTH,
)
from render import blit_centered, draw_ring, shape_sprite, text

SPAWN_ANIMATION_TIME = 0.45
PASSENGER_SPACING = 12
PASSENGERS_PER_ROW = 4
PASSENGER_GAP = 17
# Candidate sides for the waiting passengers, in order of preference.
SIDES = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _ease_out_back(value):
    overshoot = 1.7
    value -= 1
    return 1 + (overshoot + 1) * value ** 3 + overshoot * value ** 2


class Station:
    def __init__(self, x, y, shape="circle", radius=STATION_RADIUS):
        self.position = (x, y)
        self.shape = shape
        self.radius = radius
        self.waiting_passengers = []
        self.age = SPAWN_ANIMATION_TIME
        self.spawn_timer = random.uniform(0.5, 3.0)
        self.was_full = False

    @classmethod
    def spawned(cls, x, y, shape):
        station = cls(x, y, shape)
        station.age = 0.0
        return station

    @property
    def x(self):
        return self.position[0]

    @property
    def y(self):
        return self.position[1]

    def update(self, delta_time):
        self.age += delta_time

    @property
    def crowding(self):
        return len(self.waiting_passengers) / MAX_WAITING_PASSENGERS

    def draw(self, surface, time=0.0, highlighted=False, busy_directions=()):
        appear = min(1.0, self.age / SPAWN_ANIMATION_TIME)
        scale = max(0.05, _ease_out_back(appear))

        if self.crowding >= 0.5:
            pulse = 0.5 + 0.5 * math.sin(time * 8) if self.crowding >= 1 else 1.0
            # Quantised alpha keeps the number of cached ring sprites small.
            color = (*WARNING_COLOR, 120 + round(pulse * 9) * 15)
            draw_ring(
                surface,
                self.position,
                self.radius + 9,
                4,
                self.crowding,
                color,
                track_color=(*WARNING_COLOR, 40),
            )

        outline = SHAPE_COLORS[self.shape]
        shadow = shape_sprite(self.shape, self.radius, (20, 20, 30, 38))
        body = shape_sprite(self.shape, self.radius, STATION_FILL, outline, 5)
        if highlighted:
            glow = shape_sprite(self.shape, self.radius + 6, (*outline, 60))
            if scale != 1:
                glow = pygame.transform.smoothscale_by(glow, scale)
            blit_centered(surface, glow, self.position)
        if scale != 1:
            shadow = pygame.transform.smoothscale_by(shadow, scale)
            body = pygame.transform.smoothscale_by(body, scale)
        blit_centered(surface, shadow, (self.x, self.y + 2))
        blit_centered(surface, body, self.position)

        if appear >= 1:
            self._draw_passengers(surface, busy_directions)

    def _passenger_side(self, busy_directions):
        """Pick the side with no line or endpoint handle running through it."""
        best = None
        for order, (side_x, side_y) in enumerate(SIDES):
            reach_x = self.radius + PASSENGER_GAP + PASSENGERS_PER_ROW * PASSENGER_SPACING
            reach_y = self.radius + PASSENGER_GAP + 2 * PASSENGER_SPACING
            if not 0 < self.x + side_x * reach_x < WIDTH or not 0 < self.y + side_y * reach_y < HEIGHT:
                continue
            clash = max(
                (side_x * direction.x + side_y * direction.y for direction in busy_directions),
                default=-1.0,
            )
            key = (max(clash, 0.5), order)
            if best is None or key < best[0]:
                best = (key, (side_x, side_y))
        return best[1] if best else SIDES[0]

    def _draw_passengers(self, surface, busy_directions=()):
        visible = self.waiting_passengers[:MAX_WAITING_PASSENGERS]
        if not visible:
            return
        side_x, side_y = self._passenger_side(busy_directions)
        rows = (len(visible) + PASSENGERS_PER_ROW - 1) // PASSENGERS_PER_ROW
        for index, passenger in enumerate(visible):
            column, row = index % PASSENGERS_PER_ROW, index // PASSENGERS_PER_ROW
            if side_x:
                position = (
                    self.x + side_x * (self.radius + PASSENGER_GAP + column * PASSENGER_SPACING),
                    self.y + (row - (rows - 1) / 2) * PASSENGER_SPACING,
                )
            else:
                in_row = min(PASSENGERS_PER_ROW, len(visible) - row * PASSENGERS_PER_ROW)
                position = (
                    self.x + (column - (in_row - 1) / 2) * PASSENGER_SPACING,
                    self.y + side_y * (self.radius + PASSENGER_GAP + row * PASSENGER_SPACING),
                )
            passenger.draw(surface, position, 5)
        extra = len(self.waiting_passengers) - len(visible)
        if extra > 0:
            if side_x:
                anchor_x = self.x + side_x * (
                    self.radius + PASSENGER_GAP + PASSENGERS_PER_ROW * PASSENGER_SPACING
                )
                anchor = {"midleft" if side_x > 0 else "midright": (anchor_x, self.y)}
            else:
                anchor_y = self.y + side_y * (self.radius + PASSENGER_GAP + rows * PASSENGER_SPACING)
                anchor = {"midtop" if side_y > 0 else "midbottom": (self.x, anchor_y - side_y * 4)}
            text(surface, f"+{extra}", 13, MUTED_TEXT_COLOR, bold=True, **anchor)

    def contains(self, mouse_pos, padding=4):
        distance = math.hypot(self.x - mouse_pos[0], self.y - mouse_pos[1])
        return distance <= self.radius + padding
