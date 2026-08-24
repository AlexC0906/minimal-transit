import pygame

from config import SHAPE_COLORS


class Passenger:
    def __init__(self, destination_shape):
        self.destination_shape = destination_shape
        self.target_shape = destination_shape

    def draw(self, surface, position, size=5):
        color = SHAPE_COLORS[self.destination_shape]
        x, y = position
        radius = size
        if self.destination_shape == "circle":
            pygame.draw.circle(surface, color, position, radius)
        elif self.destination_shape == "square":
            square = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
            pygame.draw.rect(surface, color, square)
        else:
            points = [(x, y - radius), (x - radius, y + radius), (x + radius, y + radius)]
            pygame.draw.polygon(surface, color, points)

