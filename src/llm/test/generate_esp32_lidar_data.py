"""
Generate C array from LIDAR test data for embedding in ESP32 firmware.
Converts test_data/LIDAR_message.txt into a C source file.
"""

import re
from pathlib import Path

def parse_lidar_file(filepath: str) -> list[dict]:
    """Parse LIDAR test data file into scan points."""
    scans = []
    with open(filepath, 'r') as f:
        for line in f:
            # Parse: "18701: Angle:119.265625, Distance:2811.5"
            match = re.match(r'(\d+):\s*Angle:([\d.]+),\s*Distance:([\d.]+)', line.strip())
            if match:
                scan_id, angle, distance = match.groups()
                scans.append({
                    "id": int(scan_id),
                    "angle": float(angle),
                    "distance": float(distance)
                })
    return scans

def generate_c_file(scans: list[dict], output_path: str):
    """Generate C source file with embedded LIDAR data."""
    with open(output_path, 'w') as f:
        f.write('/**\n')
        f.write(' * @file test_lidar_data.c\n')
        f.write(' * @brief Embedded LIDAR test data array\n')
        f.write(' * \n')
        f.write(' * Auto-generated from test_data/LIDAR_message.txt\n')
        f.write(f' * Contains {len(scans)} scan points\n')
        f.write(' */\n\n')
        f.write('#include "test_lidar_data.h"\n\n')
        f.write('// LIDAR test data stored in flash memory\n')
        f.write(f'const lidar_scan_t test_lidar_data[TEST_LIDAR_SCAN_COUNT] = {{\n')
        
        for i, scan in enumerate(scans):
            f.write(f'    {{{scan["id"]}, {scan["angle"]}f, {scan["distance"]}f}}')
            if i < len(scans) - 1:
                f.write(',')
            f.write('\n')
        
        f.write('};\n')
    
    print(f"✅ Generated {output_path} with {len(scans)} scan points")

if __name__ == "__main__":
    # Paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent.parent
    test_data = repo_root / "test_data" / "LIDAR_message.txt"
    output_c = repo_root / "hoverbot_external_code" / "SwarmBotESP" / "HoverBotESP" / "main" / "test_lidar_data.c"
    
    print(f"📖 Reading: {test_data}")
    scans = parse_lidar_file(str(test_data))
    
    print(f"📝 Generating: {output_c}")
    generate_c_file(scans, str(output_c))
    
    print(f"\n✨ Done! Add these files to your ESP32 project:")
    print(f"   - test_lidar_data.h")
    print(f"   - test_lidar_data.c")
