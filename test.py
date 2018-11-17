import socket

#s = socket.create_connection(('localhost', 25565), timeout=5)
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    info = socket.getaddrinfo('localhost', 25565, 0, socket.SOCK_STREAM)

    def key(ai):
        return 0 if ai[0] == socket.AF_INET else \
                1 if ai[0] == socket.AF_INET6 else 2

    ai_faml, ai_type, ai_port, ai_cnam, ai_addr = min(info, key=key)

    s = socket.socket(ai_faml, ai_type, ai_port)
    s.connect(ai_addr)

    print(ai_addr)

    s.sendall(b'Hello, world')
    s.close()
    #data = s.recv(1024)
    #print('Received', repr(data), data)
