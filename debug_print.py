import os
from fleetparser import parse_fleet
from reportparser import parse_report

def debug_print():
    # Adjust paths as needed for your test files
    fleet_file = os.path.join(os.getcwd(), "testfleet.fleet")
    report_file = os.path.join(os.getcwd(), "testreport.xml")
    
    fleet_info = parse_fleet(fleet_file)
    report_info = parse_report(report_file)
    
    print("Fleet Information:")
    for ship in fleet_info:
        print(" Ship:", ship["Name"])
        print("  Munitions:", ship["munitions"])
        print("  Missiles:", ship["missiles"])
    
    print("\nReport Information:")
    for item in report_info:
        if "ship_name" in item:
            print(" Ship:", item["ship_name"])
            print("  Ammo Percentage Expended:", item.get("ammo_percentage_expended"))
            print("  Munitions:", item.get("munitions"))
            print("  Missiles:", item.get("missiles"))
        elif "crafts" in item:
            print(" Crafts:", item["crafts"])

if __name__ == "__main__":
    debug_print()
