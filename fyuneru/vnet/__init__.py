# -*- coding: utf-8 -*-

from logging import info, debug
from multiprocessing import Process, Pipe
from select import select

from pytun import TunTapDevice

from ..util import crypto, droproot, debugging



class VirtualNetworkInterface:
    
    def __init__(self, config):
        self.__tun = TunTapDevice()
        self.__tun.addr = config["ip"]
        self.__tun.dstaddr = config["dstip"]
        self.__tun.netmask = config["netmask"]

    def up(self):
        self.__tun.up()
        info(\
            """%s: mtu %d  addr %s  netmask %s  dstaddr %s""" % \
            (\
                self.__tun.name, 
                self.__tun.mtu, 
                self.__tun.addr, 
                self.__tun.netmask, 
                self.__tun.dstaddr
            )
        )

    def fileno(self):
        return self.__tun.fileno()

    def write(self, buf):
        self.__tun.write(buf)

    def read(self):
        return self.__tun.read(65536)



def __vNetProcess(pipe, config):
    tun = VirtualNetworkInterface(config)
    droproot.dropRoot(*config["user"])

    crypt = crypto.Crypto(config["key"])
    encrypt, decrypt = crypt.encrypt, crypt.decrypt
    
    selects = {tun: "tun", pipe: "pipe"}
    while True:
        r = select(selects.keys(), [], [], 1.0)[0]
        if len(r) < 1: continue
        for each in r:
            if selects[each] == "tun":
                buf = each.read()
                pipe.send(encrypt(buf))
                debug(debugging.showPacket(buf))

            if selects[each] == "pipe":
                buf = each.recv()
                buf = decrypt(buf)
                if buf:
                    tun.write(buf)
                    debug(debugging.showPacket(buf))
    return        
   

def start(config):
    pipeA, pipeB = Pipe()
    proc = Process(target=__vNetProcess, args=(pipeB, config))
    proc.start()
    return (pipeA, proc)
