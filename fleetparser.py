import xml.etree.ElementTree as ET

def parse_fleet(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    ships_elem = root.find('Ships')
    fleet_data = []  # Collect fleet ship dictionaries

    # Process each ship
    for ship in ships_elem.findall('Ship'):
        ship_name = ship.find('Name').text.strip() if ship.find('Name') is not None else "Unknown"
        munition_count = {}
        missile_count = {}
        socket_map = ship.find('SocketMap')
        if socket_map is None:
            continue

        # Process BulkMagazineData for munitions; if munition_key starts with "$MODMIS$/", treat as missile.
        for hull_socket in socket_map.findall('HullSocket'):
            component_data = hull_socket.find('ComponentData')
            if component_data is not None and component_data.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'BulkMagazineData':
                load = component_data.find('Load')
                if load is None:
                    continue
                for mag_save_data in load.findall('MagSaveData'):
                    munition_key = mag_save_data.find('MunitionKey').text.strip()
                    quantity = int(mag_save_data.find('Quantity').text)
                    if munition_key.startswith("$MODMIS$/"):
                        missile_count[munition_key] = missile_count.get(munition_key, 0) + quantity
                    else:
                        munition_count[munition_key] = munition_count.get(munition_key, 0) + quantity

        # Process ResizableCellLauncherData for additional missiles
        for hull_socket in socket_map.findall('HullSocket'):
            component_data = hull_socket.find('ComponentData')
            if component_data is not None and component_data.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'ResizableCellLauncherData':
                missile_load = component_data.find('MissileLoad')
                if missile_load is None:
                    continue
                for mag_save_data in missile_load.findall('MagSaveData'):
                    munition_key = mag_save_data.find('MunitionKey').text.strip()
                    quantity = int(mag_save_data.find('Quantity').text)
                    missile_count[munition_key] = missile_count.get(munition_key, 0) + quantity

        fleet_data.append({
            "Name": ship_name,
            "munitions": munition_count,
            "missiles": missile_count
        })

    return fleet_data

# Example usage:
if __name__ == "__main__":
    data = parse_fleet(r'C:\Users\aaron\OneDrive\Documents\GitHub\Nebuloous\testfleet.fleet')
    for ship in data:
        print("Ship:", ship["Name"])
        print("  Munitions:", ship["munitions"])
        print("  Missiles:", ship["missiles"])