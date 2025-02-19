import xml.etree.ElementTree as ET

def parse_report(xml_file):
    """
    Parses the report XML and returns a list of ships with their munition,
    missile and craft details.

    The returned list contains dictionaries like:
      {
         "ship_name": str,
         "ammo_percentage_expended": float or None,
         "munitions": dict,      
         "missiles": dict,       # each missile type maps to a dict with "total_carried" and "total_expended"
         "craft": {              
            "total": int,
            "destroyed": int
         },
         "defenses": dict        # each decoy type maps to a dict with "total_carried" and "total_expended"
      }
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    ships_list = []
    
    # iterate over all teams
    teams = root.find("Teams")
    if teams is None:
        return ships_list

    for team in teams.findall("TeamReportOfShipBattleReportCraftBattleReport"):
        players = team.find("Players")
        if players is None:
            continue
        # iterate over players and include only the local player's fleet
        for player in players.findall("AARPlayerReportOfShipBattleReportCraftBattleReport"):
            is_local = player.find("IsLocalPlayer")
            if is_local is None or is_local.text.strip().lower() != "true":
                continue

            ships = player.find("Ships")
            if ships is None:
                continue
            # each ship for the player
            for ship in ships.findall("ShipBattleReport"):
                # Get ship name
                ship_name_elem = ship.find("ShipName")
                ship_name = ship_name_elem.text if ship_name_elem is not None else "Unknown"

                # Ammo Percentage
                ammo_elem = ship.find("AmmoPercentageExpended")
                if ammo_elem is not None and ammo_elem.text not in (None, ""):
                    try:
                        ammo_pct = float(ammo_elem.text)
                    except ValueError:
                        ammo_pct = None
                else:
                    ammo_pct = None

                # Parse munitions from AntiShip/Weapons using GroupName key
                munitions = {}
                anti_ship = ship.find("AntiShip")
                if anti_ship is not None:
                    weapons = anti_ship.find("Weapons")
                    if weapons is not None:
                        for weapon_report in weapons.findall("WeaponReport"):
                            group_name_elem = weapon_report.find("GroupName")
                            munition_type = group_name_elem.text.strip() if group_name_elem is not None and group_name_elem.text else "Unknown"
                            
                            rounds_carried = 0
                            shots_fired = 0
                            
                            rounds_carried_elem = weapon_report.find("RoundsCarried")
                            if (rounds_carried_elem is not None and rounds_carried_elem.text 
                                    and rounds_carried_elem.text.strip().isdigit()):
                                try:
                                    rounds_carried = int(rounds_carried_elem.text.strip())
                                except ValueError:
                                    rounds_carried = 0
                            
                            shots_fired_elem = weapon_report.find("ShotsFired")
                            if (shots_fired_elem is not None and shots_fired_elem.text 
                                    and shots_fired_elem.text.strip().isdigit()):
                                try:
                                    shots_fired = int(shots_fired_elem.text.strip())
                                except ValueError:
                                    shots_fired = 0
                            
                            if munition_type in munitions:
                                munitions[munition_type]["rounds_carried"] += rounds_carried
                                munitions[munition_type]["shots_fired"] += shots_fired
                            else:
                                munitions[munition_type] = {
                                    "rounds_carried": rounds_carried,
                                    "shots_fired": shots_fired
                                }

                # Parse missiles from Strike/Missiles using MissileName key
                missiles = {}
                strike = ship.find("Strike")
                if strike is not None:
                    missiles_elem = strike.find("Missiles")
                    if missiles_elem is not None:
                        # Iterate over each report in Missiles (e.g., OffensiveMissileReport)
                        for missile_report in list(missiles_elem):
                            missile_name_elem = missile_report.find("MissileName")
                            missile_name = (missile_name_elem.text.strip() 
                                            if missile_name_elem is not None and missile_name_elem.text 
                                            else "Unknown")
                            
                            total_carried = 0
                            total_expended = 0
                            
                            total_carried_elem = missile_report.find("TotalCarried")
                            if (total_carried_elem is not None and total_carried_elem.text 
                                    and total_carried_elem.text.strip().isdigit()):
                                try:
                                    total_carried = int(total_carried_elem.text.strip())
                                except ValueError:
                                    total_carried = 0
                            
                            total_expended_elem = missile_report.find("TotalExpended")
                            if (total_expended_elem is not None and total_expended_elem.text 
                                    and total_expended_elem.text.strip().isdigit()):
                                try:
                                    total_expended = int(total_expended_elem.text.strip())
                                except ValueError:
                                    total_expended = 0
                            
                            if missile_name in missiles:
                                missiles[missile_name]["total_carried"] += total_carried
                                missiles[missile_name]["total_expended"] += total_expended
                            else:
                                missiles[missile_name] = {
                                    "total_carried": total_carried,
                                    "total_expended": total_expended
                                }

                # Parse defenses details - using MissileName element key from each DecoyReport
                defenses = {}
                defenses_elem = ship.find("Defenses")
                if defenses_elem is not None:
                    decoy_reports = defenses_elem.find("DecoyReports")
                    if decoy_reports is not None:
                        for decoy_report in decoy_reports.findall("DecoyReport"):
                            # Look for MissileName element within the DecoyReport
                            missile_name_elem = decoy_report.find("MissileName")
                            item_name = (missile_name_elem.text.strip() 
                                         if missile_name_elem is not None and missile_name_elem.text 
                                         else "Unknown")
                            
                            total_carried = 0
                            total_expended = 0
                            
                            total_carried_elem = decoy_report.find("TotalCarried")
                            if (total_carried_elem is not None and total_carried_elem.text and 
                                    total_carried_elem.text.strip().isdigit()):
                                try:
                                    total_carried = int(total_carried_elem.text.strip())
                                except ValueError:
                                    total_carried = 0
                            
                            total_expended_elem = decoy_report.find("TotalExpended")
                            if (total_expended_elem is not None and total_expended_elem.text and 
                                    total_expended_elem.text.strip().isdigit()):
                                try:
                                    total_expended = int(total_expended_elem.text.strip())
                                except ValueError:
                                    total_expended = 0
                            
                            if item_name in defenses:
                                defenses[item_name]["total_carried"] += total_carried
                                defenses[item_name]["total_expended"] += total_expended
                            else:
                                defenses[item_name] = {
                                    "total_carried": total_carried,
                                    "total_expended": total_expended
                                }

                # Parse craft information from the player's Craft element.
                craft = {"total": 0, "destroyed": 0}
                craft_elem = player.find("Craft")
                if craft_elem is not None:
                    craft_items = list(craft_elem)
                    craft["total"] = len(craft_items)
                    craft["destroyed"] = sum(1 for item in craft_items if item.get("destroyed", "").lower() == "true")

                ships_list.append({
                    "ship_name": ship_name,
                    "ammo_percentage_expended": ammo_pct,
                    "munitions": munitions,
                    "missiles": missiles,
                    "craft": craft,
                    "defenses": defenses  # New key with decoy (defensive) details
                })
    return ships_list

# Example usage:
if __name__ == "__main__":
    report_file = "testreport.xml"
    ships = parse_report(report_file)
    for ship in ships:
        print("Ship:", ship["ship_name"])
        print("  Ammo Percentage Expended:", ship["ammo_percentage_expended"])
        print("  Munitions:", ship["munitions"])
        print("  Missiles:", ship["missiles"])
        print("  Craft:", ship["craft"])
        print("  Defenses:", ship["defenses"])
        print()