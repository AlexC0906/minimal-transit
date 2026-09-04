import pygame

from config import LINE_COLOR, LINE_WIDTH


def draw_smooth_line(surface, color, start, end, width=LINE_WIDTH):
    start_point = pygame.Vector2(start)
    end_point = pygame.Vector2(end)
    direction = end_point - start_point
    if direction.length_squared() == 0:
        return
    normal = direction.normalize().rotate(90)
    for offset in range(-(width // 2), width // 2 + 1):
        shift = normal * offset
        pygame.draw.aaline(surface, color, start_point + shift, end_point + shift)


class Connection:
    def __init__(self, start_station, end_station):
        self.start = start_station
        self.end = end_station

    def draw(self, surface, color=LINE_COLOR):
        draw_smooth_line(surface, color, self.start.position, self.end.position)

    def contains_pair(self, first_station, second_station):
        return (
            self.start is first_station and self.end is second_station
        ) or (
            self.start is second_station and self.end is first_station
        )

    def connects(self, first_station, second_station):
        return self.contains_pair(first_station, second_station)
