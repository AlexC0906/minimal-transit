from pathlib import Path

import pygame

from config import BG_COLOR, BG_TINT, HEIGHT, WIDTH

ASSETS_PATH = Path(__file__).parent / "assets"
BACKGROUND_FILES = ("background_metro2.avif", "background_metro.png")


def _load_image(path):
    try:
        return pygame.image.load(str(path)).convert()
    except (pygame.error, FileNotFoundError):
        pass
    try:
        from PIL import Image

        try:
            import pillow_avif  # noqa: F401  (registers the AVIF decoder)
        except ImportError:
            pass
        pil_image = Image.open(path).convert("RGB")
        return pygame.image.fromstring(pil_image.tobytes(), pil_image.size, "RGB").convert()
    except Exception:
        return None


def _fallback_surface():
    """Soft paper gradient with a faint grid, used when no image asset loads."""
    surface = pygame.Surface((WIDTH, HEIGHT))
    top = pygame.Color(*BG_COLOR)
    bottom = pygame.Color(232, 230, 224)
    for y in range(HEIGHT):
        pygame.draw.line(surface, top.lerp(bottom, y / HEIGHT), (0, y), (WIDTH, y))
    grid = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for x in range(0, WIDTH, 40):
        pygame.draw.line(grid, (0, 0, 0, 10), (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, 40):
        pygame.draw.line(grid, (0, 0, 0, 10), (0, y), (WIDTH, y))
    surface.blit(grid, (0, 0))
    return surface


class Background:
    def __init__(self):
        image = None
        for name in BACKGROUND_FILES:
            path = ASSETS_PATH / name
            if path.exists():
                image = _load_image(path)
                if image:
                    break
        if image is None:
            self.surface = _fallback_surface()
            return
        self.surface = pygame.transform.smoothscale(image, (WIDTH, HEIGHT))
        tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        tint.fill(BG_TINT)
        self.surface.blit(tint, (0, 0))

    def draw(self, surface):
        surface.blit(self.surface, (0, 0))
