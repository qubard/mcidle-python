from io import BytesIO


class PacketBuffer:
    """ Wrapper around BytesIO """
    def __init__(self):
        self.bytes_ = BytesIO()

    def write(self, value):
        return self.bytes_.write(value)

    def read(self, length=None):
        return self.bytes_.read(length)

    def clear(self):
        self.bytes_ = BytesIO()

    def reset_cursor(self):
        self.bytes_.seek(0)

    def __len__(self):
        return len(self.bytes)

    @property
    def bytes(self):
        return self.bytes_.getvalue()

    # Hex representation of bytes array
    def __str__(self):
        return ' '.join(["%02X" % b for b in self.bytes_.getvalue()])
