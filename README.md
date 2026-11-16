# Minimal Transit

![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=for-the-badge&logo=python)
![Pygame](https://img.shields.io/badge/pygame-2.6%2B-green?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/license-MIT-lightgrey?style=for-the-badge)

**Minimal Transit** is a tactical transit-management game built with Python and Pygame, inspired by games such as *Mini Metro*.

Build colored metro lines, place trains on them, and keep passengers moving between stations before the network becomes overloaded.

## Features

- Three station shapes: circle, square, and triangle.
- Passengers have a destination shape and are displayed using that shape and its color.
- Create and extend colored metro lines with click-and-drag controls.
- Insert a new station into an existing line by dragging from a line segment to the station.
- Close a line into a loop by dragging one endpoint to the other.
- Trains accelerate, slow down near stations, stop when they have passengers to board or unload, and continue in the correct direction.
- Transfer passengers between lines through shared stations.
- Add extra trains by dragging a metro asset from the `+ METRO` control onto a line.
- Move existing trains between lines. Trains finish their current trip, unload passengers at the next station, and then continue empty on the new line.
- Up to five trains can run on each line.
- Difficulty ramps up: up to twelve stations appear over time and passengers arrive faster the longer you survive.
- A new station that appears on top of an existing line is connected to that line automatically.
- Up to six colored lines.
- Best score is saved between sessions, and a clock shows how long the network has survived.
- Short messages explain why an action is not possible (all lines in use, line full, no metro available).
- Generated sound effects for deliveries, building, warnings, and game over. No audio files needed.
- Resizable window and fullscreen; the game scales to fit.
- Passengers plan multi-line journeys and change trains at shared stations.
- Delete a whole line by dragging an endpoint back onto its only other station; extra trains return to the depot.
- Overcrowded stations show a red progress ring that pulses when the station is full.
- Game over and restart flow when too many passengers are missed.
- Clean minimal look: antialiased lines and stations, trains that rotate along the track, floating `+1` delivery markers, and HUD cards.

## Gameplay Controls

| Action | How to play |
| --- | --- |
| Create a line | Click a station, drag to another station, and release. |
| Extend a line | Drag an endpoint handle to a new station. |
| Insert a station | Drag from an existing line segment to a station. |
| Create a loop | Drag one endpoint handle to the opposite endpoint. |
| Shorten a line | Drag an endpoint handle back onto the neighbouring station. |
| Delete a line | Shorten a two-station line by dragging its endpoint onto the other station. |
| Add a train | Click `+ METRO`, drag the metro asset onto a line, and release. |
| Move a train | Click an existing train and drag it onto another line. |
| Pause / resume | Press `Space` or click `Pause`. Lines can still be edited while paused. |
| Cancel a drag | Press `Esc`. |
| Fullscreen | Press `F11` (`Esc` or `F11` to leave). The window can also be resized. |
| Mute / unmute | Press `M`. |
| Restart | Click `Play again` or press `R` after the network is overloaded. |

## Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/AlexC0906/minimal-transit.git
cd minimal-transit
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the game:

```bash
python main.py
```

On Windows, the Python launcher can also be used:

```powershell
py main.py
```

## Project Structure

```text
minimal-transit/
├── assets/
│   ├── background_metro2.avif
│   ├── circle.svg
│   ├── metro.svg
│   ├── square.svg
│   └── triangle.svg
├── background.py       # Background asset loading
├── config.py           # Game settings, colors, and limits
├── connection.py       # Geometry for route segments
├── render.py           # Fonts and antialiased drawing helpers
├── game.py             # Main game state and event loop
├── line.py             # Metro lines and route editing
├── passenger.py        # Passenger destinations and rendering
├── sound.py            # Generated sound effects
├── station.py          # Station shapes and waiting passengers
├── storage.py          # Best score persistence (save.json)
├── train.py            # Train movement, stops, boarding, and transfers
├── main.py             # Application entry point
└── requirements.txt    # Python dependencies
```

## Configuration

Gameplay values are centralized in [config.py](config.py). You can adjust values such as:

- train capacity
- maximum trains per line
- train speed and acceleration
- passenger spawn interval (starting value, minimum, and how fast it ramps)
- station spawn interval and maximum number of stations
- line colors (the number of colors is the number of lines)
- sound volume
- waiting passenger limit
- game-over threshold

## Technical Notes

- The game is drawn on an `800x600` canvas that is scaled to the window, keeping its aspect ratio.
- The best score is stored in `save.json` next to the game (ignored by git).
- Route editing uses geometric hit testing for stations, endpoints, and line segments.
- Passenger transfers use shared stations between metro lines.
- The AVIF background is loaded through Pillow and `pillow-avif-plugin`. If it cannot be loaded, a generated paper-style background is used instead.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
