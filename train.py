from collections import deque

import pygame

from config import (
    TRAIN_ACCELERATION,
    TRAIN_CAPACITY,
    TRAIN_DECELERATION,
    TRAIN_MAX_SPEED,
    TRAIN_STOP_TIME,
)
from connection import closest_point_ratio
from render import draw_shape

TRAIN_LENGTH = 32
TRAIN_HEIGHT = 17


class Train:
    def __init__(self, route, color=(30, 31, 36), speed=TRAIN_MAX_SPEED):
        self.route = route
        self.color = color
        self.speed = speed
        self.current_speed = 0.0
        self.capacity = TRAIN_CAPACITY
        self.passengers = []
        self.station_index = 0
        self.progress = 0.0
        self.direction = 1
        self.network_lines = []
        self.delivered = 0
        self.deliveries = []
        self.stop_timer = 0.0
        self.is_loop = False
        self.just_arrived = False

    # ------------------------------------------------------------------ movement
    def next_station_index(self):
        if self.is_loop:
            return (self.station_index + self.direction) % len(self.route)
        return self.station_index + self.direction

    @property
    def current_segment(self):
        return self.route[self.station_index], self.route[self.next_station_index()]

    @property
    def position(self):
        if self.is_stopped:
            return pygame.Vector2(self.route[0].position)
        start, end = self.current_segment
        return pygame.Vector2(start.position).lerp(pygame.Vector2(end.position), self.progress)

    @property
    def is_stopped(self):
        return len(self.route) < 2

    def snap_to_route(self, point):
        """Place the train on the route segment closest to `point`.

        Called whenever the route is edited, so the train never keeps an index
        that points past the end of the route or onto a removed segment.
        """
        count = len(self.route)
        if count < 2:
            self.station_index = 0
            self.progress = 0.0
            return
        if not self.is_loop and self.direction not in (1, -1):
            self.direction = 1
        target = pygame.Vector2(point)
        best = None
        for direction in (self.direction, -self.direction):
            for index in range(count):
                next_index = index + direction
                if self.is_loop:
                    next_index %= count
                elif not 0 <= next_index < count:
                    continue
                start = self.route[index].position
                end = self.route[next_index].position
                ratio = closest_point_ratio(target, start, end)
                distance = target.distance_to(pygame.Vector2(start).lerp(pygame.Vector2(end), ratio))
                if best is None or distance < best[0] - 0.01:
                    best = (distance, index, ratio, direction)
            if best is not None:
                break
        _, self.station_index, self.progress, self.direction = best

    def update(self, delta_time):
        self.just_arrived = False
        if self.is_stopped:
            return
        if self.stop_timer > 0:
            self.stop_timer = max(0.0, self.stop_timer - delta_time)
            return

        start, end = self.current_segment
        next_index = self.next_station_index()
        distance = pygame.Vector2(start.position).distance_to(end.position)
        distance_left = distance * (1.0 - self.progress)
        braking_distance = self.current_speed ** 2 / (2 * TRAIN_DECELERATION)

        if distance_left <= 1.0 or (self.current_speed == 0 and distance_left <= 10):
            self.arrive_at(next_index)
            return

        if distance_left <= braking_distance + 10:
            self.current_speed = max(0.0, self.current_speed - TRAIN_DECELERATION * delta_time)
        else:
            self.current_speed = min(self.speed, self.current_speed + TRAIN_ACCELERATION * delta_time)

        distance_travelled = self.current_speed * delta_time
        if distance_travelled >= distance_left:
            self.arrive_at(next_index)
            return
        self.progress += distance_travelled / distance

    def arrive_at(self, station_index):
        self.just_arrived = True
        self.station_index = station_index
        self.progress = 0.0
        self.current_speed = 0.0
        serviced = self.service_station(self.route[self.station_index])
        self.stop_timer = TRAIN_STOP_TIME if serviced else 0.0
        if not self.is_loop and (
            self.station_index == 0 or self.station_index == len(self.route) - 1
        ):
            self.direction = 1 if self.station_index == 0 else -1

    # ------------------------------------------------------------------ passengers
    def unload_all(self, station):
        for passenger in self.passengers:
            passenger.target_station = None
            passenger.last_route = None
        station.waiting_passengers.extend(self.passengers)
        self.passengers.clear()

    def route_shapes(self):
        return {station.shape for station in self.route}

    def service_station(self, station):
        route_shapes = self.route_shapes()
        riding = []
        dropped = []
        serviced = False

        for passenger in self.passengers:
            if passenger.destination_shape == station.shape:
                self.delivered += 1
                self.deliveries.append(station.position)
                serviced = True
                continue
            if passenger.target_station is station:
                dropped.append(passenger)
                continue
            # The route may have been edited since boarding: re-check the plan.
            plan_broken = (
                passenger.target_station is None
                and passenger.destination_shape not in route_shapes
            ) or (
                passenger.target_station is not None
                and passenger.target_station not in self.route
            )
            if plan_broken:
                transfer = self.find_transfer_station(passenger.destination_shape, station)
                if transfer is None or transfer is station:
                    dropped.append(passenger)
                    continue
                passenger.target_station = transfer
            riding.append(passenger)

        for passenger in dropped:
            passenger.target_station = None
            passenger.last_route = self.route
        serviced = serviced or bool(dropped)
        self.passengers = riding

        boarding = []
        free_seats = self.capacity - len(self.passengers)
        for passenger in station.waiting_passengers:
            if len(boarding) >= free_seats:
                break
            if passenger.destination_shape in route_shapes:
                target = None
            else:
                if passenger.last_route is self.route:
                    continue
                target = self.find_transfer_station(passenger.destination_shape, station)
                if target is None or target is station:
                    continue
            passenger.target_station = target
            boarding.append(passenger)

        boarded = set(map(id, boarding))
        station.waiting_passengers = [
            passenger for passenger in station.waiting_passengers if id(passenger) not in boarded
        ]
        station.waiting_passengers.extend(dropped)
        self.passengers.extend(boarding)
        return serviced or bool(boarding)

    def find_transfer_station(self, destination_shape, current_station):
        """Return the station on this route where a passenger should change lines.

        Searches the network of lines (breadth first) so multi-hop journeys work.
        Returns `current_station` when the passenger should simply wait here for
        another line, or None when the destination is unreachable.
        """
        route_stations = set(self.route)
        own_lines = [line for line in self.network_lines if line.stations is self.route]
        visited = set(map(id, own_lines))
        queue = deque()
        for line in self.network_lines:
            if id(line) in visited:
                continue
            shared = [station for station in self.route if station in line.stations]
            if not shared:
                continue
            visited.add(id(line))
            if current_station in shared:
                transfer = current_station
            else:
                transfer = min(
                    shared, key=lambda station: self._stops_until(self.route.index(station))
                )
            queue.append((line, transfer))

        while queue:
            line, transfer = queue.popleft()
            if any(station.shape == destination_shape for station in line.stations):
                return transfer
            line_stations = set(line.stations)
            for other in self.network_lines:
                if id(other) in visited or not line_stations.intersection(other.stations):
                    continue
                if route_stations.issuperset(other.stations):
                    continue
                visited.add(id(other))
                queue.append((other, transfer))
        return None

    def _stops_until(self, index):
        count = len(self.route)
        if self.is_loop:
            return (index - self.station_index) * self.direction % count
        if self.direction > 0:
            return index - self.station_index if index >= self.station_index else 2 * count - index
        return self.station_index - index if index <= self.station_index else 2 * count + index

    # ------------------------------------------------------------------ drawing
    def draw(self, surface, shift=None, alpha=255, position=None, angle=None):
        if position is None:
            position = self.position + (shift or pygame.Vector2())
        if angle is None:
            angle = 0.0
            if not self.is_stopped:
                start, end = self.current_segment
                direction = pygame.Vector2(end.position) - pygame.Vector2(start.position)
                if direction.length_squared():
                    angle = direction.as_polar()[1]
        if 90 < angle % 360 < 270:
            angle += 180  # keep passengers upright-ish

        scale = 3
        body = pygame.Surface((TRAIN_LENGTH * scale, TRAIN_HEIGHT * scale), pygame.SRCALPHA)
        pygame.draw.rect(body, self.color, body.get_rect(), border_radius=5 * scale)
        for index, passenger in enumerate(self.passengers[: self.capacity]):
            column, row = index % 3, index // 3
            center = ((7 + column * 9) * scale, (5 + row * 7) * scale)
            draw_shape(body, passenger.destination_shape, center, 2.6 * scale, (255, 255, 255))
        sprite = pygame.transform.rotozoom(body, -angle, 1 / scale)
        if alpha < 255:
            sprite.set_alpha(alpha)
        surface.blit(sprite, sprite.get_rect(center=(round(position[0]), round(position[1]))))
