import matplotlib.pyplot as plt
import os

def load_coords_flexible(file_path):
    lats, lons = [], []
    current_lat = None
    if not os.path.exists(file_path):
        return [], []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if 'Latitude:' in line:
                try: current_lat = float(line.split(':')[1].strip())
                except: continue
            elif 'Longitude:' in line:
                try:
                    current_lon = float(line.split(':')[1].strip())
                    if current_lat is not None:
                        lats.append(current_lat)
                        lons.append(current_lon)
                        current_lat = None
                except: continue
    return lats, lons

def plot_comparison():
    vlm_lats, vlm_lons = load_coords_flexible('VLM_coordinates.txt')
    mp_lats, mp_lons = load_coords_flexible('mp_coordinates.txt')
    print(f"VLM: {len(vlm_lats)} points, MP: {len(mp_lats)} points")
    if not vlm_lats or not mp_lats: return
    plt.figure(figsize=(10, 8))
    plt.plot(vlm_lons, vlm_lats, 'g--', label='VLM Raw', alpha=0.5)
    plt.plot(mp_lons, mp_lats, 'r-', linewidth=2, label='MP Optimized')
    plt.legend()
    plt.axis('equal')
    plt.savefig('trajectory_comparison_final.png')
    print("Success: trajectory_comparison_final.png saved.")

if __name__ == "__main__":
    plot_comparison()
