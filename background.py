from pathlib import Path

import pygame
from PIL import Image
import pillow_avif

from config import HEIGHT, WIDTH


class Background:
    def __init__(self):
        assets_path = Path(__file__).parent / "assets"
        image_path = assets_path / "background_metro2.avif"
        try:
            image = pygame.image.load(str(image_path)).convert()
        except pygame.error:
            pil_image = Image.open(image_path).convert("RGB")
            image = pygame.image.fromstring(
                pil_image.tobytes(), pil_image.size, "RGB"
            ).convert()
        self.surface = pygame.transform.smoothscale(image, (WIDTH, HEIGHT))

    def draw(self, surface):
        surface.blit(self.surface, (0, 0))