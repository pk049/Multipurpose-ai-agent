import platform
import os
import json

# print(platform.system())
# print(platform.architecture())

# # Desktop path
# desktop_path=os.path.join(os.path.expanduser("~"),'OneDrive','dEsktop')
# print(f"desktop path is {desktop_path}")
# print(os.listdir(desktop_path))
# print()

# print(os.path.abspath('code3.py'))

dictionary={
    "name":"pratik","age":20
}

print(json.dumps(dictionary))
