from connection import Connection
from train import Train


class MetroLine:
    def __init__(self, start_station, end_station, color):
        self.connection = Connection(start_station, end_station)
        self.color = color
        self.train = Train([start_station, end_station], color=color)

    @property
    def start(self):
        return self.connection.start

    @property
    def end(self):
        return self.connection.end

    def draw(self, surface):
        self.connection.draw(surface, self.color)

    def contains_pair(self, first_station, second_station):
        return self.connection.contains_pair(first_station, second_station)