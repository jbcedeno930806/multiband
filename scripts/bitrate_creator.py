import math
import json
from pathlib import Path


topology = "nsfnet"
output_filename = "bitrates_c_bands"
output_dir = f"./scripts/results/{topology}/"
Path(output_dir).mkdir(parents=True, exist_ok=True)

bitrateJSON = {}
bitrates = ["10", "40", "100", "400", "1000"]
# bands = ["C", "L", "S", "E"]
bands = ["C"]
mods = ["BPSK", "QPSK", "8-QAM", "16-QAM", "32-QAM", "64-QAM", "128-QAM"]
spanLength = 100

spanData = {
    "C": {
        "BPSK": 130,
        "QPSK": 65,
        "8-QAM": 35,
        "16-QAM": 17,
        "32-QAM": 8,
        "64-QAM": 4,
        "128-QAM": 1,
    },
    "L": {
        "BPSK": 144,
        "QPSK": 72,
        "8-QAM": 39,
        "16-QAM": 19,
        "32-QAM": 9,
        "64-QAM": 5,
        "128-QAM": 1,
    },
    "S": {
        "BPSK": 102,
        "QPSK": 51,
        "8-QAM": 29,
        "16-QAM": 14,
        "32-QAM": 7,
        "64-QAM": 3,
        "128-QAM": 0,
    },
    "E": {
        "BPSK": 31,
        "QPSK": 15,
        "8-QAM": 9,
        "16-QAM": 4,
        "32-QAM": 2,
        "64-QAM": 1,
        "128-QAM": 0,
    },
}

bitratePerSlot = {
    "BPSK": 23,
    "QPSK": 46,
    "8-QAM": 69,
    "16-QAM": 92,
    "32-QAM": 115,
    "64-QAM": 140,
    "128-QAM": 186,
}

jsonData = {}

for bitrate in bitrates:
    jsonData[bitrate] = {}
    for band in bands:
        jsonData[bitrate][band] = {}
        for mod in mods:
            reach = spanLength * spanData[band][mod]
            slots = math.ceil(int(bitrate) / bitratePerSlot[mod])
            jsonData[bitrate][band][mod] = {"reach": reach, "slots": slots}

# print(jsonData)

with open(output_dir + output_filename + ".json", "w") as bitrateFile:
    json_object = json.dumps(jsonData)
    bitrateFile.write(json_object)
