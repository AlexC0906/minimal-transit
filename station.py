import math

import pygame

from config import BG_COLOR, STATION_COLOR


class Station:
    def __init__(self, x, y, radius=16):
        self.position = (x, y)
        self.radius = radius

    @property
    def x(self):
        return self.position[0]

    @property
    def y(self):
        return self.position[1]

    def draw(self, surface):
        pygame.draw.circle(surface, STATION_COLOR, self.position, self.radius)
        pygame.draw.circle(surface, BG_COLOR, self.position, self.radius - 4)

    def contains(self, mouse_pos):
        distance = math.hypot(self.x - mouse_pos[0], self.y - mouse_pos[1])
        return distance <= self.radius
