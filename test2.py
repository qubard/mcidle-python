from src.networking.packets.serverbound import *


print(KeepAlive(ID=4).write())
print(EncryptionRequest(ServerId="test.org", PubKey="adsojdasjlkadsjkasdkj", Token="asdflkdslkfdslkfds").write(30))
