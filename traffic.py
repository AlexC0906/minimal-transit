import pygame

from config import TRAFFIC_COLOR


class Traffic:
    def __init__(self, connection, speed=180):
        self.connection = connection
        self.progress = 0.0
        self.speed = speed
        self.radius = 7

    @property
    def position(self):
        start_x, start_y = self.connection.start.position
        end_x, end_y = self.connection.end.position
        return (
            start_x + (end_x - start_x) * self.progress,
            start_y + (end_y - start_y) * self.progress,
        )

    def update(self, delta_time):
        start = pygame.Vector2(self.connection.start.position)
        end = pygame.Vector2(self.connection.end.position)
        distance = start.distance_to(end)
        self.progress += self.speed * delta_time / distance

    @property
    def arrived(self):
        return self.progress >= 1.0

    def draw(self, surface):
        pygame.draw.circle(surface, TRAFFIC_COLOR, self.position, self.radius)
