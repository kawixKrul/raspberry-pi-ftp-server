# main.py
import time

import machine
import os
import sdcard
from logger import Logger
import time

from ftpserver import FTPServer
from wifi import connect_wifi
from tamper import FileTamper
from utils import load_env

MONITORED_FILES = ["/sd/document.txt"]

def mount_sdcard():
    spi = machine.SPI(1, sck=machine.Pin(10), mosi=machine.Pin(11), miso=machine.Pin(12))
    cs = machine.Pin(13, machine.Pin.OUT)
    try:
        sd = sdcard.SDCard(spi, cs)
        os.mount(sd, "/sd")
        Logger.log_info("Karta SD zamontowana.")
        return True
    except Exception as e:
        Logger.log_alert(f"Nie wykryto karty SD lub błąd montowania: {e}")
        return False


def main():
    if not mount_sdcard():
        return

    env = load_env(".env")
    ssid = env["SSID"]
    password = env["PASSWORD"]
    ftp_user = env["FTP_USER"]
    ftp_pass = env["FTP_PASS"]
    ftp_port = int(env["FTP_PORT"])
    print(ssid, password, ftp_user, ftp_pass, ftp_port, sep='\n')
    connect_wifi(ssid, password)


    for filename in MONITORED_FILES:
        if filename not in ["/sd/" + f for f in os.listdir("/sd")]:
            with open(filename, "w") as f:
                f.write("Plik chroniony tamper detection!\n")

    for filename in MONITORED_FILES:
        if FileTamper.init_file_hash(filename):
            Logger.log_info(f"Zainicjowano hash dla pliku {filename}")
        else:
            Logger.log_alert(f"Błąd inicjalizacji hash dla pliku {filename}")
    
    ftp = FTPServer(username=ftp_user, password=ftp_pass, port=ftp_port)
    ftp.start()
    Logger.log_info("Serwer FTP uruchomiony.")

    try:
        while True: 
            ftp.poll()
            time.sleep(2)
            for filename in MONITORED_FILES:
                FileTamper.check_file_changed(filename)
    except KeyboardInterrupt:
        Logger.log_info("Serwer zatrzymany.")

if __name__ == "__main__":
    Logger.init()
    try:
        main()
    except Exception as e:
        Logger.log_alert(f"Nieoczekiwany błąd: {e}")
        machine.reset()