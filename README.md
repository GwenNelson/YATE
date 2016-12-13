# YATE - Yet Another Training Environment

YATE is an abstraction layer for 3D gaming environments and virtual worlds intended for use in training prototype AGI (Artificial General Intelligence) systems, at present supporting only minecraft, though the general architecture is intended to work for any other 3D gaming environment.

The system consists of a few parts:

 1. The game server: where the game actually runs, YATE doesn't really directly alter anything here at all
 2. YATE proxy: connects to the game server (or theoretically could embed a game engine) and translates+abstracts details to present a uniform interface
 3. YATE proxy driver: handles game-specific tasks for the YATE proxy
 4. YATE console (optional): connects to the YATE proxy and gives an overview of what the state of the game is from the AI's perspective, can also be used as a lightweight client if desired
 5. Your AGI: connects to the YATE proxy using a simple UDP-based protocol and does AGI stuff - I call mine MrRobot and it's in this repo

## To setup for minecraft
  1. Install the slightly modified SpockBot found in deps/ using "setup.py install"
  2. Start a minecraft server in offline mode running version 1.8, I also recommend using creative mode at first to avoid having to handle respawns and combat
  3. Start the YATE proxy by running minecraft_proxy.sh
  4. Enter a username, password and server IP+Port
  5. Join the game with a normal minecraft client and find your bot's avatar - it should be standing still
  6. Start the YATE console, MrRobot or both (see the relevant directories in this repo) and then have fun

