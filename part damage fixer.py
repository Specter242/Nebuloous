import os
import time
import xml.etree.ElementTree as ET
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def find_nebulous_folder():
    possible_paths = [
        r"C:\Program Files (x86)\Steam\steamapps\common\Nebulous",
        r"C:\Program Files\Steam\steamapps\common\Nebulous",
        r"C:\Program Files (x86)\Nebulous",
        r"C:\Program Files\Nebulous",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

NEBULOUS_DIR = find_nebulous_folder()
if NEBULOUS_DIR is None:
    raise FileNotFoundError("Nebulous folder not found in any of the expected locations.")

REPORTS_DIR = os.path.join(NEBULOUS_DIR, "Saves", "SkirmishReports")
FLEETS_DIR = os.path.join(NEBULOUS_DIR, "Saves", "Fleets")

class ReportHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".xml"):
            time.sleep(1)  # Delay to allow the report to fully populate
            process_skirmish_report(event.src_path)

def process_skirmish_report(report_path):
    skirmishreporttree = ET.parse(report_path)
    root1 = skirmishreporttree.getroot()

    # parse the second XML file
    file_name2 = "ANTI-MSL MSL.fleet"
    full_file_path2 = os.path.join(FLEETS_DIR, "testfolder", "test2", file_name2)
    fleettree = ET.parse(full_file_path2)
    root2 = fleettree.getroot()

    Ship_battle_report_list = root1.findall('.//ShipBattleReport')
    ship_list = root2.findall('.//Ship')

    deadlist = list()

    for ship in Ship_battle_report_list:
        if ship.find(".//Eliminated").text == 'Destroyed' or ship.find(".//Eliminated").text == 'Evacuated':
            namefromsbr = ship.find('.//ShipName').text
            namefromsbr = namefromsbr.split(" ", 1)[-1]
            deadlist.append(namefromsbr)

    for ship in ship_list:  # each ship object in fleet file
        for sbr in Ship_battle_report_list:  # each ship battle report from after action
            namefromsbr = sbr.find('.//ShipName').text
            namefromsbr = namefromsbr.split(" ", 1)[-1]

            if ship.find('.//Name').text == namefromsbr:  # if name of ship from fleet file matches ship battle report name entry
                offensive_missile_report_list = sbr.findall('.//OffensiveMissileReport')
                mag_save_data_list = ship.findall('.//MagSaveData')
                total_missiles_remain = 0
                for offensive_missile_report in offensive_missile_report_list:
                    missile_name = offensive_missile_report.find('.//MissileName').text
                    for mag_save_data in mag_save_data_list:
                        munition_key = mag_save_data.find('.//MunitionKey').text
                        munition_key = munition_key.split("/")[-1]
                        if missile_name == munition_key:
                            total_missiles_remain = int(offensive_missile_report.find('.//TotalCarried').text) - int(offensive_missile_report.find('.//TotalExpended').text)
                            mag_save_data.find('.//Quantity').text = str(total_missiles_remain)

                parts = ship.find('.//Parts')
                sockets = ship.findall('.//HullSocket')

                weaponreports = sbr.findall('.//WeaponReport')
                defweaponreports = sbr.findall('.//DefensiveWeaponReport')

                restoresconsumed = int(sbr.find('.//RestoresTotal').text) - int(sbr.find('.//RestoresRemaining').text)

                ammodict = {}
                for weapons in weaponreports:
                    ammodict.update({weapons.find('.//Name').text.split("- ", 1)[-1]: int(weapons.find('.//ShotsFired').text)})
                for weapons in defweaponreports:
                    ammodict.update({weapons.find('.//Name').text.split("- ", 1)[-1]: int(weapons.find('.//ShotsFired').text)})

                for socket in sockets:
                    socketname = socket.find('.//ComponentName').text
                    socketname = socketname.split("/", 1)[-1]
                    if socketname == 'Large DC Locker' or socketname == 'Small DC Locker' or socketname == 'Reinforced DC Locker' or socketname == 'Rapid DC Locker':
                        if restoresconsumed > 0:
                            socketval = int(socket.find('.//RestoresConsumed').text)
                            socketval = socketval + 1
                            socket.find('.//RestoresConsumed').text = str(socketval)
                            restoresconsumed = restoresconsumed - 1

                    if socketname == 'Reinforced Magazine' or socketname == 'Bulk Magazine':
                        magazines = socket.findall('.//MagSaveData')
                        for mag in magazines:
                            for key in ammodict:
                                if key == mag.find('.//MunitionKey').text.split("/", 1)[-1]:
                                    while ammodict[key] > 0:
                                        num = int(mag.find('.//Quantity').text) - 1
                                        mag.find('.//Quantity').text = str(num)
                                        ammodict[key] = ammodict[key] - 1

                for x in sbr.findall('.//PartDamage'):
                    for each in parts:
                        if x.find('.//Key').text == each.find('.//Key').text:
                            each.find('.//Destroyed').text = x.find('.//IsDestroyed').text
                            health_percent = float(x.find('.//HealthPercent').text)
                            hp = float(each.find('.//HP').text)
                            hp = hp * health_percent
                            each.find('.//HP').text = str(hp)

    for each in root2.findall('.//Ships'):
        for y in each.findall('.//Ship'):
            for x in deadlist:
                if y.find('.//Name').text == x:
                    each.remove(y)

    fleettree.write('modified_3K_Heavy.fleet')

def monitor_reports():
    observer = Observer()
    event_handler = ReportHandler()
    observer.schedule(event_handler, REPORTS_DIR, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    monitor_reports()