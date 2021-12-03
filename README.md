# PIRL (Pool In Real Life)

A real-life billiards training application that features a preactice and game mode.

## Features

### Practice Mode

Allows users to take a “snapshot” of the pool table layout between shots. The user can then replay difficult layouts.

### Game Mode

Allows a user to play a real-life pool game against a computer using a physics engine to determine the new pool ball positions and overlays the new locations onto the table.

### Settings Menu

This menu has multiple HSV sliders to calibrate a mask for each pool ball color.

## Future Features
- [] Check if ball reaches pocket
- [] Check win conditions
- [] Fix intaller for releases
- [] Better AI
- [] Error handling
- [] Table calibration
- [] Add docustring comments
- [] Add tests
- [] Fix background image scaling
- [] Auto update when slider is moved
- [] Audio files

## Installation

Clone the repo and use the package manager pip to install requirments.

```bash
pip install -r requirements.txt
```

## Build and Create Installer (currently not working)

```bash
python setup.py bdist_msi
```

## References
* Tkinter using OOP: [pythonprogramming.net](https://pythonprogramming.net/)