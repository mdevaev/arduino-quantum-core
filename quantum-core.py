#!/usr/bin/env python3


import struct
import time

import argh


# =====
def get_local_stat():
    import psutil
    with open("/proc/loadavg") as loadavg_file:
        averages = loadavg_file.readline().split()[:3]
        averages = tuple( float(avg) * 10 for avg in averages )
        return {
            "cpu":  psutil.cpu_percent(),
            "mem":  psutil.phymem_usage().percent,
            "la1":  averages[0],
            "la5":  averages[1],
            "la15": averages[2],
        }

class QuantumCore:
    def __init__(self, device):
        import serial
        self._tty = serial.Serial(device, 115200)

    def send(self, cpu, mem, la1, la5, la15):
        values = map(self._make_byte, (cpu, mem, la1, la5, la15))
        self._tty.write(struct.pack("<ccccc", *values))

    def _make_byte(self, value) :
        return bytes([int(value)])


# =====
@argh.arg("--device", default="/dev/ttyACM0")
@argh.arg("--interval", default=1, type=int)
def run_local(device=None, interval=None):
    qc = QuantumCore(device)
    while True:
        qc.send(**get_local_stat())
        time.sleep(interval)

@argh.arg("--url", default="http://localhost:8080")
@argh.arg("--device", default="/dev/ttyACM0")
@argh.arg("--interval", default=1, type=int)
def run_remote(url=None, device=None, interval=None):
    import requests
    import requests.exceptions

    qc = QuantumCore(device)
    while True:
        try:
            response = requests.get(url)
        except requests.exceptions.Timeout:
            raise
        if str(response.status_code)[0] != "5":  # 5xx
            response.raise_for_status()
        qc.send(**response.json())
        time.sleep(interval)

@argh.arg("--port", default=8080)
def run_server(port=None):
    import json
    import wsgiref.simple_server

    def application(env, start_response):
        start_response("200 OK", [("Content-Type", "application/json")])
        return [json.dumps(get_local_stat()).encode()]

    httpd = wsgiref.simple_server.make_server("", port, application)
    print("Serving HTTP on port {}...".format(port))

    httpd.serve_forever()

def main():
    parser = argh.ArghParser(description="Quantum Core -- hardware monitoring")
    parser.add_commands((
            run_local,
            run_remote,
            run_server,
        ))
    parser.dispatch()

if __name__ == "__main__":
    main()
