"""Send a file safely to the QNX unit as hex over its Telnet console."""
import argparse
import getpass
import hashlib
import os
import socket
import time


def negotiate(sock, data):
    clean = bytearray()
    index = 0
    while index < len(data):
        if data[index] == 255 and index + 2 < len(data):
            command, option = data[index + 1], data[index + 2]
            sock.sendall(bytes((255, 254 if command in (251, 252) else 252, option)))
            index += 3
        else:
            clean.append(data[index])
            index += 1
    return bytes(clean)


def expect(sock, token, timeout=15):
    data = bytearray()
    deadline = time.time() + timeout
    while token not in data:
        if time.time() >= deadline:
            raise TimeoutError("Telnet prompt not received: " + repr(token))
        try:
            data.extend(negotiate(sock, sock.recv(8192)))
        except TimeoutError:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("target")
    parser.add_argument("--host", default="172.16.250.248")
    parser.add_argument("--user", default="root")
    args = parser.parse_args()
    password = os.environ.get("CW_TELNET_PASSWORD") or getpass.getpass()
    payload = open(args.source, "rb").read()
    sock = socket.create_connection((args.host, 23), timeout=10)
    sock.settimeout(0.25)
    expect(sock, b"login:")
    sock.sendall((args.user + "\n").encode("ascii"))
    expect(sock, b"Password:")
    sock.sendall((password + "\n").encode("ascii"))
    expect(sock, b"# ")
    target = args.target + ".hex"
    sock.sendall(("rm -f " + target + "; : > " + target + "; echo CW_BEGIN\n").encode("ascii"))
    expect(sock, b"CW_BEGIN")
    sock.sendall(bytes((255, 251, 0, 255, 253, 0)))
    time.sleep(0.2)
    sock.sendall(("stty raw -echo; cat > " + target + "\n").encode("ascii"))
    time.sleep(0.5)
    sock.sendall(payload.hex().encode("ascii"))
    sock.shutdown(socket.SHUT_WR)
    time.sleep(1)
    sock.close()
    print("SIZE=" + str(len(payload)) + " SHA256=" + hashlib.sha256(payload).hexdigest())


if __name__ == "__main__":
    main()
