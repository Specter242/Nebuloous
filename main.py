import os
import time
import shutil
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
IN_THEATER_DIR = os.path.join(FLEETS_DIR, "In Theater")
if not os.path.exists(IN_THEATER_DIR):
    os.makedirs(IN_THEATER_DIR)

print(f"Monitoring directory: {REPORTS_DIR}")

class ReportHandler(FileSystemEventHandler):
    def on_created(self, event):
        print(f"File created: {event.src_path}")  # Log file creation
        if event.src_path.endswith(".xml"):
            time.sleep(1)  # Delay to allow the report to fully populate
            process_skirmish_report(event.src_path)

def process_skirmish_report(report_path):
    print(f"Processing report: {report_path}")
    try:
        tree = ET.parse(report_path)
    except PermissionError:
        print(f"Permission denied: {report_path}")
        return
    except Exception as e:
        print(f"Failed to process report {report_path}: {e}")
        return

    root = tree.getroot()
    local_team = root.find("LocalPlayerTeam").text
    print(f"Local team: {local_team}")

    fleet_prefix = ""
    for team in root.findall("Teams/TeamReportOfShipBattleReportCraftBattleReport"):
        if team.find("TeamID").text == local_team:
            player = team.find("Players/AARPlayerReportOfShipBattleReportCraftBattleReport")
            if player.find("IsLocalPlayer").text == "true":
                fleet_prefix = player.find("Colors/FleetPrefix").text if player.find("Colors/FleetPrefix") is not None else ""
                break

    print(f"Fleet prefix: {fleet_prefix}")

    for team in root.findall("Teams/TeamReportOfShipBattleReportCraftBattleReport"):
        if team.find("TeamID").text == local_team:
            player = team.find("Players/AARPlayerReportOfShipBattleReportCraftBattleReport")
            ships = player.findall("Ships/ShipBattleReport")
            active_ships = []
            
            for ship in ships:
                if ship.find("Eliminated").text == "NotEliminated":
                    ship_name = ship.find("ShipName").text
                    ship_name_without_prefix = ship_name.replace(fleet_prefix, "", 1).strip()
                    print(f"Original ship name: {ship_name}, Without prefix: {ship_name_without_prefix}")
                    active_ships.append(ship_name_without_prefix)
            
            print(f"Active ships: {active_ships}")
            fleet_path = find_matching_fleet(active_ships)
            if fleet_path:
                print(f"Matching fleet found: {fleet_path}")
                save_updated_fleet(fleet_path, ships)
            else:
                print("No matching fleet found")

def find_matching_fleet(ship_names):
    print(f"Finding matching fleet for ships: {ship_names}")
    for fleet_file in os.listdir(FLEETS_DIR):
        if fleet_file.endswith(".fleet"):
            tree = ET.parse(os.path.join(FLEETS_DIR, fleet_file))
            root = tree.getroot()
            fleet_ships = [ship.find("Name").text for ship in root.findall("Ships/Ship")]
            print(f"Fleet ships: {fleet_ships}")
            if set(ship_names).issubset(set(fleet_ships)):
                return os.path.join(FLEETS_DIR, fleet_file)
    return None

def save_updated_fleet(fleet_path, ships):
    print(f"Saving updated fleet: {fleet_path}")
    tree = ET.parse(fleet_path)
    root = tree.getroot()
    fleet_name = root.find("Name").text
    new_fleet_name = get_new_fleet_name(fleet_name)
    new_fleet_path = os.path.join(IN_THEATER_DIR, f"{new_fleet_name}.fleet")
    
    # Copy the original fleet file to the new location
    shutil.copy(fleet_path, new_fleet_path)
    
    # Load the copied fleet file for modification
    tree = ET.parse(new_fleet_path)
    root = tree.getroot()
    
    ship_elements = root.findall("Ships/Ship")
    for ship_elem in ship_elements:
        ship_name = ship_elem.find("Name").text
        report_ship = next((s for s in ships if s.find("ShipName").text.replace(s.find("FleetPrefix").text if s.find("FleetPrefix") is not None else "", "", 1).strip() == ship_name), None)
        if report_ship:
            condition = float(report_ship.find("Condition").text)
            if condition <= 0:
                root.find("Ships").remove(ship_elem)
            else:
                for weapon in report_ship.findall("AntiShip/Weapons/WeaponReport"):
                    weapon_name = weapon.find("Name").text
                    ammo_remaining = weapon.find("RoundsCarried").text
                    for hull_socket in ship_elem.findall("SocketMap/HullSocket"):
                        if hull_socket.find("ComponentName").text == weapon_name:
                            hull_socket.find("ComponentData/Quantity").text = ammo_remaining
    
    tree.write(new_fleet_path)
    print(f"Updated fleet saved: {new_fleet_path}")

def get_new_fleet_name(base_name):
    count = 1
    while os.path.exists(os.path.join(IN_THEATER_DIR, f"{base_name} Battle {count}.fleet")):
        count += 1
    return f"{base_name} Battle {count}"

def monitor_reports():
    observer = Observer()
    event_handler = ReportHandler()
    observer.schedule(event_handler, REPORTS_DIR, recursive=False)
    observer.start()
    
    print("Monitoring skirmish reports for new files...")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    monitor_reports()
