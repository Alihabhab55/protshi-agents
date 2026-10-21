import json

with open("bag.json", encoding="utf-8") as f:
    bag = json.load(f)

print(bag["name"])
