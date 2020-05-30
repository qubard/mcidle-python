# mcidle-python
An idling cli for Minecraft that tunnels your connection to a Minecraft server allowing you to disconnect at any point but remain connected to the server through `mcidle`.

[Watch a demo here!](https://youtu.be/r26vacizGJw)

It is particularly useful for servers which punish you for disconnecting (e.g `2b2t.org` which has queues).

Feel free to submit an issue if something doesn't work properly. I would like to point out that this has not been
heavily tested so there will definitely be bugs.

This only has only been tested to work on python3.7 and below! python3.8 seems to break it with the `cryptography` library not being compiled for 3.8 or above. [Install python3.6.8 here](https://www.python.org/downloads/release/python-368/) if you're experiencing issues. You can see your python version by running `python` in a command prompt.

# Supported Versions

If your game/server version is not listed below then `mcidle` will not function properly.

| Version        | Protocol     |
|:-------------:|:-------------:|
| 1.12.2        | 340           |

Make sure you connect with the exact game version that matches the mcidle server and the real-server.

# Installation Guide

You will need [pipx](https://github.com/pipxproject/pipx) to install this. 

Run

```
pipx install git+https://github.com/qubard/mcidle-python.git
```

to install the application. If you're on Windows you may have to restart your command line.

Then `mcidle` should be an available command in your command line on Mac, Windows or Linux.

A simple way to run it in the background of a server is to use `nohup mcidle > output.log &` (with flags). To terminate, run `pkill python` which will kill all running instances of python.

# Notes

When you provide arguments `username` and `password` to the CLI you do not need to provide them again so long as your credentials have not been invalidated. Your username and password are not saved and the login credentials are stored in `credentials.json` (keep these secret).

***If you re-login to Minecraft after starting `mcidle` your `credentials.json` file will be invalidated, simply re-login and don't close mcidle and you'll be able to connect.***

***You'll know you have this error if you see an "Invalid Session" error after connecting to the local mcidle server.***

Make sure that when you connect you connect with the same game client version number as the server.

If you keep on logging in too fast (re-updating credentials) you might get an "invalid username or password" error even though your username/password is correct. Wait 5 minutes before running the script again (this has to do with the way Mojang auth works).

# Example Usage

Run `mcidle --username=example@example.com --password=pw123 --ip=2b2t.org` to point mcidle to `2b2t.org` and listen on `localhost:1337` with the login information `example@example.com` and password `pw123`.

Connecting to `localhost:1337` with your Minecraft client will let you resume your connection to `2b2t.org`. You can change the port at any time by changing the `dport` flag.

Run `mcidle --help` for additional instructions on how to use the command-line utility.

```
usage: mcidle.exe [-h] [--ip IP] [--port PORT] [--protocol PROTOCOL]
                  [--username USERNAME] [--password PASSWORD] [--dport DPORT]
                  [--bindip BINDIP] [--reconnect RECONNECT]

optional arguments:
  -h, --help            show this help message and exit
  --ip IP               The ip address of the server to connect to (e.g
                        localhost)
  --port PORT           The port of the server to connect to (default=25565)
  --protocol PROTOCOL   The protocol version of the server to connect to
                        (default=340)
  --username USERNAME   Your Mojang account username (an email or legacy name)
  --password PASSWORD   Your Mojang account password
  --dport DPORT         The port to connect to with mcidle (default=1337)
  --bindip BINDIP       The IP to bind to with mcidle
  --reconnect RECONNECT
                        The reconnect rate in seconds
```

# Known Issues

- Since Python is slow, reading from a buffer/passing chunks to be processed is slow which can halt the processing of KeepAlives which means that the player can disconnect randomly. The only real solution to this is dedicating a separate thread just to KeepAlives or converting this to C/C++. This would depend on how fast the server you run mcidle on is though, in practice on an Intel i7 8700k I did not have any issues in a single threaded setup.

- Anti AFK is broken on certain servers. Currently moves you 3 blocks in the X direction and 3 blocks back. I would recommend using an anti-afk pool until this is fixed

- In past versions we used multiple threads for worker loggers with Python's `multiprocessing` library, but this actually slowed down the program significantly due to the huge cost of acquiring a lock on dictionary objects so by default now we use 1 thread for packet processing and a synchronized queue to avoid heavy lock hits

- On some windows installs (Windows 10) you may not be able to install the `cryptography` package. This is because `cryptography` was not compiled for 3.8+. Install `python3.7` or below (preferably `3.6.8`) and try again.
  
- Placing a block or modifying the chunk you're in then reconnecting will not show the changes. This is because I did
  not add the processing for chunk sections yet/digging packets (see the `experimental` branch, but Python is still too
  slow to handle these things it seems). To solve this walk out of range of the chunks and then back in to force the
  game to reload them
  
- Some servers use something like `TCP shield` which can detect if you're using a proxy (use wireshark to see the endpoint you connect to) which stops you from connecting.

- If you run this on some VPS providers your ip range might be blocked and you won't be able to connect

- Since you don't move while idling if someone digs blocks underneath you and makes the game think you're falling you can be kicked for flying
