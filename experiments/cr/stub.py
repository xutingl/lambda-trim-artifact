# READ DEBLOAT Env variable
import os

DEBLOAT = os.getenv("DEBLOAT_ENV", "off")
if DEBLOAT == "on":
    filename = "output/debloated.txt"
else:
    filename = "output/normal.txt"

with open(filename, "a") as f:
    f.write(f"{import_time}\n")
