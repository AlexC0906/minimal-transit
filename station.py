import math

import pygame

from config import BG_COLOR, SHAPE_COLORS, STATION_COLOR, WARNING_COLOR


class Station:
    def __init__(self, x, y, shape="circle", radius=20):
        self.position = (x, y)
        self.shape = shape
        self.radius = radius
        self.waiting_passengers = []

    @property
    def x(self):
        return self.position[0]

    @property
    def y(self):
        return self.position[1]

    def draw(self, surface):
        color = SHAPE_COLORS[self.shape]
        if self.shape == "circle":
            pygame.draw.circle(surface, color, self.position, self.radius)
        elif self.shape == "square":
            square = pygame.Rect(0, 0, self.radius * 2, self.radius * 2)
            square.center = self.position
            pygame.draw.rect(surface, color, square)
        else:
            points = self._triangle_points(self.radius)
            pygame.draw.polygon(surface, color, points)

        if len(self.waiting_passengers) >= 6:
            pygame.draw.circle(surface, WARNING_COLOR, self.position, self.radius + 5, 2)
        self._draw_passengers(surface)
        self._draw_passenger_count(surface)

    def _triangle_points(self, radius):
        x, y = self.position
        return [(x, y - radius), (x - radius, y + radius), (x + radius, y + radius)]

    def _draw_passenger_count(self, surface):
        if not self.waiting_passengers:
            return
        font = pygame.font.Font(None, 20)
        count = font.render(str(len(self.waiting_passengers)), True, STATION_COLOR)
        surface.blit(count, (self.x + self.radius, self.y - self.radius))

    def _draw_passengers(self, surface):
        for index, passenger in enumerate(self.waiting_passengers[:8]):
            angle = index * math.pi / 4
            position = (
                round(self.x + math.cos(angle) * (self.radius + 9)),
                round(self.y + math.sin(angle) * (self.radius + 9)),
            )
            passenger.draw(surface, position)

    def contains(self, mouse_pos):
        distance = math.hypot(self.x - mouse_pos[0], self.y - mouse_pos[1])
        return distance <= self.radius
