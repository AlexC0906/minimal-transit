import pygame

from config import LINE_WIDTH, MAX_TRAINS_PER_LINE
from connection import closest_point_ratio, segment_shift
from render import draw_disc, draw_thick_line
from train import Train


class MetroLine:
    def __init__(self, start_station, end_station, color):
        self.stations = [start_station, end_station]
        self.color = color
        self.is_loop = False
        self.trains = []
        self.add_train(0)

    # ------------------------------------------------------------------ trains
    def add_train(self, station_index=0):
        if len(self.trains) >= MAX_TRAINS_PER_LINE:
            return None
        train = Train(self.stations, self.color)
        self.attach_train(train, station_index)
        return train

    def attach_train(self, train, station_index):
        train.route = self.stations
        train.color = self.color
        train.is_loop = self.is_loop
        train.station_index = station_index
        train.direction = -1 if (
            not self.is_loop and station_index == len(self.stations) - 1
        ) else 1
        train.progress = 0.0
        train.current_speed = 0.0
        train.stop_timer = 0.0
        if train not in self.trains:
            self.trains.append(train)

    def remove_train(self, train):
        if train in self.trains:
            self.trains.remove(train)
            return True
        return False

    def _edit_route(self, edit):
        """Apply a route edit and re-seat every train on the new route."""
        positions = [(train, train.position) for train in self.trains]
        result = edit()
        for train, position in positions:
            train.route = self.stations
            train.is_loop = self.is_loop
            train.snap_to_route(position)
        return result

    # ------------------------------------------------------------------ editing
    @property
    def start(self):
        return self.stations[0]

    @property
    def end(self):
        return self.stations[-1]

    @property
    def segments(self):
        segments = list(zip(self.stations, self.stations[1:]))
        if self.is_loop:
            segments.append((self.stations[-1], self.stations[0]))
        return segments

    def add_station(self, station, endpoint="end"):
        if station in self.stations:
            return
        if endpoint == "start":
            self._edit_route(lambda: self.stations.insert(0, station))
        else:
            self._edit_route(lambda: self.stations.append(station))

    def remove_endpoint(self, endpoint):
        if len(self.stations) <= 2 or self.is_loop:
            return False
        index = 0 if endpoint == "start" else -1
        removed = self.stations[index]
        self._edit_route(lambda: self.stations.pop(index))
        for train in self.trains:
            for passenger in train.passengers:
                if passenger.target_station is removed:
                    passenger.target_station = None
        return True

    def insert_station(self, station, segment_index):
        if station in self.stations:
            return
        self._edit_route(lambda: self.stations.insert(segment_index + 1, station))

    def close_loop(self):
        if len(self.stations) >= 3:
            self._edit_route(lambda: setattr(self, "is_loop", True))

    def contains_station(self, station):
        return station in self.stations

    def contains_point(self, point, tolerance=10):
        return self.segment_index_at(point, tolerance) is not None

    def segment_index_at(self, point, tolerance=10):
        target = pygame.Vector2(point)
        for index, (start, end) in enumerate(self.segments):
            ratio = closest_point_ratio(target, start.position, end.position)
            closest = pygame.Vector2(start.position).lerp(pygame.Vector2(end.position), ratio)
            if target.distance_to(closest) <= tolerance:
                return index
        return None

    # ------------------------------------------------------------------ handles
    def endpoint_at(self, point, line_index=0, line_count=1, tolerance=14):
        if self.is_loop:
            return None
        target = pygame.Vector2(point)
        for endpoint in ("start", "end"):
            if target.distance_to(self.handle_position(endpoint, line_index, line_count)) <= tolerance:
                return endpoint
        return None

    def endpoint_position(self, endpoint):
        if endpoint == "start":
            station, neighbor = self.stations[0], self.stations[1]
        else:
            station, neighbor = self.stations[-1], self.stations[-2]
        direction = pygame.Vector2(station.position) - pygame.Vector2(neighbor.position)
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        return pygame.Vector2(station.position) + direction.normalize() * (station.radius + 16)

    def handle_position(self, endpoint, line_index=0, line_count=1):
        position = self.endpoint_position(endpoint)
        station = self.stations[0] if endpoint == "start" else self.stations[-1]
        direction = position - pygame.Vector2(station.position)
        lateral_offset = (line_index - (line_count - 1) / 2) * 14
        return position + direction.normalize().rotate(90) * lateral_offset

    def draw_endpoints(self, surface, line_index=0, line_count=1):
        if self.is_loop:
            return
        for endpoint, station in (("start", self.stations[0]), ("end", self.stations[-1])):
            handle = self.handle_position(endpoint, line_index, line_count)
            towards_station = pygame.Vector2(station.position) - handle
            stem_end = pygame.Vector2(station.position) - towards_station.normalize() * station.radius
            draw_thick_line(surface, self.color, stem_end, handle, LINE_WIDTH)
            bar = towards_station.normalize().rotate(90) * 10
            draw_thick_line(surface, self.color, handle - bar, handle + bar, LINE_WIDTH + 1)

    # ------------------------------------------------------------------ drawing
    def draw(self, surface, offsets=None):
        for index, (start, end) in enumerate(self.segments):
            offset = offsets[index] if offsets else 0
            shift = segment_shift(start, end, offset)
            draw_thick_line(
                surface,
                self.color,
                pygame.Vector2(start.position) + shift,
                pygame.Vector2(end.position) + shift,
                LINE_WIDTH,
                round_caps=False,
            )
            draw_disc(surface, self.color, pygame.Vector2(start.position) + shift, LINE_WIDTH / 2)
            draw_disc(surface, self.color, pygame.Vector2(end.position) + shift, LINE_WIDTH / 2)
