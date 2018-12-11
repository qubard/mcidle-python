# mcidle-python
an idling cli for minecraft. mcidle works by proxying your connection to a minecraft server remotely allowing you to disconnect at any point but remain connected to the server through mcidle.

it is particularly useful for servers which punish you for disconnecting (e.g `2b2t.org` which has queues)

# TODOs

- `auth.json` (store/read auth credentials)
- handle `UpdateBlockEntity`
- cli args
- handle gamemode changes and inventory
- test out other versions (version support)
- complete README w/ usage
- codecov