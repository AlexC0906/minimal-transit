import pygame

from config import LINE_COLOR, TRAIN_CAPACITY


class Train:
    def __init__(self, route, color=LINE_COLOR, speed=180):
        self.route = route
        self.color = color
        self.speed = speed
        self.capacity = TRAIN_CAPACITY
        self.passengers = []
        self.station_index = 0
        self.progress = 0.0
        self.direction = 1
        self.delivered = 0

    @property
    def position(self):
        start = pygame.Vector2(self.route[self.station_index].position)
        end = pygame.Vector2(self.route[self.station_index + self.direction].position)
        return start.lerp(end, self.progress)

    def update(self, delta_time):
        remaining_distance = self.speed * delta_time
        while remaining_distance > 0 and not self.is_stopped:
            start = pygame.Vector2(self.route[self.station_index].position)
            end = pygame.Vector2(self.route[self.station_index + self.direction].position)
            distance = start.distance_to(end)
            distance_left = distance * (1.0 - self.progress)

            if remaining_distance < distance_left:
                self.progress += remaining_distance / distance
                remaining_distance = 0
            else:
                remaining_distance -= distance_left
                self.station_index += self.direction
                self.progress = 0.0
                self.service_station(self.route[self.station_index])
                if self.station_index == 0 or self.station_index == len(self.route) - 1:
                    self.direction *= -1

    @property
    def is_stopped(self):
        return len(self.route) < 2

    def service_station(self, station):
        delivered = sum(
            passenger.destination_shape == station.shape
            for passenger in self.passengers
        )
        self.passengers = [
            passenger
            for passenger in self.passengers
            if passenger.destination_shape != station.shape
        ]
        self.delivered += delivered
        free_seats = self.capacity - len(self.passengers)
        if free_seats <= 0:
            return

        route_shapes = {station.shape for station in self.route}
        boardable = [
            passenger
            for passenger in station.waiting_passengers
            if passenger.destination_shape in route_shapes
        ]
        boarding = boardable[:free_seats]
        self.passengers.extend(boarding)
        station.waiting_passengers = [
            passenger for passenger in station.waiting_passengers if passenger not in boarding
        ]

    def draw(self, surface):
        train_rect = pygame.Rect(0, 0, 22, 14)
        train_rect.center = (round(self.position.x), round(self.position.y))
        pygame.draw.rect(surface, self.color, train_rect, border_radius=3)
        pygame.draw.rect(surface, (255, 255, 255), train_rect.inflate(-8, -6), border_radius=1)