"""Shared drawing helpers: fonts, antialiased shapes, lines and cards."""

import math
from functools import lru_cache

import pygame
from pygame import gfxdraw

SUPERSAMPLE = 3
FONT_NAMES = "segoeui,helveticaneue,helvetica,arial"

_fonts = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont(FONT_NAMES, size, bold=bold)
    return _fonts[key]


def text(surface, value, size, color, bold=False, **anchor):
    rendered = font(size, bold).render(str(value), True, color)
    rect = rendered.get_rect(**anchor)
    surface.blit(rendered, rect)
    return rect


def _shape_polygon(shape, center, radius, inset=0.0):
    x, y = center
    if shape == "triangle":
        outer = radius * 1.25 - inset * 2
        drop = radius * 0.15
        return [
            (
                x + outer * math.cos(math.radians(angle)),
                y + drop + outer * math.sin(math.radians(angle)),
            )
            for angle in (-90, 30, 150)
        ]
    return None


def _draw_shape(surface, shape, center, radius, color, inset=0.0):
    if shape == "circle":
        pygame.draw.circle(surface, color, center, max(1, radius - inset))
    elif shape == "square":
        half = radius * 0.9 - inset
        rect = pygame.Rect(0, 0, half * 2, half * 2)
        rect.center = center
        pygame.draw.rect(surface, color, rect, border_radius=max(0, round(radius * 0.22 - inset)))
    else:
        pygame.draw.polygon(surface, color, _shape_polygon(shape, center, radius, inset))


@lru_cache(maxsize=512)
def shape_sprite(shape, radius, fill, outline=None, outline_width=0):
    """Return an antialiased sprite of a station/passenger shape, centred in its surface."""
    size = math.ceil((radius * 1.4 + outline_width + 3) * 2)
    scale = SUPERSAMPLE
    big = pygame.Surface((size * scale, size * scale), pygame.SRCALPHA)
    center = (size * scale / 2, size * scale / 2)
    if outline:
        _draw_shape(big, shape, center, radius * scale, outline)
        _draw_shape(big, shape, center, radius * scale, fill, outline_width * scale)
    else:
        _draw_shape(big, shape, center, radius * scale, fill)
    return pygame.transform.smoothscale(big, (size, size))


def blit_centered(surface, sprite, center):
    surface.blit(sprite, sprite.get_rect(center=(round(center[0]), round(center[1]))))


def draw_shape(surface, shape, center, radius, fill, outline=None, outline_width=0):
    blit_centered(surface, shape_sprite(shape, radius, fill, outline, outline_width), center)


def _int_points(points):
    return [(round(point[0]), round(point[1])) for point in points]


def draw_disc(surface, color, center, radius):
    x, y, r = round(center[0]), round(center[1]), max(1, round(radius))
    gfxdraw.aacircle(surface, x, y, r, color)
    gfxdraw.filled_circle(surface, x, y, r, color)


def draw_thick_line(surface, color, start, end, width, round_caps=True):
    start = pygame.Vector2(start)
    end = pygame.Vector2(end)
    direction = end - start
    if direction.length_squared() == 0:
        return
    normal = direction.normalize().rotate(90) * (width / 2)
    points = _int_points([start + normal, end + normal, end - normal, start - normal])
    gfxdraw.aapolygon(surface, points, color)
    gfxdraw.filled_polygon(surface, points, color)
    if round_caps:
        draw_disc(surface, color, start, width / 2 - 0.5)
        draw_disc(surface, color, end, width / 2 - 0.5)


def draw_ring(surface, center, radius, width, fraction, color, track_color=None):
    """Draw a progress ring that starts at 12 o'clock and fills clockwise."""
    fraction = round(max(0.0, min(1.0, fraction)) * 64) / 64
    blit_centered(surface, ring_sprite(radius, width, fraction, color, track_color), center)


@lru_cache(maxsize=512)
def ring_sprite(radius, width, fraction, color, track_color=None):
    scale = SUPERSAMPLE
    size = math.ceil(radius + width + 2) * 2
    big = pygame.Surface((size * scale, size * scale), pygame.SRCALPHA)
    middle = size * scale / 2

    def band(start, stop, band_color):
        steps = max(2, int(72 * (stop - start) / math.tau))
        outer, inner = (radius + width / 2) * scale, (radius - width / 2) * scale
        angles = [start + (stop - start) * step / steps for step in range(steps + 1)]
        points = [
            (middle + math.cos(a) * outer, middle + math.sin(a) * outer) for a in angles
        ] + [
            (middle + math.cos(a) * inner, middle + math.sin(a) * inner) for a in reversed(angles)
        ]
        pygame.draw.polygon(big, band_color, points)

    top = -math.pi / 2
    if track_color:
        band(top, top + math.tau, track_color)
    if fraction > 0:
        band(top, top + math.tau * fraction, color)
    return pygame.transform.smoothscale(big, (size, size))


@lru_cache(maxsize=64)
def card_sprite(width, height, radius=14, color=(255, 255, 255, 236), shadow=True):
    scale = SUPERSAMPLE
    margin = 8 if shadow else 0
    big = pygame.Surface(((width + margin * 2) * scale, (height + margin * 2) * scale), pygame.SRCALPHA)
    if shadow:
        for spread, alpha in ((6, 10), (4, 14), (2, 20)):
            rect = pygame.Rect(
                (margin - spread) * scale,
                (margin - spread + 3) * scale,
                (width + spread * 2) * scale,
                (height + spread * 2) * scale,
            )
            pygame.draw.rect(big, (20, 20, 30, alpha), rect, border_radius=(radius + spread) * scale)
    body = pygame.Rect(margin * scale, margin * scale, width * scale, height * scale)
    pygame.draw.rect(big, color, body, border_radius=radius * scale)
    return pygame.transform.smoothscale(big, (width + margin * 2, height + margin * 2)), margin


def draw_card(surface, rect, radius=14, color=(255, 255, 255, 236), shadow=True):
    sprite, margin = card_sprite(rect.width, rect.height, radius, color, shadow)
    surface.blit(sprite, (rect.x - margin, rect.y - margin))
