import os
import time
import xml.etree.ElementTree as ET
import uuid
import shutil
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
IN_THEATER_DIR = os.path.join(FLEETS_DIR, "In theater")

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
                full_name = ship.find("ShipName").text
                name = full_name.split(' ', 1)[1] if ' ' in full_name else full_name  # Exclude prefix
                hull_string = ship.find("HullString").text
                number = ''.join(filter(str.isdigit, hull_string)) if hull_string else "0"
                ship_data = {
                    "name": name,
                    "hull": ship.find("HullKey").text,
                    "condition": ship.find("Condition").text,
                    "cost": ship.find("OriginalPointCost").text if ship.find("OriginalPointCost") is not None else "0",
                    "number": number,
                    "ammo": [
                        {
                            "weapon": w.find("Name").text,
                            "remaining": w.find("RoundsCarried").text
                        }
                        for w in ship.findall("AntiShip/Weapons/WeaponReport")
                    ],
                    "eliminated": ship.find("Eliminated").text == "Eliminated"
                }
                fleet_ships.append(ship_data)
            
            if fleet_ships:
                matching_fleet_path = find_matching_fleet(fleet_ships)
                if matching_fleet_path:
                    update_fleet_file(matching_fleet_path, fleet_ships)

def find_matching_fleet(fleet_ships):
    for fleet_file in os.listdir(FLEETS_DIR):
        if fleet_file.endswith(".fleet"):
            fleet_path = os.path.join(FLEETS_DIR, fleet_file)
            tree = ET.parse(fleet_path)
            root = tree.getroot()
            ships = root.findall("Ships/Ship")
            if len(ships) == len(fleet_ships):
                match = True
                for ship, fleet_ship in zip(ships, fleet_ships):
                    if ship.find("Name").text != fleet_ship["name"] or ship.find("HullType").text != fleet_ship["hull"]:
                        match = False
                        break
                if match:
                    return fleet_path
    return None

def update_fleet_file(fleet_path, fleet_ships):
    tree = ET.parse(fleet_path)
    root = tree.getroot()
    fleet_name = root.find("Name").text
    battle_number = 1
    new_fleet_name = f"{fleet_name} battle {battle_number}"
    while os.path.exists(os.path.join(IN_THEATER_DIR, f"{new_fleet_name}.fleet")):
        battle_number += 1
        new_fleet_name = f"{fleet_name} battle {battle_number}"
    
    new_fleet_path = os.path.join(IN_THEATER_DIR, f"{new_fleet_name}.fleet")
    
    # Copy the original fleet file to the new location
    shutil.copy(fleet_path, new_fleet_path)
    
    # Update the copied fleet file
    tree = ET.parse(new_fleet_path)
    root = tree.getroot()
    root.find("Name").text = new_fleet_name
    ships_element = root.find("Ships")
    ships_element.clear()
    
    for ship in fleet_ships:
        if ship["eliminated"]:
            continue  # Skip eliminated ships
        ship_elem = ET.SubElement(ships_element, "Ship")
        save_id_elem = ET.SubElement(ship_elem, "SaveID")
        save_id_elem.set("{http://www.w3.org/2001/XMLSchema-instance}nil", "true")  # Set xsi:nil="true"
        ET.SubElement(ship_elem, "Key").text = str(uuid.uuid4())  # Generate a unique key for each ship
        ET.SubElement(ship_elem, "Name").text = ship["name"]
        ET.SubElement(ship_elem, "Cost").text = ship.get("cost", "0")  # Calculate or retrieve the cost
        ET.SubElement(ship_elem, "Number").text = ship["number"]  # Assign the number from HullString
        ET.SubElement(ship_elem, "SymbolOption").text = "0"  # Assign a symbol option
        ET.SubElement(ship_elem, "HullType").text = ship["hull"]
        ET.SubElement(ship_elem, "Condition").text = ship["condition"]
        
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
    
    # Write the updated XML content directly without pretty-printing
    tree.write(new_fleet_path, encoding='utf-8', xml_declaration=True)
    
    print(f"Saved updated fleet: {new_fleet_path}")

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
