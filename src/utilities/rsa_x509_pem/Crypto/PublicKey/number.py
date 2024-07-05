#
#   number.py : Number-theoretic functions
#
#  Part of the Python Cryptography Toolkit
#
# Distribute and use freely; there are no restrictions on further
# dissemination and usage except those imposed by the laws of your
# country of residence.  This software is provided "as is" without
# warranty of fitness for use or suitability for any purpose, express
# or implied. Use at your own risk or not at all.
#

#import sateraito_logger as logging

__revision__ = "$Id: number.py,v 1.13 2003/04/04 18:21:07 akuchling Exp $"

# GAEGEN2対応
#bignum = long
bignum = int
try:
    from Crypto.PublicKey import _fastmath
except ImportError:
    _fastmath = None

# Commented out and replaced with faster versions below
## def long2str(n):
##     s=''
##     while n>0:
##         s=chr(n & 255)+s
##         n=n>>8
##     return s

## import types
## def str2long(s):
##     if type(s)!=types.StringType: return s   # Integers will be left alone
##     return reduce(lambda x,y : x*256+ord(y), s, 0L)

def size(N):
    """size(N:long) : int
    Returns the size of the number N in bits.
    """
    # GAEGEN2対応
    #bits, power = 0, 1L
    bits, power = 0, 1
    while N >= power:
        bits += 1
        power = power << 1
    return bits


def getRandomNumber(N, randfunc):
    """getRandomNumber(N:int, randfunc:callable):long
    Return an N-bit random number."""

    S = randfunc(N / 8)
    odd_bits = N % 8
    if odd_bits != 0:
        char = ord(randfunc(1)) >> (8 - odd_bits)
        S = chr(char) + S
    value = bytes_to_long(S)
    # GAEGEN2対応
    #value |= 2L ** (N - 1)                # Ensure high bit is set
    value |= 2 ** (N - 1)                # Ensure high bit is set
    assert size(value) >= N
    return value


def GCD(x, y):
    """GCD(x:long, y:long): long
    Return the GCD of x and y.
    """
    x = abs(x)
    y = abs(y)
    while x > 0:
        x, y = y % x, x
    return y


def inverse(u, v):
    """inverse(u:long, u:long):long
    Return the inverse of u mod v.
    """
    # GAEGEN2対応
    #u3, v3 = long(u), long(v)
    u3, v3 = int(u), int(v)
    # GAEGEN2対応
    #u1, v1 = 1L, 0L
    u1, v1 = 1, 0
    while v3 > 0:
        q = u3 / v3
        u1, v1 = v1, u1 - v1 * q
        u3, v3 = v3, u3 - v3 * q
    while u1 < 0:
        u1 = u1 + v
    return u1

# Given a number of bits to generate and a random generation function,
# find a prime number of the appropriate size.

def getPrime(N, randfunc):
    """getPrime(N:int, randfunc:callable):long
    Return a random N-bit prime number.
    """

    number = getRandomNumber(N, randfunc) | 1
    while (not isPrime(number)):
        number = number + 2
    return number


def isPrime(N):
    """isPrime(N:long):bool
    Return true if N is prime.
    """
    if N == 1:
        return 0
    if N in sieve:
        return 1
    for i in sieve:
        if (N % i) == 0:
            return 0

    # Use the accelerator if available
    if _fastmath is not None:
        return _fastmath.isPrime(N)

    # Compute the highest bit that's set in N
    # GAEGEN2対応
    #N1 = N - 1L
    #n = 1L
    #while (n < N):
    #    n = n << 1L
    #n = n >> 1L
    N1 = N - 1
    n = 1
    while (n < N):
        n = n << 1
    n = n >> 1

    # Rabin-Miller test
    for c in sieve[:7]:
        # GAEGEN2対応
        #a = long(c)
        #d = 1L
        a = int(c)
        d = 1
        t = n
        while (t):  # Iterate over the bits in N1
            x = (d * d) % N
            # GAEGEN2対応
            #if x == 1L and d != 1L and d != N1:
            if x == 1 and d != 1 and d != N1:
                return 0  # Square root of 1 found
            if N1 & t:
                d = (x * a) % N
            else:
                d = x
            # GAEGEN2対応
            #t = t >> 1L
            t = t >> 1
        # GAEGEN2対応
        #if d != 1L:
        if d != 1:
            return 0
    return 1

# Small primes used for checking primality; these are all the primes
# less than 256.  This should be enough to eliminate most of the odd
# numbers before needing to do a Rabin-Miller test at all.

sieve = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59,
         61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127,
         131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193,
         197, 199, 211, 223, 227, 229, 233, 239, 241, 251]

# Improved conversion functions contributed by Barry Warsaw, after
# careful benchmarking

import struct


# GAEGEN2対応：pycryptodomeのUtil.number.pyの「long_to_bytes」をコピーして使用
#def long_to_bytes(n, blocksize=0):
#    """long_to_bytes(n:long, blocksize:int) : string
#    Convert a long integer to a byte string.
#
#    If optional blocksize is given and greater than zero, pad the front of the
#    byte string with binary zeros so that the length is a multiple of
#    blocksize.
#    """
#    logging.debug('long_to_bytes=%s' % (n))
#    # after much testing, this algorithm was deemed to be the fastest
#    # GAEGEN2対応
#    #s = ''
#    s = b''
#    # GAEGEN2対応
#    #n = long(n)
#    n = int(n)
#    pack = struct.pack
#    while n > 0:
#        # GAEGEN2対応
#        #s = pack('>I', n & 0xffffffffL) + s
#        s = pack('>I', n & 0xffffffff) + s
#        n = n >> 32
#        # strip off leading zeros
#    for i in range(len(s)):
#        # GAEGEN2対応
#        #if s[i] != '\000':
#        if s[i] != b'\000':
#            break
#    else:
#        # only happens when n == 0
#        # GAEGEN2対応
#        #s = '\000'
#        s = b'\000'
#        i = 0
#    s = s[i:]
#    # add back some pad bytes.  this could be done more efficiently w.r.t. the
#    # de-padding being done above, but sigh...
#    if blocksize > 0 and len(s) % blocksize:
#        # GAEGEN2対応
#        #s = (blocksize - len(s) % blocksize) * '\000' + s
#        s = (blocksize - len(s) % blocksize) * b'\x00' + s
#    logging.debug('long_to_bytes=%s' % (s))
#    return s
def long_to_bytes(n, blocksize=0):
    """Convert a positive integer to a byte string using big endian encoding.

    If :data:`blocksize` is absent or zero, the byte string will
    be of minimal length.

    Otherwise, the length of the byte string is guaranteed to be a multiple
    of :data:`blocksize`. If necessary, zeroes (``\\x00``) are added at the left.

    .. note::
        In Python 3, if you are sure that :data:`n` can fit into
        :data:`blocksize` bytes, you can simply use the native method instead::

            >>> n.to_bytes(blocksize, 'big')

        For instance::

            >>> n = 80
            >>> n.to_bytes(2, 'big')
            b'\\x00P'

        However, and unlike this ``long_to_bytes()`` function,
        an ``OverflowError`` exception is raised if :data:`n` does not fit.
    """

    if n < 0 or blocksize < 0:
        raise ValueError("Values must be non-negative")

    result = []
    pack = struct.pack

    # Fill the first block independently from the value of n
    bsr = blocksize
    while bsr >= 8:
        result.insert(0, pack('>Q', n & 0xFFFFFFFFFFFFFFFF))
        n = n >> 64
        bsr -= 8

    while bsr >= 4:
        result.insert(0, pack('>I', n & 0xFFFFFFFF))
        n = n >> 32
        bsr -= 4

    while bsr > 0:
        result.insert(0, pack('>B', n & 0xFF))
        n = n >> 8
        bsr -= 1

    if n == 0:
        if len(result) == 0:
            bresult = b'\x00'
        else:
            bresult = b''.join(result)
    else:
        # The encoded number exceeds the block size
        while n > 0:
            result.insert(0, pack('>Q', n & 0xFFFFFFFFFFFFFFFF))
            n = n >> 64
        result[0] = result[0].lstrip(b'\x00')
        bresult = b''.join(result)
        # bresult has minimum length here
        if blocksize > 0:
            target_len = ((len(bresult) - 1) // blocksize + 1) * blocksize
            bresult = b'\x00' * (target_len - len(bresult)) + bresult

    return bresult


def bytes_to_long(s):
    """bytes_to_long(string) : long
    Convert a byte string to a long integer.

    This is (essentially) the inverse of long_to_bytes().
    """
    # GAEGEN2対応
    #acc = 0L
    acc = 0
    unpack = struct.unpack
    length = len(s)
    if length % 4:
        extra = (4 - length % 4)
        # GAEGEN2対応
        #s = '\000' * extra + s
        s = b'\x00' * extra + s
        length = length + extra
    for i in range(0, length, 4):
        acc = (acc << 32) + unpack('>I', s[i:i + 4])[0]
    return acc

# For backwards compatibility...
import warnings


def long2str(n, blocksize=0):
    warnings.warn("long2str() has been replaced by long_to_bytes()")
    return long_to_bytes(n, blocksize)


def str2long(s):
    warnings.warn("str2long() has been replaced by bytes_to_long()")
    return bytes_to_long(s)
