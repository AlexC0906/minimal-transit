import pygame

from config import (
    TRAIN_ACCELERATION,
    TRAIN_CAPACITY,
    TRAIN_DECELERATION,
    TRAIN_MAX_SPEED,
    TRAIN_STOP_TIME,
)


class Train:
    def __init__(self, route, color=(16, 16, 16), speed=TRAIN_MAX_SPEED):
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
        self.stop_timer = 0.0
        self.is_loop = False
        self.just_arrived = False

    def next_station_index(self):
        if self.is_loop:
            return (self.station_index + self.direction) % len(self.route)
        return self.station_index + self.direction

    @property
    def position(self):
        start = pygame.Vector2(self.route[self.station_index].position)
        end = pygame.Vector2(self.route[self.next_station_index()].position)
        return start.lerp(end, self.progress)

    def update(self, delta_time):
        self.just_arrived = False
        if self.is_stopped:
            return
        if self.stop_timer > 0:
            self.stop_timer = max(0.0, self.stop_timer - delta_time)
            return

        start = pygame.Vector2(self.route[self.station_index].position)
        next_index = self.next_station_index()
        end = pygame.Vector2(self.route[next_index].position)
        distance = start.distance_to(end)
        distance_left = distance * (1.0 - self.progress)
        braking_distance = self.current_speed ** 2 / (2 * TRAIN_DECELERATION)

        if distance_left <= 1.0 or (self.current_speed == 0 and distance_left <= 10):
            self.arrive_at(next_index)
            return

        if distance_left <= braking_distance + 10:
            self.current_speed = max(
                0.0, self.current_speed - TRAIN_DECELERATION * delta_time
            )
        else:
            self.current_speed = min(
                self.speed, self.current_speed + TRAIN_ACCELERATION * delta_time
            )

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
            self.direction *= -1

    def unload_all(self, station):
        station.waiting_passengers.extend(self.passengers)
        self.passengers.clear()

    @property
    def is_stopped(self):
        return len(self.route) < 2

    def service_station(self, station):
        remaining_passengers = []
        transfers = []
        serviced = False
        for passenger in self.passengers:
            if passenger.target_shape != station.shape:
                remaining_passengers.append(passenger)
                continue
            serviced = True
            if passenger.destination_shape == station.shape:
                self.delivered += 1
            else:
                passenger.target_shape = None
                transfers.append(passenger)

        self.passengers = remaining_passengers
        station.waiting_passengers.extend(transfers)
        free_seats = self.capacity - len(self.passengers)
        if free_seats <= 0:
            return serviced

        route_shapes = {route_station.shape for route_station in self.route}
        boardable = []
        for passenger in station.waiting_passengers:
            if passenger in transfers:
                continue
            if passenger.destination_shape in route_shapes:
                passenger.target_shape = passenger.destination_shape
                boardable.append(passenger)
                continue
            transfer_station = self.find_transfer_station(passenger.destination_shape)
            if transfer_station:
                passenger.target_shape = transfer_station.shape
                boardable.append(passenger)

        boarding = boardable[:free_seats]
        self.passengers.extend(boarding)
        station.waiting_passengers = [
            passenger
            for passenger in station.waiting_passengers
            if passenger not in boarding
        ]
        return serviced or bool(boarding)

    def find_transfer_station(self, destination_shape):
        route_stations = set(self.route)
        for line in self.network_lines:
            if line.train is self or not any(
                station.shape == destination_shape for station in line.stations
            ):
                continue
            for station in line.stations:
                if station in route_stations and station.shape != destination_shape:
                    return station
        return None

    def draw(self, surface):
        train_rect = pygame.Rect(0, 0, 34, 18)
        train_rect.center = (round(self.position.x), round(self.position.y))
        pygame.draw.rect(surface, self.color, train_rect, border_radius=8)
        for index, passenger in enumerate(self.passengers[:self.capacity]):
            passenger.draw(surface, (train_rect.left + 7 + index * 5, train_rect.centery), 2)
