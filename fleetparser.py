import xml.etree.ElementTree as ET

def parse_fleet(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    ships = root.find('Ships')
    missile_types = root.find('MissileTypes')
    craft_types = root.find('CraftTypes')

    # Build a mapping from TemplateKey to Nickname for craft types.
    craft_template_map = {}
    for craft_template in craft_types.findall('CraftTemplate'):
        template_key = craft_template.find('TemplateKey').text.strip()
        nickname = craft_template.find('Nickname').text.strip()
        craft_template_map[template_key] = nickname

    for ship in ships.findall('Ship'):
        ship_name = ship.find('Name').text
        print(f"Ship: {ship_name}")

        # Process BulkMagazineData to separate munitions & missiles
        munition_count = {}
        missile_count = {}

        for hull_socket in ship.find('SocketMap').findall('HullSocket'):
            component_data = hull_socket.find('ComponentData')
            if (component_data is not None and
                component_data.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'BulkMagazineData'):
                load = component_data.find('Load')
                if load is None:
                    continue
                for mag_save_data in load.findall('MagSaveData'):
                    munition_key = mag_save_data.find('MunitionKey').text
                    quantity = int(mag_save_data.find('Quantity').text)
                    if munition_key.startswith("$MODMIS$/"):
                        missile_count[munition_key] = missile_count.get(munition_key, 0) + quantity
                    else:
                        munition_count[munition_key] = munition_count.get(munition_key, 0) + quantity

        print("  Munitions:")
        for key, qty in munition_count.items():
            print(f"    {key}: {qty}")

        # Also include any missiles from ResizableCellLauncherData (if present)
        for hull_socket in ship.find('SocketMap').findall('HullSocket'):
            component_data = hull_socket.find('ComponentData')
            if (component_data is not None and
                component_data.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'ResizableCellLauncherData'):
                missile_load = component_data.find('MissileLoad')
                if missile_load is None:
                    continue
                for mag_save_data in missile_load.findall('MagSaveData'):
                    munition_key = mag_save_data.find('MunitionKey').text
                    quantity = int(mag_save_data.find('Quantity').text)
                    missile_count[munition_key] = missile_count.get(munition_key, 0) + quantity

        print("  Missiles:")
        for key, qty in missile_count.items():
            print(f"    {key}: {qty}")

        # Parse stored crafts
        print("  Stored Crafts:")
        craft_count = {}
        for hull_socket in ship.find('SocketMap').findall('HullSocket'):
            component_data = hull_socket.find('ComponentData')
            if (component_data is not None and
                component_data.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}type') == 'CraftHangarData'):
                stored_craft_element = component_data.find('StoredCraft')
                if stored_craft_element is None:
                    continue
                for stored_craft in stored_craft_element.findall('SavedStoredCraft'):
                    raw_key = stored_craft.find('CraftTemplateKey').text.strip()
                    # If the key starts with "$CRAFT$/", remove the prefix and try to match the nickname.
                    if raw_key.startswith("$CRAFT$/"):
                        remainder = raw_key[len("$CRAFT$/"):]
                        craft_name = None
                        # Look for a craft nickname that the remainder ends with.
                        for nickname in craft_template_map.values():
                            if remainder.endswith(nickname):
                                craft_name = nickname
                                break
                        if craft_name is None:
                            craft_name = remainder
                    else:
                        craft_name = craft_template_map.get(raw_key, "Unknown Craft")
                    # Count the craft
                    if craft_name in craft_count:
                        craft_count[craft_name] += 1
                    else:
                        craft_count[craft_name] = 1
        for craft_name, count in craft_count.items():
            print(f"    {craft_name}: {count}")

if __name__ == "__main__":
    parse_fleet(r'C:\Users\aaron\OneDrive\Documents\GitHub\Nebuloous\testfleet.fleet')