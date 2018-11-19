from io import BytesIO


class PacketBuffer:
    """ Wrapper around BytesIO """
    def __init__(self):
        self.bytes = BytesIO()

    def write(self, value):
        return self.bytes.write(value)

    def read(self, length=None):
        return self.bytes.read(length)

    def clear(self):
        self.bytes = BytesIO()

    def reset_cursor(self):
        self.bytes.seek(0)

    def get_bytes(self):
        return self.bytes.getvalue()

    # Hex representation of bytes array
    def __str__(self):
        return ' '.join(["%02X" % b for b in self.bytes.getvalue()])