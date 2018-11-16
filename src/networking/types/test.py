from basic import *

import io

with io.BytesIO() as f:
    String.write("Hello, world.", f)
    print(f.getvalue(), f.tell())
    f.seek(0)
    s = String.read(f)
    print(s)
