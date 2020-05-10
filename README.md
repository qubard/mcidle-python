# mcidle-python
An idling cli for minecraft which works by proxying your connection to a minecraft server remotely allowing you to disconnect at any point but remain connected to the server through mcidle.

It is particularly useful for servers which punish you for disconnecting (e.g `2b2t.org` which has queues)

Feel free to submit an issue if something doesn't work properly. I would like to point out that this has not been
heavily tested so there will definitely be bugs.

# Supported Versions

If your game/server version is not listed below then `mcidle` will not function properly.

| Version        | Protocol     |
|:-------------:|:-------------:|
| 1.12.2        | 340           |

Make sure you connect with the exact game version that matches the mcidle server and the real-server.

# Setup

Simply run `pip install -r requirements.txt` to install all the necessary packages.

# Notes

When you provide arguments `username` and `password` to the CLI you do not need to provide them again so long as your credentials have not been invalidated. Your username and password are not saved and the login credentials are stored in `credentials.json` (keep these secret).

***If you re-login to Minecraft after starting `mcidle` your `credentials.json` file will be invalidated, simply re-login and don't close mcidle and you'll be able to connect.***

***You'll know you have this error if you see an "Invalid Session" error after connecting to the local mcidle server.***

Make sure that when you connect you connect with the same game client version number as the server.

If you keep on logging in too fast (re-updating credentials) you might get an "invalid username or password" error even though your username/password is correct. Wait 5 minutes before running the script again (this has to do with the way Mojang auth works).

# Example Usage

Run `python3 mcidle.py --username=example@example.com --password=pw123 --ip=2b2t.org` to point mcidle to `2b2t.org` and listen on `localhost:1337` with the login information `example@example.com` and password `pw123`.

Connecting to `localhost:1337` with your Minecraft client will let you resume your connection to `2b2t.org`. You can change the port at any time by changing the `dport` flag.

Run `python3 mcidle.py --help` for additional instructions on how to use the command-line utility.

```
usage: mcidle.py [-h] [--ip IP] [--port PORT] [--protocol PROTOCOL]
               [--username USERNAME] [--password PASSWORD] [--dstport DSTPORT]

optional arguments:
  -h, --help           show this help message and exit
  --ip IP              The ip address of the server to connect to (e.g
                       localhost)
  --port PORT          The port of the server to connect to (default=25565)
  --protocol PROTOCOL  The protocol version of the server to connect to
                       (default=340)
  --username USERNAME  Your Mojang account username (an email or legacy name)
  --password PASSWORD  Your Mojang account password
  --dport DPORT    The port that mcidle listens on (default=1337)

```

# Known Issues

- Since Python is slow, reading from a buffer/passing chunks to be processed is slow which can halt the processing of KeepAlives which means that the player can disconnect randomly. The only real solution to this is dedicating a separate thread just to KeepAlives or converting this to C/C++. This would depend on how fast the server you run mcidle on is though, in practice on an Intel i7 8700k I did not have any issues in a single threaded setup.

- In past versions we used multiple threads for worker loggers with Python's `multiprocessing` library, but this actually slowed down the program significantly due to the huge cost of acquiring a lock on dictionary objects so by default now we use 1 thread for packet processing and a synchronized queue to avoid heavy lock hits

- On some windows installs (Windows 10) you may get a `missing Visual C++ 14.0` error while installing the pip
  requirements. Install it
  [here](https://www.microsoft.com/en-ca/download/details.aspx?id=48145). If you can't build it still try installing the latest Visual Studio.
  
- Placing a block or modifying the chunk you're in then reconnecting will not show the changes. This is because I did
  not add the processing for chunk sections yet/digging packets (see the `experimental` branch, but Python is still too
  slow to handle these things it seems). To solve this walk out of range of the chunks and then back in to force the
  game to reload them
  
- Some servers use something like `TCP shield` which can detect if you're using a proxy (use wireshark to see the endpoint you connect to) which stops you from connecting.

- If you run this on some VPS providers your ip range might be blocked and you won't be able to connect

- Since you don't move while idling if someone digs blocks underneath you and makes the game think you're falling you can be kicked for flying

# TODOs
- Avoid destroying/recreating threads since it is very bug prone
- handle `UpdateBlockEntity`
- handle chunks and various mob entities
- test out other versions (version support)
- version number files, somehow? player shouldn't have to worry about versions messing up
- basic TravisCI integration with a test suite
