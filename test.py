import socket

s = socket.create_connection(('localhost', 25565), timeout=5)

s.sendall(b'Hello, world')
data = s.recv(1024)
print('Received', repr(data), data)
