import pygame

from config import LINE_COLOR


class Connection:
    def __init__(self, start_station, end_station):
        self.start = start_station
        self.end = end_station

    def draw(self, surface, color=LINE_COLOR):
        pygame.draw.line(surface, color, self.start.position, self.end.position, 4)

    def contains_pair(self, first_station, second_station):
        return (
            self.start is first_station and self.end is second_station
        ) or (
            self.start is second_station and self.end is first_station
        )

    def connects(self, first_station, second_station):
        return self.contains_pair(first_station, second_station)
