from src.networking.connection import MinecraftConnection, MinecraftServer

conn = MinecraftConnection(ip="localhost", protocol=340, username="leddit", \
                  profile={}).start()

server = MinecraftServer(port=1337)
server.start()