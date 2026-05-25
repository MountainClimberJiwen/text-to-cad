import sys
sys.path.insert(0, "/Users/jiwen/PycharmProjects/freecad-assembler")
exec(open("/Users/jiwen/PycharmProjects/freecad-assembler/models/v3/poc_v3_station.py").read())

# Export STEP
objs = [obj for obj in doc.Objects if hasattr(obj, 'Shape')]
import Import
Import.export(objs, "/Users/jiwen/PycharmProjects/freecad-assembler/models/v3/poc_v3_station.step")

# Save FCStd
doc.saveAs("/Users/jiwen/PycharmProjects/freecad-assembler/models/v3/poc_v3_station.FCStd")
print("Export done.")
