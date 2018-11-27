# mcidle-python
an idling cli for minecraft

# TODOs

Goal is to port the golang version to python

- connect the client to the server
    - authentication code to get valid session id
    - authentication and encryption routines
    - pycraft has some good examples..
- then write a listener thread which streams packets to a buffer for output from C->S
- custom exceptions (for connectivity states)
- not handling edge cases where there is no encryption
- `auth.json` (store/read auth credentials)