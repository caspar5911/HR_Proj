import os

base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "src", "routes")
dst = os.path.join(base, "leave.tsx")

print(f"Will write to: {dst}")
print("Content will be generated in parts...")