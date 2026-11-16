"""Geometry helpers for route segments."""

import pygame


def segment_shift(start_station, end_station, offset):
    """Sideways shift used to draw parallel lines on a shared segment.

    The direction is normalised by station identity, so every line sharing the
    segment uses the same side reference regardless of its travel direction.
    """
    if not offset:
        return pygame.Vector2()
    direction = pygame.Vector2(end_station.position) - pygame.Vector2(start_station.position)
    if direction.length_squared() == 0:
        return pygame.Vector2()
    if id(start_station) > id(end_station):
        direction = -direction
    return direction.normalize().rotate(90) * offset


def closest_point_ratio(point, start, end):
    start = pygame.Vector2(start)
    segment = pygame.Vector2(end) - start
    if segment.length_squared() == 0:
        return 0.0
    return max(0.0, min(1.0, (pygame.Vector2(point) - start).dot(segment) / segment.length_squared()))
