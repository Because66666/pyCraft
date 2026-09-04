"""Contains definitions for minecraft's different data types
Each type has a method which is used to read and write it.
These definitions and methods are used by the packet definitions
"""
import math
import struct
import uuid
import io

import pynbt

from .utility import Vector, class_and_instancemethod


__all__ = (
    'Type', 'Boolean', 'UnsignedByte', 'Byte', 'Short', 'UnsignedShort',
    'Integer', 'FixedPoint', 'FixedPointInteger', 'Angle', 'VarInt', 'VarLong',
    'Long', 'UnsignedLong', 'Float', 'Double', 'ShortPrefixedByteArray',
    'VarIntPrefixedByteArray', 'TrailingByteArray', 'String', 'UUID',
    'Position', 'LpVec3', 'NBT', 'PrefixedArray', 'PrefixedOptional',
)


class Type(object):
    # pylint: disable=no-self-argument
    __slots__ = ()

    @class_and_instancemethod
    def read_with_context(cls_or_self, file_object, _context):
        return cls_or_self.read(file_object)

    @class_and_instancemethod
    def send_with_context(cls_or_self, value, socket, _context):
        return cls_or_self.send(value, socket)

    @classmethod
    def read(cls, file_object):
        if cls.read_with_context == Type.read_with_context:
            raise NotImplementedError('One of "read" or "read_with_context" '
                                      'must be overridden in a subclass.')
        else:
            raise TypeError('This type requires a ConnectionContext: '
                            'call "read_with_context" instead of "read".')

    @classmethod
    def send(cls, value, socket):
        if cls.send_with_context == Type.send_with_context:
            raise NotImplementedError('One of "send" or "send_with_context" '
                                      'must be overridden in a subclass.')
        else:
            raise TypeError('This type requires a ConnectionContext: '
                            'call "send_with_context" instead of "send".')


class Boolean(Type):
    @staticmethod
    def read(file_object):
        return struct.unpack('?', file_object.read(1))[0]

    @staticmethod
    def send(value, socket):
        socket.send(struct.pack('?', value))


class UnsignedByte(Type):
    @staticmethod
    def read(file_object):
        return struct.unpack('>B', file_object.read(1))[0]

    @staticmethod
    def send(value, socket):
        socket.send(struct.pack('>B', value))


class Byte(Type):
    @staticmethod
    def read(file_object):
        return struct.unpack('>b', file_object.read(1))[0]

    @staticmethod
    def send(value, socket):
        socket.send(struct.pack('>b', value))


class Short(Type):
    @staticmethod
    def read(file_object):
        return struct.unpack('>h', file_object.read(2))[0]

    @staticmethod
    def send(value, socket):
        socket.send(struct.pack('>h', value))


class UnsignedShort(Type):
    @staticmethod
    def read(file_object):
        return struct.unpack('>H', file_object.read(2))[0]

    @staticmethod
    def send(value, socket):
        socket.send(struct.pack('>H', value))


class Integer(Type):
    @staticmethod
    def read(file_object):
        return struct.unpack('>i', file_object.read(4))[0]

    @staticmethod
    def send(value, socket):
        socket.send(struct.pack('>i', value))


class FixedPoint(Type):
    __slots__ = 'integer_type', 'denominator'

    def __init__(self, integer_type, fractional_bits=5):
        self.integer_type = integer_type
        self.denominator = 2**fractional_bits

    def read(self, file_object):
        return self.integer_type.read(file_object) / self.denominator

    def send(self, value, socket):
        self.integer_type.send(int(value * self.denominator))


# This named instance is retained for backward compatibility:
FixedPointInteger = FixedPoint(Integer)


class Angle(Type):
    @staticmethod
    def read(file_object):
        # Linearly transform angle in steps of 1/256 into steps of 1/360
        return 360 * UnsignedByte.read(file_object) / 256

    @staticmethod
    def send(value, socket):
        # Normalize angle between 0 and 255 and convert to int.
        UnsignedByte.send(round(256 * ((value % 360) / 360)), socket)


class VarInt(Type):
    max_bytes = 5

    @classmethod
    def read(cls, file_object):
        number = 0
        # Limit of 'cls.max_bytes' bytes, otherwise its possible to cause
        # a DOS attack by sending VarInts that just keep going
        bytes_encountered = 0
        while True:
            byte = file_object.read(1)
            if len(byte) < 1:
                raise EOFError("Unexpected end of message.")

            byte = ord(byte)
            number |= (byte & 0x7F) << 7 * bytes_encountered
            if not byte & 0x80:
                break

            bytes_encountered += 1
            if bytes_encountered > cls.max_bytes:
                raise ValueError("Tried to read too long of a VarInt")
        return number

    @staticmethod
    def send(value, socket):
        out = bytes()
        while True:
            byte = value & 0x7F
            value >>= 7
            out += struct.pack("B", byte | (0x80 if value > 0 else 0))
            if value == 0:
                break
        socket.send(out)

    @staticmethod
    def size(value):
        for max_value, size in VARINT_SIZE_TABLE.items():
            if value < max_value:
                return size
        raise ValueError("Integer too large")


class VarLong(VarInt):
    max_bytes = 10


# Maps (maximum integer value -> size of VarInt in bytes)
VARINT_SIZE_TABLE = {
    2 ** 7: 1,
    2 ** 14: 2,
    2 ** 21: 3,
    2 ** 28: 4,
    2 ** 35: 5,
    2 ** 42: 6,
    2 ** 49: 7,
    2 ** 56: 8,
    2 ** 63: 9,
    2 ** 70: 10,
    2 ** 77: 11,
    2 ** 84: 12
}


class Long(Type):
    @staticmethod
    def read(file_object):
        return struct.unpack('>q', file_object.read(8))[0]

    @staticmethod
    def send(value, socket):
        socket.send(struct.pack('>q', value))


class UnsignedLong(Type):
    @staticmethod
    def read(file_object):
        return struct.unpack('>Q', file_object.read(8))[0]

    @staticmethod
    def send(value, socket):
        socket.send(struct.pack('>Q', value))


class Float(Type):
    @staticmethod
    def read(file_object):
        return struct.unpack('>f', file_object.read(4))[0]

    @staticmethod
    def send(value, socket):
        socket.send(struct.pack('>f', value))


class Double(Type):
    @staticmethod
    def read(file_object):
        return struct.unpack('>d', file_object.read(8))[0]

    @staticmethod
    def send(value, socket):
        socket.send(struct.pack('>d', value))


class ShortPrefixedByteArray(Type):
    @staticmethod
    def read(file_object):
        length = Short.read(file_object)
        return struct.unpack(str(length) + "s", file_object.read(length))[0]

    @staticmethod
    def send(value, socket):
        Short.send(len(value), socket)
        socket.send(value)


class VarIntPrefixedByteArray(Type):
    @staticmethod
    def read(file_object):
        length = VarInt.read(file_object)
        return struct.unpack(str(length) + "s", file_object.read(length))[0]

    @staticmethod
    def send(value, socket):
        VarInt.send(len(value), socket)
        socket.send(struct.pack(str(len(value)) + "s", value))


class TrailingByteArray(Type):
    """ A byte array consisting of all remaining data. If present in a packet
        definition, this should only be the type of the last field. """

    @staticmethod
    def read(file_object):
        return file_object.read()

    @staticmethod
    def send(value, socket):
        socket.send(value)


class String(Type):
    @staticmethod
    def read(file_object):
        length = VarInt.read(file_object)
        return file_object.read(length).decode("utf-8")

    @staticmethod
    def send(value, socket):
        value = value.encode('utf-8')
        VarInt.send(len(value), socket)
        socket.send(value)


class UUID(Type):
    @staticmethod
    def read(file_object):
        return str(uuid.UUID(bytes=file_object.read(16)))

    @staticmethod
    def send(value, socket):
        socket.send(uuid.UUID(value).bytes)


class Position(Type, Vector):
    """3D position vectors with a specific, compact network representation."""
    __slots__ = ()

    @staticmethod
    def read_with_context(file_object, context):
        location = UnsignedLong.read(file_object)
        x = int(location >> 38)                # 26 most significant bits

        if context.protocol_later_eq(443):
            z = int((location >> 12) & 0x3FFFFFF)  # 26 intermediate bits
            y = int(location & 0xFFF)              # 12 least signficant bits
        else:
            y = int((location >> 26) & 0xFFF)      # 12 intermediate bits
            z = int(location & 0x3FFFFFF)          # 26 least significant bits

        if x >= pow(2, 25):
            x -= pow(2, 26)

        if y >= pow(2, 11):
            y -= pow(2, 12)

        if z >= pow(2, 25):
            z -= pow(2, 26)

        return Position(x=x, y=y, z=z)

    @staticmethod
    def send_with_context(position, socket, context):
        # 'position' can be either a tuple or Position object.
        x, y, z = position
        value = ((x & 0x3FFFFFF) << 38 | (z & 0x3FFFFFF) << 12 | (y & 0xFFF)
                 if context.protocol_later_eq(443) else
                 (x & 0x3FFFFFF) << 38 | (y & 0xFFF) << 26 | (z & 0x3FFFFFF))
        UnsignedLong.send(value, socket)


class LpVec3(Type, Vector):
    """A variable-length, quantized 3D vector of floats, introduced in
       protocol 773 (1.21.9) for entity velocities. A zero vector is a
       single zero byte; otherwise the vector is packed into 6 bytes,
       optionally followed by a VarInt scale continuation."""
    __slots__ = ()

    _MAX_QUANTIZED_VALUE = 32766.0
    _ABS_MIN_VALUE = 3.051944088384301e-05
    _ABS_MAX_VALUE = 1.7179869183e10

    @staticmethod
    def _unpack(packed, shift):
        quantized = min((packed >> shift) & 0x7FFF,
                        int(LpVec3._MAX_QUANTIZED_VALUE))
        return quantized * 2.0 / LpVec3._MAX_QUANTIZED_VALUE - 1.0

    @staticmethod
    def read(file_object):
        first = UnsignedByte.read(file_object)
        if first == 0:
            return LpVec3(0.0, 0.0, 0.0)
        packed = first \
            + (UnsignedByte.read(file_object) << 8) \
            + (struct.unpack('>I', file_object.read(4))[0] << 16)
        scale = first & 3
        if first & 4:
            scale += VarInt.read(file_object) * 4
        return LpVec3(*(LpVec3._unpack(packed, shift) * scale
                        for shift in (3, 18, 33)))

    @staticmethod
    def send(value, socket):
        def sanitize(component):
            return max(-LpVec3._ABS_MAX_VALUE,
                       min(float(component), LpVec3._ABS_MAX_VALUE))

        x, y, z = (sanitize(component) for component in value)
        maximum = max(abs(x), abs(y), abs(z))
        if maximum < LpVec3._ABS_MIN_VALUE:
            UnsignedByte.send(0, socket)
            return

        scale = int(math.ceil(maximum))
        continuation = scale > 3
        markers = (scale % 4) | 4 if continuation else scale

        def pack(component):
            return int(math.floor(
                (component / scale * 0.5 + 0.5) * 32766 + 0.5))

        packed = markers + (pack(x) << 3) + (pack(y) << 18) \
            + (pack(z) << 33)
        UnsignedByte.send(packed & 0xFF, socket)
        UnsignedByte.send((packed >> 8) & 0xFF, socket)
        socket.send(struct.pack('>I', (packed >> 16) & 0xFFFFFFFF))
        if continuation:
            VarInt.send(scale // 4, socket)


class NBT(Type):
    @staticmethod
    def read(file_object):
        return pynbt.NBTFile(io=file_object)

    @staticmethod
    def send(value, socket):
        buffer = io.BytesIO()
        pynbt.NBTFile(value=value).save(buffer)
        socket.send(buffer.getvalue())

    @staticmethod
    def read_with_context(file_object, context):
        if context.protocol_earlier(764):
            return NBT.read(file_object)
        # In protocol 764 and later, the root tag is anonymous: the type
        # byte is followed directly by the payload, with no root name.
        tag_type = file_object.read(1)
        if tag_type == b'\x00':
            # A zero type byte encodes an empty compound.
            return pynbt.NBTFile()
        # Present the stream to pynbt as a named root tag by prefixing the
        # type byte with a zero-length root name.
        return pynbt.NBTFile(io=_AnonymousRootReader(tag_type, file_object))

    @staticmethod
    def send_with_context(value, socket, context):
        if context.protocol_earlier(764):
            return NBT.send(value, socket)
        if value is None or len(value) == 0:
            # An empty compound is encoded as a single zero type byte.
            socket.send(b'\x00')
            return
        buffer = io.BytesIO()
        pynbt.NBTFile(value=value).save(buffer)
        data = buffer.getvalue()
        # Strip the (always empty) root name: keep the leading type byte
        # and skip the following two-byte name length.
        socket.send(data[:1] + data[3:])


class _AnonymousRootReader(object):
    """ A file-like object that serves the given prefix bytes followed by
        the contents of an underlying file-like object. Used to present an
        anonymous-root NBT tag to pynbt as a named root tag. """
    __slots__ = 'prefix', 'file_object'

    def __init__(self, prefix, file_object):
        self.prefix = io.BytesIO(prefix + b'\x00\x00')
        self.file_object = file_object

    def read(self, length=-1):
        if length is None or length < 0:
            return self.prefix.read() + self.file_object.read()
        head = self.prefix.read(length)
        return head + self.file_object.read(length - len(head))


class PrefixedArray(Type):
    __slots__ = 'length_type', 'element_type'

    def __init__(self, length_type, element_type):
        self.length_type = length_type
        self.element_type = element_type

    def read(self, file_object):
        return self.__read(file_object, self.element_type.read)

    def send(self, value, socket):
        return self.__send(value, socket, self.element_type.send)

    def read_with_context(self, file_object, context):
        def element_read(file_object):
            return self.element_type.read_with_context(file_object, context)
        return self.__read(file_object, element_read)

    def send_with_context(self, value, socket, context):
        def element_send(value, socket):
            return self.element_type.send_with_context(value, socket, context)
        return self.__send(value, socket, element_send)

    def __read(self, file_object, element_read):
        length = self.length_type.read(file_object)
        return [element_read(file_object) for i in range(length)]

    def __send(self, value, socket, element_send):
        self.length_type.send(len(value), socket)
        for element in value:
            element_send(element, socket)


class PrefixedOptional(Type):
    """ An optional value, prefixed by a Boolean indicating whether it is
        present. 'None' is read and written as an absent value. """
    __slots__ = 'element_type',

    def __init__(self, element_type):
        self.element_type = element_type

    def read(self, file_object):
        if Boolean.read(file_object):
            return self.element_type.read(file_object)

    def send(self, value, socket):
        Boolean.send(value is not None, socket)
        if value is not None:
            self.element_type.send(value, socket)

    def read_with_context(self, file_object, context):
        if Boolean.read(file_object):
            return self.element_type.read_with_context(file_object, context)

    def send_with_context(self, value, socket, context):
        Boolean.send(value is not None, socket)
        if value is not None:
            self.element_type.send_with_context(value, socket, context)
