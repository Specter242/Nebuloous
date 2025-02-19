import os
import time
import shutil
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import xml.etree.ElementTree as ET
from reportparser import parse_report
from fleetparser import parse_fleet

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

logging.info(f"Monitoring directory: {REPORTS_DIR}")

class ReportHandler(FileSystemEventHandler):
    def on_created(self, event):
        logging.info(f"File created: {event.src_path}")  # Log file creation
        if event.src_path.endswith(".xml"):
            time.sleep(1)  # Delay to allow the report to fully populate
            process_skirmish_report(event.src_path)

def process_skirmish_report(report_path):
    logging.info(f"Processing report: {report_path}")
    try:
        report_data = {"ships": parse_report(report_path)}
        print("Report Information:", report_data)  # Debug print for report data
        tree = ET.parse(report_path)
        root = tree.getroot()
        fleet_prefix_elem = root.find(".//Colors/FleetPrefix")
        fleet_prefix = fleet_prefix_elem.text.strip() if fleet_prefix_elem is not None else ""
    except PermissionError:
        logging.error(f"Permission denied: {report_path}")
        return
    except Exception as e:
        logging.error(f"Failed to process report {report_path}: {e}")
        return

    active_ships = []
    for ship in report_data.get("ships", []):
        name = ship["ship_name"]
        if fleet_prefix and name.startswith(fleet_prefix):
            name = name[len(fleet_prefix):].strip()
        active_ships.append(name)
    logging.info(f"Active ships (without prefix): {active_ships}")

    campaign_fleet_path = find_matching_fleet(active_ships)
    if campaign_fleet_path:
        logging.info(f"Matching campaign fleet found: {campaign_fleet_path}")
        try:
            # Generate a unique new fleet name in the In Theater folder by appending "battle X"
            base_name, ext = os.path.splitext(os.path.basename(campaign_fleet_path))
            count = 1
            new_name = f"{base_name} battle {count}{ext}"
            target_fleet_path = os.path.join(IN_THEATER_DIR, new_name)
            while os.path.exists(target_fleet_path):
                count += 1
                new_name = f"{base_name} battle {count}{ext}"
                target_fleet_path = os.path.join(IN_THEATER_DIR, new_name)
            shutil.copy(campaign_fleet_path, target_fleet_path)
            logging.info(f"Copied fleet to In Theater: {target_fleet_path}")
            fleet_data = parse_fleet(target_fleet_path)
            print("Fleet Information:", fleet_data)  # Debug print for fleet data
            if fleet_data is None:
                raise ValueError("parse_fleet returned None")
        except Exception as e:
            logging.error(f"Failed to copy/parse fleet {campaign_fleet_path}: {e}")
            return
        update_fleet_with_report(target_fleet_path, fleet_data, report_data)
    else:
        logging.info("No matching fleet found")

def update_fleet_with_report(fleet_path, fleet_data, report_data):
    logging.info(f"Updating fleet with report: {fleet_path}")

    for ship_report in report_data.get("ships", []):
        ship_name = ship_report["ship_name"]
        for fleet_ship in fleet_data:
            if fleet_ship["Name"] == ship_name:
                # Update munitions
                for munition, details in ship_report["munitions"].items():
                    if munition in fleet_ship["munitions"]:
                        fleet_ship["munitions"][munition] -= details["shots_fired"]
                        if fleet_ship["munitions"][munition] < 0:
                            fleet_ship["munitions"][munition] = 0
                # Update missiles
                for missile, details in ship_report["missiles"].items():
                    if missile in fleet_ship["missiles"]:
                        fleet_ship["missiles"][missile] -= details["total_expended"]
                        if fleet_ship["missiles"][missile] < 0:
                            fleet_ship["missiles"][missile] = 0

    save_updated_fleet(fleet_path, fleet_data)

def save_updated_fleet(fleet_path, fleet_data):
    logging.info(f"Saving updated fleet: {fleet_path}")
    tree = ET.parse(fleet_path)
    root = tree.getroot()

    # Update the fleet's Name element to match the base filename (e.g., "blast battle 1")
    new_fleet_name = os.path.splitext(os.path.basename(fleet_path))[0]
    name_elem = root.find("Name")
    if name_elem is not None:
        name_elem.text = new_fleet_name
    else:
        name_elem = ET.Element("Name")
        name_elem.text = new_fleet_name
        root.insert(0, name_elem)

    # ...existing code for updating munitions and missiles...
    for fleet_ship in fleet_data:
        for ship in root.findall("Ships/Ship"):
            if ship.find("Name").text == fleet_ship["Name"]:
                # Update munitions
                for hull_socket in ship.find("SocketMap").findall("HullSocket"):
                    component_data = hull_socket.find("ComponentData")
                    if (component_data is not None and
                        component_data.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'BulkMagazineData'):
                        load = component_data.find("Load")
                        if load is not None:
                            for mag_save_data in load.findall("MagSaveData"):
                                munition_key = mag_save_data.find("MunitionKey").text
                                if munition_key in fleet_ship["munitions"]:
                                    mag_save_data.find("Quantity").text = str(fleet_ship["munitions"][munition_key])
                    # Update missiles
                    if (component_data is not None and
                        component_data.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'ResizableCellLauncherData'):
                        missile_load = component_data.find("MissileLoad")
                        if missile_load is not None:
                            for mag_save_data in missile_load.findall("MagSaveData"):
                                missile_key = mag_save_data.find("MunitionKey").text
                                if missile_key in fleet_ship["missiles"]:
                                    mag_save_data.find("Quantity").text = str(fleet_ship["missiles"][missile_key])

    tree.write(fleet_path, xml_declaration=True, encoding='utf-8', method="xml")

def find_matching_fleet(ship_names):
    campaign_fleets_dir = os.path.join(FLEETS_DIR, "Campaign Fleets")
    logging.info(f"Finding matching fleet for ships: {ship_names} in {campaign_fleets_dir}")
    for fleet_file in os.listdir(campaign_fleets_dir):
        if fleet_file.endswith(".fleet"):
            tree = ET.parse(os.path.join(campaign_fleets_dir, fleet_file))
            root = tree.getroot()
            fleet_ships = [ship.find("Name").text for ship in root.findall("Ships/Ship")]
            logging.info(f"Fleet ships: {fleet_ships}")
            if set(ship_names).issubset(set(fleet_ships)):
                return os.path.join(campaign_fleets_dir, fleet_file)
    return None

def monitor_reports():
    observer = Observer()
    event_handler = ReportHandler()
    observer.schedule(event_handler, REPORTS_DIR, recursive=False)
    observer.start()
    
    logging.info("Monitoring skirmish reports for new files...")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    monitor_reports()