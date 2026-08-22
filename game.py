import random

import pygame

from config import (
    BG_COLOR,
    DRAWING_COLOR,
    FPS,
    HEIGHT,
    MAX_STATIONS,
    MIN_STATION_DISTANCE,
    STATION_MARGIN,
    STATION_SPAWN_INTERVAL,
    WIDTH,
)
from connection import Connection
from station import Station
from traffic import Traffic


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Minimalist Traffic Management")
        self.clock = pygame.time.Clock()

        self.stations = [
            Station(200, 300),
            Station(600, 200),
            Station(450, 450),
        ]
        self.connections = []
        self.traffic = []
        self.spawn_timer = 0.0
        self.station_spawn_timer = 0.0
        self.is_drawing = False
        self.start_station = None
        self.current_mouse_pos = (0, 0)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.start_drawing(event.pos)
            elif event.type == pygame.MOUSEMOTION and self.is_drawing:
                self.current_mouse_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.finish_drawing(event.pos)
        return True

    def start_drawing(self, mouse_pos):
        for station in self.stations:
            if station.contains(mouse_pos):
                self.is_drawing = True
                self.start_station = station
                self.current_mouse_pos = mouse_pos
                return

    def finish_drawing(self, mouse_pos):
        if not self.is_drawing:
            return

        target_station = next(
            (
                station
                for station in self.stations
                if station is not self.start_station and station.contains(mouse_pos)
            ),
            None,
        )
        if target_station and not self.has_connection(self.start_station, target_station):
            self.connections.append(Connection(self.start_station, target_station))

        self.is_drawing = False
        self.start_station = None

    def has_connection(self, first_station, second_station):
        return any(
            connection.contains_pair(first_station, second_station)
            for connection in self.connections
        )

    def update(self, delta_time):
        self.spawn_timer += delta_time
        if self.connections and self.spawn_timer >= 2.0:
            self.spawn_timer = 0.0
            self.traffic.append(Traffic(random.choice(self.connections)))

        self.station_spawn_timer += delta_time
        if (
            self.station_spawn_timer >= STATION_SPAWN_INTERVAL
            and len(self.stations) < MAX_STATIONS
        ):
            self.station_spawn_timer = 0.0
            self.spawn_station()

        for traffic in self.traffic:
            traffic.update(delta_time)
        self.traffic = [traffic for traffic in self.traffic if not traffic.arrived]

    def spawn_station(self):
        for _ in range(30):
            position = (
                random.randint(STATION_MARGIN, WIDTH - STATION_MARGIN),
                random.randint(STATION_MARGIN, HEIGHT - STATION_MARGIN),
            )
            if all(
                pygame.Vector2(position).distance_to(pygame.Vector2(station.position))
                >= MIN_STATION_DISTANCE
                for station in self.stations
            ):
                self.stations.append(Station(*position))
                return True
        return False

    def draw(self):
        self.screen.fill(BG_COLOR)

        for connection in self.connections:
            connection.draw(self.screen)

        if self.is_drawing and self.start_station:
            pygame.draw.line(
                self.screen,
                DRAWING_COLOR,
                self.start_station.position,
                self.current_mouse_pos,
                4,
            )

        for traffic in self.traffic:
            traffic.draw(self.screen)
        for station in self.stations:
            station.draw(self.screen)

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            delta_time = self.clock.tick(FPS) / 1000.0
            self.update(delta_time)
            self.draw()
        pygame.quit()
