import random

import pygame

from background import Background
from config import (
    AUTO_CONNECT_DISTANCE,
    CARD_COLOR,
    DARK_BUTTON,
    DIFFICULTY_RAMP_TIME,
    DISABLED_BUTTON,
    FPS,
    HEIGHT,
    LETTERBOX_COLOR,
    LINE_COLORS,
    LINE_WIDTH,
    MAX_FRAME_TIME,
    MAX_LINES,
    MAX_MISSED_PASSENGERS,
    MAX_STATIONS,
    MAX_TRAINS_PER_LINE,
    MAX_WAITING_PASSENGERS,
    MIN_STATION_DISTANCE,
    MUTED_TEXT_COLOR,
    PASSENGER_SPAWN_INTERVAL,
    PASSENGER_SPAWN_INTERVAL_MIN,
    SHAPES,
    SHARED_LINE_OFFSET,
    STATION_MARGIN,
    STATION_SPAWN_GROWTH,
    STATION_SPAWN_INTERVAL,
    SUCCESS_COLOR,
    TEXT_COLOR,
    TRAIN_CREDIT_INTERVAL,
    WARNING_COLOR,
    WIDTH,
)
from connection import segment_shift
from line import MetroLine
from passenger import Passenger
from render import draw_card, draw_disc, draw_thick_line, font, text
from sound import Sounds
from station import Station
from storage import load_best_score, save_best_score
from train import Train

EFFECT_DURATION = 0.9
TOAST_DURATION = 2.4


class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        # Everything is drawn on a fixed-size canvas, then scaled to the window.
        pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        self.screen = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.fullscreen = False
        self.windowed_size = (WIDTH, HEIGHT)
        pygame.display.set_caption("Minimal Transit")
        self.clock = pygame.time.Clock()
        self.background = Background()
        self.sounds = Sounds()
        self.best_score = load_best_score()

        self.hud_rect = pygame.Rect(16, 16, 292, 84)
        self.controls_rect = pygame.Rect(WIDTH - 186, 16, 170, 128)
        self.add_train_button = pygame.Rect(WIDTH - 176, 26, 150, 40)
        self.credit_bar = pygame.Rect(WIDTH - 176, 94, 150, 4)
        self.pause_button = pygame.Rect(WIDTH - 176, 106, 150, 30)
        self.legend_rect = pygame.Rect(16, HEIGHT - 52, MAX_LINES * 26 + 16, 36)
        self.restart_button = pygame.Rect(0, 0, 180, 42)
        self.restart_button.center = (WIDTH // 2, HEIGHT // 2 + 70)
        self.reset()

    def reset(self):
        self.stations = [
            Station(200, 300, "circle"),
            Station(560, 230, "square"),
            Station(450, 450, "triangle"),
        ]
        self.lines = []
        self.score = 0
        self.missed_passengers = 0
        self.game_over = False
        self.is_paused = False
        self.new_best = False
        self.time = 0.0
        self.play_time = 0.0
        self.toast = None
        self.station_spawn_timer = 0.0
        self.train_credits = 1
        self.train_credit_timer = 0.0
        self.effects = []
        self.mouse_pos = (0, 0)
        self.pending_train_moves = {}
        self.cancel_interactions()

    def cancel_interactions(self):
        self.is_drawing = False
        self.start_station = None
        self.drawing_line = None
        self.drawing_endpoint = None
        self.drawing_segment = None
        self.dragging_train = None
        self.dragging_train_line = None
        self.dragging_new_train = False

    # ------------------------------------------------------------------ input
    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.cancel_interactions()
        self.sounds.play("click")

    def show_toast(self, message, sound="error"):
        self.toast = [message, 0.0]
        if sound:
            self.sounds.play(sound)

    @property
    def is_interacting(self):
        return self.is_drawing or self.dragging_new_train or self.dragging_train is not None

    def toggle_fullscreen(self):
        if self.fullscreen:
            pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        else:
            self.windowed_size = pygame.display.get_surface().get_size()
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.fullscreen = not self.fullscreen

    def view_transform(self):
        """Scale and offset that fit the canvas inside the window (letterboxed)."""
        width, height = pygame.display.get_surface().get_size()
        scale = min(width / WIDTH, height / HEIGHT) or 1.0
        size = (max(1, round(WIDTH * scale)), max(1, round(HEIGHT * scale)))
        offset = ((width - size[0]) // 2, (height - size[1]) // 2)
        return scale, size, offset

    def to_logical(self, position):
        scale, _, offset = self.view_transform()
        return ((position[0] - offset[0]) / scale, (position[1] - offset[1]) / scale)

    def present(self):
        window = pygame.display.get_surface()
        _, size, offset = self.view_transform()
        if size == (WIDTH, HEIGHT) and offset == (0, 0):
            window.blit(self.screen, (0, 0))
        else:
            window.fill(LETTERBOX_COLOR)
            window.blit(pygame.transform.smoothscale(self.screen, size), offset)
        pygame.display.flip()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEMOTION:
                self.mouse_pos = self.to_logical(event.pos)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_m:
                    muted = self.sounds.toggle_mute()
                    self.show_toast("Sound off" if muted else "Sound on", sound="click")
                elif event.key == pygame.K_r and self.game_over:
                    self.reset()
                elif event.key == pygame.K_SPACE and not self.game_over:
                    self.toggle_pause()
                elif event.key == pygame.K_ESCAPE:
                    if self.is_interacting:
                        self.cancel_interactions()
                    elif self.fullscreen:
                        self.toggle_fullscreen()
                continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse_pos = position = self.to_logical(event.pos)
                if self.game_over:
                    if self.restart_button.collidepoint(position):
                        self.reset()
                    continue
                self.handle_mouse_down(position)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and not self.game_over:
                self.mouse_pos = position = self.to_logical(event.pos)
                if self.dragging_new_train:
                    self.finish_new_train_drag(position)
                elif self.dragging_train:
                    self.finish_train_drag(position)
                else:
                    self.finish_drawing(position)
        return True

    def handle_mouse_down(self, mouse_pos):
        if self.pause_button.collidepoint(mouse_pos):
            self.toggle_pause()
            return
        if self.add_train_button.collidepoint(mouse_pos):
            if self.train_credits > 0:
                self.cancel_interactions()
                self.dragging_new_train = True
            else:
                remaining = max(0, int(TRAIN_CREDIT_INTERVAL - self.train_credit_timer))
                self.show_toast(f"No metro available yet. Next one in {self.format_time(remaining)}")
            return
        if self.controls_rect.collidepoint(mouse_pos) or self.hud_rect.collidepoint(mouse_pos):
            return
        if self.start_train_drag(mouse_pos):
            return
        self.start_drawing(mouse_pos)

    def line_at(self, mouse_pos):
        for line in reversed(self.lines):
            if line.contains_point(mouse_pos, 18) or any(
                station.contains(mouse_pos) for station in line.stations
            ):
                return line
        return None

    @staticmethod
    def nearest_station_index(line, mouse_pos):
        return min(
            range(len(line.stations)),
            key=lambda index: pygame.Vector2(line.stations[index].position).distance_to(mouse_pos),
        )

    def reserved_trains(self, line):
        """Trains on a line plus trains already on their way to it."""
        incoming = sum(
            1
            for train, (target, _) in self.pending_train_moves.items()
            if target is line and train not in line.trains
        )
        return len(line.trains) + incoming

    def finish_new_train_drag(self, mouse_pos):
        target_line = self.line_at(mouse_pos)
        if target_line and self.reserved_trains(target_line) < MAX_TRAINS_PER_LINE:
            new_train = target_line.add_train(self.nearest_station_index(target_line, mouse_pos))
            if new_train:
                new_train.network_lines = self.lines
                self.train_credits -= 1
                self.sounds.play("train")
        elif target_line:
            self.show_toast(f"This line already has {MAX_TRAINS_PER_LINE} metros")
        self.dragging_new_train = False

    def start_train_drag(self, mouse_pos):
        for line in reversed(self.lines):
            for train in line.trains:
                if train.position.distance_to(mouse_pos) <= 20:
                    self.cancel_interactions()
                    self.dragging_train = train
                    self.dragging_train_line = line
                    return True
        return False

    def finish_train_drag(self, mouse_pos):
        train = self.dragging_train
        target_line = self.line_at(mouse_pos)
        if target_line is self.dragging_train_line:
            self.pending_train_moves.pop(train, None)
        elif target_line and self.reserved_trains(target_line) < MAX_TRAINS_PER_LINE:
            station_index = self.nearest_station_index(target_line, mouse_pos)
            self.pending_train_moves[train] = (target_line, station_index)
            self.sounds.play("train")
        elif target_line:
            self.show_toast(f"This line already has {MAX_TRAINS_PER_LINE} metros")
        self.dragging_train = None
        self.dragging_train_line = None

    def start_drawing(self, mouse_pos):
        self.cancel_interactions()
        for line_index, line in enumerate(self.lines):
            endpoint = line.endpoint_at(mouse_pos, line_index, len(self.lines))
            if endpoint:
                self.drawing_line = line
                self.drawing_endpoint = endpoint
                self.is_drawing = True
                return

        if len(self.lines) < MAX_LINES:
            for station in self.stations:
                if station.contains(mouse_pos):
                    self.is_drawing = True
                    self.start_station = station
                    return

        for line in reversed(self.lines):
            segment = line.segment_index_at(mouse_pos)
            if segment is not None:
                self.drawing_line = line
                self.drawing_segment = segment
                self.is_drawing = True
                return

        if self.station_at(mouse_pos):
            self.show_toast(f"All {MAX_LINES} lines are in use. Delete one to build another")

    def station_at(self, mouse_pos, exclude=None):
        return next(
            (
                station
                for station in self.stations
                if station is not exclude and station.contains(mouse_pos)
            ),
            None,
        )

    def finish_drawing(self, mouse_pos):
        if not self.is_drawing:
            return
        target_station = self.station_at(mouse_pos, exclude=self.start_station)
        line = self.drawing_line
        if target_station and line:
            stations = line.stations
            neighbor = None
            if self.drawing_endpoint == "start":
                neighbor, opposite = stations[1], stations[-1]
            elif self.drawing_endpoint == "end":
                neighbor, opposite = stations[-2], stations[0]

            if self.drawing_endpoint and target_station is neighbor:
                if len(stations) == 2:
                    self.delete_line(line)
                else:
                    line.remove_endpoint(self.drawing_endpoint)
                self.sounds.play("remove")
            elif self.drawing_endpoint and target_station is opposite:
                if len(stations) >= 3:
                    line.close_loop()
                    self.sounds.play("build")
            elif not line.contains_station(target_station):
                if self.drawing_segment is not None:
                    line.insert_station(target_station, self.drawing_segment)
                else:
                    line.add_station(target_station, self.drawing_endpoint or "end")
                self.sounds.play("build")
        elif target_station and self.start_station and len(self.lines) < MAX_LINES:
            line = MetroLine(self.start_station, target_station, self.next_line_color())
            line.trains[0].network_lines = self.lines
            self.lines.append(line)
            line.trains[0].service_station(line.start)
            self.sounds.play("build")
        self.cancel_interactions()

    def delete_line(self, line):
        for train in line.trains:
            position = train.position
            station = min(
                line.stations,
                key=lambda s: pygame.Vector2(s.position).distance_to(position),
            )
            train.unload_all(station)
            self.pending_train_moves.pop(train, None)
        # The first train comes free with a line; extra ones go back to the depot.
        self.train_credits += max(0, len(line.trains) - 1)
        for train, (target, _) in list(self.pending_train_moves.items()):
            if target is line:
                del self.pending_train_moves[train]
        self.lines.remove(line)

    def next_line_color(self):
        used_colors = {line.color for line in self.lines}
        return next(color for color in LINE_COLORS if color not in used_colors)

    # ------------------------------------------------------------------ simulation
    def update(self, delta_time):
        delta_time = min(delta_time, MAX_FRAME_TIME)
        self.time += delta_time
        for effect in self.effects:
            effect[1] += delta_time
        self.effects = [effect for effect in self.effects if effect[1] < EFFECT_DURATION]
        if self.toast:
            self.toast[1] += delta_time
            if self.toast[1] >= TOAST_DURATION:
                self.toast = None
        if self.game_over or self.is_paused:
            return
        self.play_time += delta_time

        passenger_interval = self.passenger_interval()
        for station in self.stations:
            station.update(delta_time)
            if station.age < 1.0:
                continue
            station.spawn_timer -= delta_time
            if station.spawn_timer <= 0:
                station.spawn_timer = passenger_interval * random.uniform(0.75, 1.25)
                self.spawn_passenger(station)
            is_full = len(station.waiting_passengers) >= MAX_WAITING_PASSENGERS
            if is_full and not station.was_full:
                self.sounds.play("warning", min_gap=0.4)
            station.was_full = is_full
        if self.game_over:
            return

        self.train_credit_timer += delta_time
        while self.train_credit_timer >= TRAIN_CREDIT_INTERVAL:
            self.train_credit_timer -= TRAIN_CREDIT_INTERVAL
            self.train_credits += 1

        self.station_spawn_timer += delta_time
        station_interval = STATION_SPAWN_INTERVAL + STATION_SPAWN_GROWTH * max(0, len(self.stations) - 3)
        if self.station_spawn_timer >= station_interval and len(self.stations) < MAX_STATIONS:
            self.station_spawn_timer = 0.0
            self.spawn_station()

        for line in list(self.lines):
            for train in list(line.trains):
                train.network_lines = self.lines
                if train is not self.dragging_train:
                    train.update(delta_time)
                self.score += train.delivered
                train.delivered = 0
                if train.deliveries:
                    self.sounds.play("deliver")
                self.effects.extend([position, 0.0, "+1", TEXT_COLOR] for position in train.deliveries)
                train.deliveries.clear()
                if train.just_arrived and train in self.pending_train_moves:
                    target_line, station_index = self.pending_train_moves.pop(train)
                    self.move_train_to_line(train, line, target_line, station_index)

    def move_train_to_line(self, train, source_line, target_line, station_index):
        if target_line not in self.lines or len(target_line.trains) >= MAX_TRAINS_PER_LINE:
            return
        train.unload_all(train.route[train.station_index])
        source_line.remove_train(train)
        target_line.attach_train(train, min(station_index, len(target_line.stations) - 1))
        train.network_lines = self.lines

    def passenger_interval(self):
        """Seconds between passengers at one station; shrinks as the game goes on."""
        ramp = min(1.0, self.play_time / DIFFICULTY_RAMP_TIME)
        return PASSENGER_SPAWN_INTERVAL + (PASSENGER_SPAWN_INTERVAL_MIN - PASSENGER_SPAWN_INTERVAL) * ramp

    def spawn_passenger(self, station):
        if len(station.waiting_passengers) >= MAX_WAITING_PASSENGERS:
            self.missed_passengers += 1
            self.effects.append([station.position, 0.0, "missed", WARNING_COLOR])
            if self.missed_passengers >= MAX_MISSED_PASSENGERS:
                self.end_game()
            else:
                self.sounds.play("miss")
            return
        destinations = [shape for shape in SHAPES if shape != station.shape]
        station.waiting_passengers.append(Passenger(random.choice(destinations)))

    def end_game(self):
        self.game_over = True
        self.cancel_interactions()
        self.new_best = self.score > self.best_score
        if self.new_best:
            self.best_score = self.score
            save_best_score(self.score)
        self.sounds.play("gameover")

    @staticmethod
    def format_time(seconds):
        seconds = int(seconds)
        return f"{seconds // 60}:{seconds % 60:02d}"

    def spawn_station(self):
        blocked = [
            rect.inflate(60, 60)
            for rect in (self.hud_rect, self.controls_rect, self.legend_rect)
        ]
        for _ in range(60):
            position = (
                random.randint(STATION_MARGIN, WIDTH - STATION_MARGIN),
                random.randint(STATION_MARGIN, HEIGHT - STATION_MARGIN),
            )
            if any(rect.collidepoint(position) for rect in blocked):
                continue
            if all(
                pygame.Vector2(position).distance_to(station.position) >= MIN_STATION_DISTANCE
                for station in self.stations
            ):
                shape = random.choice(SHAPES)
                station = Station.spawned(*position, shape)
                self.stations.append(station)
                self.connect_to_passing_lines(station)
                return True
        return False

    def connect_to_passing_lines(self, station):
        """Add a newly spawned station to every line that runs through its spot."""
        connected = False
        for line in self.lines:
            segment = line.segment_index_at(station.position, AUTO_CONNECT_DISTANCE)
            if segment is not None and not line.contains_station(station):
                line.insert_station(station, segment)
                connected = True
        if connected:
            self.effects.append([station.position, 0.0, "connected", SUCCESS_COLOR])
            self.sounds.play("build")
        return connected

    # ------------------------------------------------------------------ drawing
    def compute_offsets(self):
        shared = {}
        for line_index, line in enumerate(self.lines):
            for start, end in line.segments:
                shared.setdefault(frozenset((id(start), id(end))), []).append(line_index)
        offsets = []
        for line_index, line in enumerate(self.lines):
            line_offsets = {}
            for start, end in line.segments:
                key = frozenset((id(start), id(end)))
                siblings = shared[key]
                rank = siblings.index(line_index)
                line_offsets[key] = (rank - (len(siblings) - 1) / 2) * SHARED_LINE_OFFSET
            offsets.append(line_offsets)
        return offsets

    def busy_directions(self):
        """For each station, the directions taken up by lines and endpoint handles."""
        busy = {}
        line_count = len(self.lines)
        for line_index, line in enumerate(self.lines):
            for start, end in line.segments:
                direction = pygame.Vector2(end.position) - pygame.Vector2(start.position)
                if direction.length_squared() == 0:
                    continue
                direction = direction.normalize()
                busy.setdefault(id(start), []).append(direction)
                busy.setdefault(id(end), []).append(-direction)
            if line.is_loop:
                continue
            for endpoint, station in (("start", line.start), ("end", line.end)):
                direction = line.handle_position(endpoint, line_index, line_count) - pygame.Vector2(
                    station.position
                )
                if direction.length_squared():
                    busy.setdefault(id(station), []).append(direction.normalize())
        return busy

    def draw(self):
        self.background.draw(self.screen)
        line_count = len(self.lines)
        offsets = self.compute_offsets()

        for line_index, line in enumerate(self.lines):
            line.draw_endpoints(self.screen, line_index, line_count)
            segment_offsets = [
                offsets[line_index][frozenset((id(start), id(end)))] for start, end in line.segments
            ]
            line.draw(self.screen, segment_offsets)

        self.draw_route_preview()

        hovered = self.station_at(self.mouse_pos, self.start_station) if self.is_drawing else None
        busy = self.busy_directions()
        for station in self.stations:
            station.draw(
                self.screen,
                self.time,
                highlighted=station is hovered,
                busy_directions=busy.get(id(station), ()),
            )

        for line_index, line in enumerate(self.lines):
            for train in line.trains:
                if train is self.dragging_train or train.is_stopped:
                    continue
                start, end = train.current_segment
                offset = offsets[line_index].get(frozenset((id(start), id(end))), 0)
                alpha = 150 if train in self.pending_train_moves else 255
                train.draw(self.screen, segment_shift(start, end, offset), alpha)

        self.draw_effects()
        self.draw_drag_ghost()
        self.draw_hud()
        self.draw_controls()
        self.draw_legend()

        banner_shown = False
        if self.is_paused and not self.game_over:
            self.draw_paused()
            banner_shown = True
        elif not self.lines and not self.game_over:
            self.draw_hint("Drag from one station to another to build your first line")
            banner_shown = True
        if self.toast and not self.game_over:
            self.draw_toast(raised=banner_shown)
        if self.game_over:
            self.draw_game_over()

        self.update_cursor()
        self.present()

    def draw_route_preview(self):
        if not self.is_drawing:
            return
        line = self.drawing_line
        color = line.color if line else self.next_line_color()
        target = self.station_at(self.mouse_pos, self.start_station)
        end = target.position if target else self.mouse_pos
        if line and self.drawing_segment is not None:
            if self.drawing_segment < len(line.segments):
                first, second = line.segments[self.drawing_segment]
                draw_thick_line(self.screen, color, first.position, end, LINE_WIDTH - 2)
                draw_thick_line(self.screen, color, end, second.position, LINE_WIDTH - 2)
            return
        if line:
            index = self.lines.index(line)
            start = line.handle_position(self.drawing_endpoint, index, len(self.lines))
        else:
            start = self.start_station.position
        draw_thick_line(self.screen, color, start, end, LINE_WIDTH)
        if not target:
            draw_disc(self.screen, color, end, 7)

    def draw_drag_ghost(self):
        if not (self.dragging_new_train or self.dragging_train):
            return
        train = self.dragging_train
        if train is None:
            train = Train([], DARK_BUTTON)
        hovered_line = self.line_at(self.mouse_pos)
        original_color = train.color
        if hovered_line:
            train.color = hovered_line.color
        train.draw(self.screen, alpha=200, position=self.mouse_pos, angle=0)
        train.color = original_color

    def draw_effects(self):
        for position, age, label, color in self.effects:
            progress = age / EFFECT_DURATION
            surface = font(15, True).render(label, True, color)
            surface.set_alpha(round(255 * (1 - progress) ** 1.5))
            rect = surface.get_rect(center=(position[0], position[1] - 34 - 22 * progress))
            self.screen.blit(surface, rect)

    def draw_hud(self):
        draw_card(self.screen, self.hud_rect)
        left = self.hud_rect.x + 16
        text(self.screen, "DELIVERED", 11, MUTED_TEXT_COLOR, bold=True, topleft=(left, 26))
        text(self.screen, self.score, 30, TEXT_COLOR, bold=True, topleft=(left, 36))

        missed_x = self.hud_rect.x + 118
        text(self.screen, "MISSED", 11, MUTED_TEXT_COLOR, bold=True, topleft=(missed_x, 26))
        for index in range(MAX_MISSED_PASSENGERS):
            center = (missed_x + 7 + index * 20, 56)
            color = WARNING_COLOR if index < self.missed_passengers else (225, 225, 230)
            draw_disc(self.screen, color, center, 6)

        time_x = self.hud_rect.x + 208
        text(self.screen, "TIME", 11, MUTED_TEXT_COLOR, bold=True, topleft=(time_x, 26))
        text(self.screen, self.format_time(self.play_time), 20, TEXT_COLOR, bold=True, topleft=(time_x, 42))

        trains = sum(len(line.trains) for line in self.lines)
        waiting = sum(len(station.waiting_passengers) for station in self.stations)
        stats = f"{len(self.stations)} stations  ·  {trains} trains  ·  {waiting} waiting"
        text(self.screen, stats, 12, MUTED_TEXT_COLOR, bottomleft=(left, self.hud_rect.bottom - 8))

    def draw_toast(self, raised=False):
        label = font(13, True).render(self.toast[0], True, TEXT_COLOR)
        rect = pygame.Rect(0, 0, label.get_width() + 44, 36)
        rect.midbottom = (WIDTH // 2 + 40, HEIGHT - 16 - (46 if raised else 0))
        draw_card(self.screen, rect, radius=18)
        self.screen.blit(label, label.get_rect(center=rect.center))

    def draw_controls(self):
        draw_card(self.screen, self.controls_rect)
        button = self.add_train_button
        available = self.train_credits > 0
        hovered = available and button.collidepoint(self.mouse_pos)
        color = DARK_BUTTON if available else DISABLED_BUTTON
        if hovered:
            color = (60, 62, 72)
        pygame.draw.rect(self.screen, color, button, border_radius=10)
        icon = pygame.Rect(0, 0, 22, 12)
        icon.center = (button.x + 30, button.centery)
        pygame.draw.rect(self.screen, (255, 255, 255), icon, border_radius=4)
        text(self.screen, "+ Metro", 16, (255, 255, 255), bold=True, midleft=(button.x + 52, button.centery))

        if available:
            status = f"{self.train_credits} available"
        else:
            remaining = max(0, int(TRAIN_CREDIT_INTERVAL - self.train_credit_timer))
            status = f"Next metro in {remaining // 60}:{remaining % 60:02d}"
        text(self.screen, status, 12, MUTED_TEXT_COLOR, center=(button.centerx, button.bottom + 13))
        bar = self.credit_bar
        pygame.draw.rect(self.screen, (230, 230, 234), bar, border_radius=2)
        fill = bar.copy()
        fill.width = round(bar.width * self.train_credit_timer / TRAIN_CREDIT_INTERVAL)
        if fill.width:
            pygame.draw.rect(self.screen, LINE_COLORS[0], fill, border_radius=2)

        pause = self.pause_button
        hovered = pause.collidepoint(self.mouse_pos)
        if self.is_paused:
            background, foreground, label = WARNING_COLOR, (255, 255, 255), "Resume"
        else:
            background = (228, 228, 233) if hovered else (240, 240, 243)
            foreground, label = TEXT_COLOR, "Pause"
        pygame.draw.rect(self.screen, background, pause, border_radius=8)
        text(self.screen, label, 14, foreground, bold=True, center=pause.center)

    def draw_legend(self):
        draw_card(self.screen, self.legend_rect, radius=18)
        used = {line.color for line in self.lines}
        for index, color in enumerate(LINE_COLORS):
            center = (self.legend_rect.x + 21 + index * 26, self.legend_rect.centery)
            draw_disc(self.screen, color, center, 8)
            if color not in used:
                draw_disc(self.screen, CARD_COLOR, center, 5)

    def draw_hint(self, message):
        rect = pygame.Rect(0, 0, 440, 36)
        rect.midbottom = (WIDTH // 2 + 40, HEIGHT - 16)
        draw_card(self.screen, rect, radius=18)
        text(self.screen, message, 13, MUTED_TEXT_COLOR, center=rect.center)

    def draw_paused(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((30, 31, 36, 28))
        self.screen.blit(overlay, (0, 0))
        rect = pygame.Rect(0, 0, 300, 36)
        rect.midbottom = (WIDTH // 2 + 40, HEIGHT - 16)
        draw_card(self.screen, rect, radius=18)
        text(self.screen, "Paused  ·  you can still edit lines", 13, TEXT_COLOR, bold=True, center=rect.center)

    def draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((244, 242, 237, 190))
        self.screen.blit(overlay, (0, 0))
        card = pygame.Rect(0, 0, 400, 250)
        card.center = (WIDTH // 2, HEIGHT // 2)
        draw_card(self.screen, card, radius=20)
        text(self.screen, "Network overloaded", 28, TEXT_COLOR, bold=True, center=(card.centerx, card.y + 52))
        noun = "passenger" if self.score == 1 else "passengers"
        summary = f"You delivered {self.score} {noun} in {self.format_time(self.play_time)}"
        text(self.screen, summary, 16, MUTED_TEXT_COLOR, center=(card.centerx, card.y + 92))
        if self.new_best:
            text(self.screen, "New best score!", 15, SUCCESS_COLOR, bold=True, center=(card.centerx, card.y + 124))
        else:
            text(
                self.screen,
                f"Best score: {self.best_score}",
                14,
                MUTED_TEXT_COLOR,
                center=(card.centerx, card.y + 124),
            )
        hovered = self.restart_button.collidepoint(self.mouse_pos)
        pygame.draw.rect(
            self.screen, (60, 62, 72) if hovered else DARK_BUTTON, self.restart_button, border_radius=10
        )
        text(self.screen, "Play again  (R)", 16, (255, 255, 255), bold=True, center=self.restart_button.center)

    def update_cursor(self):
        clickable = (
            self.restart_button.collidepoint(self.mouse_pos)
            if self.game_over
            else self.pause_button.collidepoint(self.mouse_pos)
            or (self.train_credits > 0 and self.add_train_button.collidepoint(self.mouse_pos))
        )
        cursor = pygame.SYSTEM_CURSOR_HAND if clickable else pygame.SYSTEM_CURSOR_ARROW
        if getattr(self, "_cursor", None) != cursor:
            try:
                pygame.mouse.set_cursor(cursor)
            except pygame.error:
                pass
            self._cursor = cursor

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            delta_time = self.clock.tick(FPS) / 1000.0
            self.update(delta_time)
            self.draw()
        pygame.quit()
