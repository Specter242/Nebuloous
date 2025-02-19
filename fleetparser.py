import xml.etree.ElementTree as ET

def parse_fleet(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    ships = root.find('Ships')
    missile_types = root.find('MissileTypes')
    craft_types = root.find('CraftTypes')

    for ship in ships.findall('Ship'):
        ship_name = ship.find('Name').text
        print(f"Ship: {ship_name}")

        # Parse munitions
        print("  Munitions:")
        for hull_socket in ship.find('SocketMap').findall('HullSocket'):
            component_data = hull_socket.find('ComponentData')
            if component_data is not None and component_data.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'BulkMagazineData':
                for mag_save_data in component_data.find('Load').findall('MagSaveData'):
                    munition_key = mag_save_data.find('MunitionKey').text
                    quantity = mag_save_data.find('Quantity').text
                    print(f"    {munition_key}: {quantity}")

        # Parse missiles
        print("  Missiles:")
        for hull_socket in ship.find('SocketMap').findall('HullSocket'):
            component_data = hull_socket.find('ComponentData')
            if component_data is not None and component_data.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'ResizableCellLauncherData':
                for mag_save_data in component_data.find('MissileLoad').findall('MagSaveData'):
                    munition_key = mag_save_data.find('MunitionKey').text
                    quantity = mag_save_data.find('Quantity').text
                    print(f"    {munition_key}: {quantity}")

if __name__ == "__main__":
    parse_fleet(r'C:\Users\aaron\OneDrive\Documents\GitHub\Nebuloous\testfleet.fleet')