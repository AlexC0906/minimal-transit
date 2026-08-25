from connection import Connection
from train import Train
import pygame

from config import MAX_TRAINS_PER_LINE


class MetroLine:
    def __init__(self, start_station, end_station, color):
        self.stations = [start_station, end_station]
        self.color = color
        self.is_loop = False
        self.train = Train(self.stations)
        self.trains = [self.train]

    def add_train(self, station_index=0):
        if len(self.trains) >= MAX_TRAINS_PER_LINE:
            return None
        train = Train(self.stations)
        train.is_loop = self.is_loop
        train.station_index = station_index
        if not self.is_loop and station_index == len(self.stations) - 1:
            train.direction = -1
        self.trains.append(train)
        return train

    @property
    def start(self):
        return self.stations[0]

    @property
    def end(self):
        return self.stations[-1]

    def add_station(self, station, endpoint="end"):
        if station not in self.stations:
            if endpoint == "start":
                self.stations.insert(0, station)
                for train in self.trains:
                    train.station_index += 1
            else:
                self.stations.append(station)
            for train in self.trains:
                train.route = self.stations

    def remove_endpoint(self, endpoint):
        if len(self.stations) <= 2:
            return False
        if endpoint == "start":
            self.stations.pop(0)
            for train in self.trains:
                train.station_index = max(0, train.station_index - 1)
        else:
            self.stations.pop()
            for train in self.trains:
                train.station_index = min(train.station_index, len(self.stations) - 1)
        for train in self.trains:
            train.route = self.stations
        return True

    def insert_station(self, station, segment_index):
        if station in self.stations:
            return
        insert_index = segment_index + 1
        self.stations.insert(insert_index, station)
        for train in self.trains:
            if insert_index <= train.station_index:
                train.station_index += 1
            train.route = self.stations

    def close_loop(self):
        if len(self.stations) >= 3:
            self.is_loop = True
            for train in self.trains:
                train.is_loop = True

    def contains_station(self, station):
        return station in self.stations

    def contains_point(self, point, tolerance=10):
        return self.segment_index_at(point, tolerance) is not None

    def segment_index_at(self, point, tolerance=10):
        target = pygame.Vector2(point)
        for index, (start, end) in enumerate(zip(self.stations, self.stations[1:])):
            start_point = pygame.Vector2(start.position)
            segment = pygame.Vector2(end.position) - start_point
            if segment.length_squared() == 0:
                continue
            ratio = max(0, min(1, (target - start_point).dot(segment) / segment.length_squared()))
            closest = start_point + segment * ratio
            if target.distance_to(closest) <= tolerance:
                return index
        return None

    def endpoint_at(self, point, line_index=0, line_count=1, tolerance=12):
        if self.is_loop:
            return None
        target = pygame.Vector2(point)
        start_distance = target.distance_to(self.handle_position("start", line_index, line_count))
        end_distance = target.distance_to(self.handle_position("end", line_index, line_count))
        if start_distance <= tolerance:
            return "start"
        if end_distance <= tolerance:
            return "end"
        return None

    def endpoint_position(self, endpoint):
        if endpoint == "start":
            station = self.stations[0]
            neighbor = self.stations[1]
            direction = pygame.Vector2(station.position) - pygame.Vector2(neighbor.position)
        else:
            station = self.stations[-1]
            neighbor = self.stations[-2]
            direction = pygame.Vector2(station.position) - pygame.Vector2(neighbor.position)
        return pygame.Vector2(station.position) + direction.normalize() * (station.radius + 9)

    def handle_position(self, endpoint, line_index=0, line_count=1):
        position = self.endpoint_position(endpoint)
        station = self.stations[0] if endpoint == "start" else self.stations[-1]
        direction = position - pygame.Vector2(station.position)
        lateral_offset = (line_index - (line_count - 1) / 2) * 14
        return position + direction.normalize().rotate(90) * lateral_offset

    def draw_endpoints(self, surface, line_index=0, line_count=1):
        if self.is_loop:
            return
        for index, station in ((0, self.stations[0]), (-1, self.stations[-1])):
            endpoint = self.handle_position("start" if index == 0 else "end", line_index, line_count)
            direction = pygame.Vector2(station.position) - endpoint
            perpendicular = direction.normalize().rotate(90) * 11
            start = endpoint - perpendicular
            end = endpoint + perpendicular
            pygame.draw.line(surface, self.color, start, end, 8)

    def draw(self, surface, offsets=None):
        segments = list(zip(self.stations, self.stations[1:]))
        if self.is_loop:
            segments.append((self.stations[-1], self.stations[0]))
        for index, (start, end) in enumerate(segments):
            start_point = pygame.Vector2(start.position)
            end_point = pygame.Vector2(end.position)
            direction = end_point - start_point
            offset = offsets[index][2] if offsets else 0
            if offset and direction.length_squared():
                shift = direction.normalize().rotate(90) * offset
                start_point += shift
                end_point += shift
            pygame.draw.line(surface, self.color, start_point, end_point, 4)

    def contains_pair(self, first_station, second_station):
        return any(
            {start, end} == {first_station, second_station}
            for start, end in zip(self.stations, self.stations[1:])
        )