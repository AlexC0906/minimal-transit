import random
from collections import deque

import pygame

from config import (
    BG_COLOR,
    DRAWING_COLOR,
    FPS,
    HEIGHT,
    LINE_COLORS,
    MAX_LINES,
    MAX_STATIONS,
    MAX_MISSED_PASSENGERS,
    MAX_WAITING_PASSENGERS,
    MIN_STATION_DISTANCE,
    PASSENGER_SPAWN_INTERVAL,
    STATION_MARGIN,
    STATION_SPAWN_INTERVAL,
    TRAIN_CREDIT_INTERVAL,
    WIDTH,
)
from background import Background
from line import MetroLine
from passenger import Passenger
from station import Station


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Minimalist Traffic Management")
        self.clock = pygame.time.Clock()
        self.background = Background()

        self.stations = [
            Station(200, 300, "circle"),
            Station(600, 200, "square"),
            Station(450, 450, "triangle"),
        ]
        self.lines = []
        self.score = 0
        self.missed_passengers = 0
        self.game_over = False
        self.passenger_spawn_timer = 0.0
        self.station_spawn_timer = 0.0
        self.is_drawing = False
        self.start_station = None
        self.drawing_line = None
        self.drawing_endpoint = None
        self.drawing_segment = None
        self.current_mouse_pos = (0, 0)
        self.add_train_button = pygame.Rect(WIDTH - 170, 18, 145, 38)
        self.add_train_mode = False
        self.dragging_train = None
        self.dragging_new_train = False
        self.train_credits = 1
        self.train_credit_timer = 0.0

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r and self.game_over:
                self.__init__()
                return True
            if self.game_over:
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.add_train_button.collidepoint(event.pos):
                    if self.train_credits <= 0:
                        continue
                    self.add_train_mode = True
                    self.dragging_new_train = True
                    self.current_mouse_pos = event.pos
                    self.is_drawing = False
                    continue
                if self.add_train_mode:
                    continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.start_drawing(event.pos)
            elif event.type == pygame.MOUSEMOTION and self.is_drawing:
                self.current_mouse_pos = event.pos
            elif event.type == pygame.MOUSEMOTION and (
                self.dragging_train or self.dragging_new_train
            ):
                self.current_mouse_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.dragging_new_train:
                    self.finish_new_train_drag(event.pos)
                    continue
                if self.dragging_train:
                    self.finish_train_drag(event.pos)
                    continue
                self.finish_drawing(event.pos)
        return True

    def finish_new_train_drag(self, mouse_pos):
        target_line = next(
            (
                line
                for line in self.lines
                if line.contains_point(mouse_pos, 18)
                or any(station.contains(mouse_pos) for station in line.stations)
            ),
            None,
        )
        if target_line:
            station_index = min(
                range(len(target_line.stations)),
                key=lambda index: pygame.Vector2(
                    target_line.stations[index].position
                ).distance_to(mouse_pos),
            )
            new_train = target_line.add_train(station_index)
            if new_train:
                new_train.network_lines = self.lines
                self.train_credits -= 1
        self.dragging_new_train = False
        self.add_train_mode = False

    def start_train_drag(self, mouse_pos):
        for line in reversed(self.lines):
            for train in line.trains:
                if pygame.Vector2(train.position).distance_to(mouse_pos) <= 30:
                    self.dragging_train = train
                    self.current_mouse_pos = mouse_pos
                    return

    def finish_train_drag(self, mouse_pos):
        target_line = next(
            (
                line
                for line in self.lines
                if line.contains_point(mouse_pos, 18)
                or any(station.contains(mouse_pos) for station in line.stations)
            ),
            None,
        )
        if target_line:
            new_train = target_line.add_train()
            new_train.network_lines = self.lines
        self.dragging_train = None
        self.add_train_mode = False

    def start_drawing(self, mouse_pos):
        self.drawing_line = None
        self.drawing_endpoint = None
        self.drawing_segment = None
        for line_index, line in enumerate(self.lines):
            endpoint = line.endpoint_at(mouse_pos, line_index, len(self.lines))
            if endpoint:
                self.drawing_line = line
                self.drawing_endpoint = endpoint
                break
        if self.drawing_line:
            self.is_drawing = True
            self.current_mouse_pos = mouse_pos
            return

        for station in self.stations:
            if station.contains(mouse_pos):
                self.is_drawing = True
                self.start_station = station
                self.current_mouse_pos = mouse_pos
                return

        self.drawing_line = next(
            (line for line in self.lines if line.contains_point(mouse_pos)),
            None,
        )
        if self.drawing_line:
            self.drawing_segment = self.drawing_line.segment_index_at(mouse_pos)
            self.is_drawing = True
            self.current_mouse_pos = mouse_pos

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
        if target_station:
            if self.drawing_line:
                opposite_endpoint = (
                    self.drawing_endpoint == "start"
                    and target_station is self.drawing_line.end
                ) or (
                    self.drawing_endpoint == "end"
                    and target_station is self.drawing_line.start
                )
                removing_start = (
                    self.drawing_endpoint == "start"
                    and len(self.drawing_line.stations) > 2
                    and target_station is self.drawing_line.stations[1]
                )
                removing_end = (
                    self.drawing_endpoint == "end"
                    and len(self.drawing_line.stations) > 2
                    and target_station is self.drawing_line.stations[-2]
                )
                if removing_start:
                    self.drawing_line.remove_endpoint("start")
                elif removing_end:
                    self.drawing_line.remove_endpoint("end")
                elif opposite_endpoint:
                    self.drawing_line.close_loop()
                elif not self.drawing_line.contains_station(target_station):
                    if self.drawing_segment is not None:
                        self.drawing_line.insert_station(target_station, self.drawing_segment)
                    else:
                        endpoint = self.drawing_endpoint or "end"
                        self.drawing_line.add_station(target_station, endpoint)
            elif (
                len(self.lines) < MAX_LINES
                and not self.has_connection(self.start_station, target_station)
            ):
                color = LINE_COLORS[len(self.lines) % len(LINE_COLORS)]
                line = MetroLine(self.start_station, target_station, color)
                line.train.service_station(line.start)
                self.lines.append(line)

        self.is_drawing = False
        self.start_station = None
        self.drawing_line = None
        self.drawing_endpoint = None
        self.drawing_segment = None

    def has_connection(self, first_station, second_station):
        return any(line.contains_pair(first_station, second_station) for line in self.lines)

    def update(self, delta_time):
        if self.game_over:
            return
        self.train_credit_timer += delta_time
        while self.train_credit_timer >= TRAIN_CREDIT_INTERVAL:
            self.train_credit_timer -= TRAIN_CREDIT_INTERVAL
            self.train_credits += 1
        self.passenger_spawn_timer += delta_time
        if self.passenger_spawn_timer >= PASSENGER_SPAWN_INTERVAL:
            self.passenger_spawn_timer = 0.0
            self.spawn_passengers()

        self.station_spawn_timer += delta_time
        if (
            self.station_spawn_timer >= STATION_SPAWN_INTERVAL
            and len(self.stations) < MAX_STATIONS
        ):
            self.station_spawn_timer = 0.0
            self.spawn_station()

        for line in self.lines:
            line.train.network_lines = self.lines
            for train in line.trains:
                train.network_lines = self.lines
                train.update(delta_time)
                self.score += train.delivered
                train.delivered = 0

    def find_random_route(self):
        if len(self.stations) < 2 or not self.lines:
            return None

        origin, destination = random.sample(self.stations, 2)
        return self.find_route(origin, destination)

    def find_line_route(self):
        routes = []
        for origin in self.stations:
            for destination in self.stations:
                if origin is not destination:
                    route = self.find_route(origin, destination)
                    if route:
                        routes.append(route)
        return max(routes, key=len, default=None)

    def find_route(self, origin, destination):
        routes = {origin: [origin]}
        pending = deque([origin])

        while pending:
            current = pending.popleft()
            if current is destination:
                return routes[current]

            for line in self.lines:
                for first, second in zip(line.stations, line.stations[1:]):
                    if first is current:
                        neighbor = second
                    elif second is current:
                        neighbor = first
                    else:
                        continue
                    if neighbor not in routes:
                        routes[neighbor] = routes[current] + [neighbor]
                        pending.append(neighbor)
        return None

    def spawn_passengers(self):
        shapes = ["circle", "square", "triangle"]
        for station in self.stations:
            destinations = [shape for shape in shapes if shape != station.shape]
            if len(station.waiting_passengers) >= MAX_WAITING_PASSENGERS:
                self.missed_passengers += 1
                if self.missed_passengers >= MAX_MISSED_PASSENGERS:
                    self.game_over = True
                continue
            station.waiting_passengers.append(Passenger(random.choice(destinations)))

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
                shape = random.choice(("circle", "square", "triangle"))
                self.stations.append(Station(*position, shape))
                return True
        return False

    def draw(self):
        self.background.draw(self.screen)
        line_count = len(self.lines)

        shared_segments = {}
        for line_index, line in enumerate(self.lines):
            segments = list(zip(line.stations, line.stations[1:]))
            if line.is_loop:
                segments.append((line.stations[-1], line.stations[0]))
            for start, end in segments:
                key = frozenset((id(start), id(end)))
                shared_segments.setdefault(key, []).append(line_index)

        for line_index, line in enumerate(self.lines):
            offsets = []
            segments = list(zip(line.stations, line.stations[1:]))
            if line.is_loop:
                segments.append((line.stations[-1], line.stations[0]))
            for start, end in segments:
                key = frozenset((id(start), id(end)))
                siblings = shared_segments[key]
                rank = siblings.index(line_index)
                offsets.append((start, end, (rank - (len(siblings) - 1) / 2) * 7))
            line.draw(self.screen, offsets)
            line.draw_endpoints(self.screen, line_index, line_count)

        if self.is_drawing and (self.start_station or self.drawing_line):
            if self.drawing_line:
                drawing_start = (
                    self.drawing_line.handle_position(
                        self.drawing_endpoint,
                        self.lines.index(self.drawing_line),
                        len(self.lines),
                    )
                    if self.drawing_endpoint
                    else self.current_mouse_pos
                )
                drawing_color = self.drawing_line.color
            else:
                drawing_start = self.start_station.position
                drawing_color = LINE_COLORS[len(self.lines)]
            pygame.draw.line(
                self.screen,
                drawing_color,
                drawing_start,
                self.current_mouse_pos,
                4,
            )

        for station in self.stations:
            station.draw(self.screen)
        for line in self.lines:
            for train in line.trains:
                train.draw(self.screen)
        for line_index, line in enumerate(self.lines):
            line.draw_endpoints(self.screen, line_index, line_count)

        self.draw_controls()

        self.draw_hud()

        if self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((245, 245, 247, 220))
            self.screen.blit(overlay, (0, 0))
            font = pygame.font.Font(None, 52)
            title = font.render("Network overloaded", True, (29, 29, 31))
            hint = pygame.font.Font(None, 28).render("Press R to restart", True, (100, 100, 105))
            self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 24)))
            self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 24)))

        pygame.display.flip()

    def draw_hud(self):
        font = pygame.font.Font(None, 28)
        score_text = font.render(f"Delivered: {self.score}", True, (29, 29, 31))
        network_text = font.render(
            f"Stations: {len(self.stations)}  Lines: {len(self.lines)}  "
            f"Trains: {sum(len(line.trains) for line in self.lines)}  Waiting: "
            f"{sum(len(station.waiting_passengers) for station in self.stations)}  "
            f"Missed: {self.missed_passengers}/{MAX_MISSED_PASSENGERS}",
            True,
            (100, 100, 105),
        )
        self.screen.blit(score_text, (24, 20))
        self.screen.blit(network_text, (24, 48))

    def draw_controls(self):
        color = (29, 29, 31) if self.train_credits else (150, 150, 155)
        pygame.draw.rect(self.screen, color, self.add_train_button, border_radius=6)
        font = pygame.font.Font(None, 24)
        label = font.render("+ METRO", True, (255, 255, 255))
        self.screen.blit(label, label.get_rect(center=self.add_train_button.center))
        timer_font = pygame.font.Font(None, 20)
        if self.train_credits:
            timer_text = f"Available: {self.train_credits}"
        else:
            remaining = max(0, int(TRAIN_CREDIT_INTERVAL - self.train_credit_timer))
            timer_text = f"Next metro: {remaining // 60}:{remaining % 60:02d}"
        timer = timer_font.render(timer_text, True, (100, 100, 105))
        timer_position = (self.add_train_button.centerx, self.add_train_button.bottom + 14)
        self.screen.blit(timer, timer.get_rect(center=timer_position))
        if self.dragging_new_train:
            position = (round(self.current_mouse_pos[0]), round(self.current_mouse_pos[1]))
            ghost = pygame.Rect(0, 0, 34, 18)
            ghost.center = position
            pygame.draw.rect(self.screen, (16, 16, 16), ghost, border_radius=8)

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            delta_time = self.clock.tick(FPS) / 1000.0
            self.update(delta_time)
            self.draw()
        pygame.quit()
