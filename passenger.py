import pygame

from config import PASSENGER_COLOR, SHAPE_COLORS


class Passenger:
    def __init__(self, destination_shape):
        self.destination_shape = destination_shape

    def draw(self, surface, position):
        color = SHAPE_COLORS[self.destination_shape]
        x, y = position
        radius = 5
        if self.destination_shape == "circle":
            pygame.draw.circle(surface, color, position, radius)
        elif self.destination_shape == "square":
            square = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
            pygame.draw.rect(surface, color, square)
        else:
            points = [(x, y - radius), (x - radius, y + radius), (x + radius, y + radius)]
            pygame.draw.polygon(surface, color, points)

        pygame.draw.circle(surface, PASSENGER_COLOR, position, 2)