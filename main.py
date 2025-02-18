import os
import time
import xml.etree.ElementTree as ET
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Function to find the Nebulous game folder
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

# Paths to watch and save
NEBULOUS_DIR = find_nebulous_folder()
if NEBULOUS_DIR is None:
    raise FileNotFoundError("Could not find the Nebulous game folder.")

REPORTS_DIR = os.path.join(NEBULOUS_DIR, "Saves/SkirmishReports")
FLEETS_DIR = os.path.join(NEBULOUS_DIR, "Saves/Fleets")

class ReportHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".xml"):
            time.sleep(1)  # Delay to allow the report to fully populate
            process_skirmish_report(event.src_path)

def process_skirmish_report(report_path):
    try:
        if os.path.getsize(report_path) == 0:
            print(f"Error: XML file {report_path} is empty.")
            return
        
        tree = ET.parse(report_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing XML file {report_path}: {e}")
        return
    
    # Identify the local player's team
    local_team = root.find("LocalPlayerTeam").text
    
    # Locate the correct team
    for team in root.findall("Teams/TeamReportOfShipBattleReportCraftBattleReport"):
        if team.find("TeamID").text == local_team:
            player = team.find("Players/AARPlayerReportOfShipBattleReportCraftBattleReport")
            ships = player.findall("Ships/ShipBattleReport")
            fleet_ships = []
            
            for ship in ships:
                if ship.find("Eliminated").text == "NotEliminated":
                    ship_data = {
                        "name": ship.find("ShipName").text,
                        "hull": ship.find("HullKey").text,
                        "condition": ship.find("Condition").text,
                        "ammo": [
                            {
                                "weapon": w.find("Name").text,
                                "remaining": w.find("RoundsCarried").text
                            }
                            for w in ship.findall("AntiShip/Weapons/WeaponReport")
                        ]
                    }
                    fleet_ships.append(ship_data)
            
            if fleet_ships:
                save_fleet_file(fleet_ships)

def save_fleet_file(ships):
    if not os.path.exists(FLEETS_DIR):
        os.makedirs(FLEETS_DIR)
    
    fleet_name = f"Recovered_Fleet_{int(time.time())}"
    fleet_path = os.path.join(FLEETS_DIR, f"{fleet_name}.fleet")
    
    fleet_root = ET.Element("Fleet")
    ET.SubElement(fleet_root, "Name").text = fleet_name
    ET.SubElement(fleet_root, "Version").text = "3"
    ET.SubElement(fleet_root, "FactionKey").text = "Stock/Alliance"
    
    ships_element = ET.SubElement(fleet_root, "Ships")
    
    for ship in ships:
        ship_elem = ET.SubElement(ships_element, "Ship")
        ET.SubElement(ship_elem, "Name").text = ship["name"]
        ET.SubElement(ship_elem, "HullType").text = ship["hull"]
        ET.SubElement(ship_elem, "Condition").text = ship["condition"]
        
        # Add additional details
        ET.SubElement(ship_elem, "Key").text = "some-unique-key"  # Generate or retrieve a unique key
        ET.SubElement(ship_elem, "Cost").text = "0"  # Calculate or retrieve the cost
        ET.SubElement(ship_elem, "Number").text = "0"  # Assign a number
        ET.SubElement(ship_elem, "SymbolOption").text = "0"  # Assign a symbol option
        
        socket_map = ET.SubElement(ship_elem, "SocketMap")
        for ammo in ship["ammo"]:
            hull_socket = ET.SubElement(socket_map, "HullSocket")
            ET.SubElement(hull_socket, "ComponentName").text = ammo["weapon"]
            component_data = ET.SubElement(hull_socket, "ComponentData")
            ET.SubElement(component_data, "Quantity").text = ammo["remaining"]
        
        # Add empty elements for WeaponGroups, TemplateMissileTypes, and TemplateSpacecraftTypes
        ET.SubElement(ship_elem, "WeaponGroups")
        ET.SubElement(ship_elem, "TemplateMissileTypes")
        ET.SubElement(ship_elem, "TemplateSpacecraftTypes")
    
    tree = ET.ElementTree(fleet_root)
    try:
        tree.write(fleet_path)
        print(f"Saved fleet: {fleet_path}")
    except IOError as e:
        print(f"Error saving fleet file {fleet_path}: {e}")

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
