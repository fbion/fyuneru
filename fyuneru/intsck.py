# -*- coding: utf-8 -*-

"""
Internal Fyuneru Socket for Proxy Processes

A fyuneru socket basing on UDP socket is defined. It is always a listening UDP
socket on a port in local addr, which does automatic handshake with given
internal magic word, and provides additionally abilities like encryption
underlays, traffic statistics, etc.
"""

import os
import sys
import hashlib
from time import time
from struct import pack, unpack
from socket import socket, AF_UNIX, SOCK_DGRAM
from fyuneru.crypto import Crypto

UDPCONNECTOR_WORD = \
    "Across the Great Wall, we can reach every corner in the world."

class InternalSocket:

    __sockpath = None
    __sock = None

    peer = None

    sendtiming = 0
    recvtiming = 0

    def __init__(self, key):
        self.__crypto = Crypto(key)
        self.__sock = socket(AF_UNIX, SOCK_DGRAM)

    def __getattr__(self, name):
        return getattr(self.__sock, name)

    def getUNIXSocketPathByName(self, socketName):
        pid = str(os.getpid())
        socketid = hashlib.sha1(socketName).hexdigest()
        socketFile = '.fyuneru-intsck-%s-%s' % (pid, socketid)
        return os.path.join('/', 'tmp', socketFile) 

    def close(self):
        # close socket
        print "Internal socket shutting down..."
        try:
            self.__sock.close()
        except Exception,e:
            print "Error closing socket: %s" % e
        # remove socket file
        try:
            if None != self.__sockpath:
                os.remove(self.__sockpath)
        except Exception,e:
            print "Error removing UNIX socket: %s" % e

    def bind(self, name):
        socketPath = self.getUNIXSocketPathByName(name)
        if os.path.exists(socketPath):
            os.remove(socketPath)
        self.__sockpath = socketPath
        self.__sock.bind(self.__sockpath)

    def receive(self):
        buf, sender = self.__sock.recvfrom(65536)

        if buf.strip() == UDPCONNECTOR_WORD:
            # connection word received, answer
            self.peer = sender
            self.__sock.sendto(UDPCONNECTOR_WORD, sender)
            return None

        if self.peer != sender:
            # Sender has not made a handshake
            return None

        decryption = self.__crypto.decrypt(buf)
        if not decryption: return None

        if len(decryption) < 8: return None
        header = decryption[:8]
        timestamp = unpack('<d', header)[0]
        buf = decryption[8:]

        self.recvtiming = max(self.recvtiming, timestamp)
        return buf 

    def send(self, buf):
        if None == self.peer:
            return
        self.sendtiming = time()
        header = pack('<d', self.sendtiming)
        encryption = self.__crypto.encrypt(header + buf)
        self.__sock.sendto(encryption, self.peer)

    def __str__(self):
        """Pack this packet into a string."""
        buf = pack('<Bd', SIGN_DATAPACKET, self.timestamp)
