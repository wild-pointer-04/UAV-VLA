import os

def extract_number(filename):
    # 第一步：用 '.' 分割文件名并取第一部分
    parts = filename.split('.')
    if not parts or parts[0] == "":
        return 999999  # 如果是隐藏文件（如 .DS_Store），返回一个大数排到最后
    
    # 第二步：去掉可能存在的空格，并检查是否为数字
    name_part = parts[0].strip()
    if name_part.isdigit():
        return int(name_part)
    
    # 第三步：如果不是数字（比如 metadata.json），也不要报错，返回大数跳过
    return 999999

def extract_waypoints(input_directory):
    output_content = ""

    for idx, filename in enumerate(sorted(os.listdir(input_directory), key=extract_number), start=1):
        if filename.endswith('.waypoints'):
            file_path = os.path.join(input_directory, filename)

            with open(file_path, 'r') as file:
                waypoints_data = file.readlines()

            output_content += f"Image {idx}:\n"

            home_line = waypoints_data[1].strip().split('\t')
            home_lat = home_line[8]
            home_lon = home_line[9]
            
            output_content += "  Home Position:\n"
            output_content += f"    Latitude: {home_lat}\n"
            output_content += f"    Longitude: {home_lon}\n"

            for building_idx, line in enumerate(waypoints_data[2:], start=1):
                building_data = line.strip().split('\t')
                building_lat = building_data[8]
                building_lon = building_data[9]
                output_content += f"  Building {building_idx}:\n"
                output_content += f"    Latitude: {building_lat}\n"
                output_content += f"    Longitude: {building_lon}\n"

            output_content += "\n"
    return output_content

def process_mp_data(input_directory, output_txt):
    output_content = extract_waypoints(input_directory)
    
    with open(output_txt, 'w') as f:
        f.write(output_content)

    print("Data has been saved to", output_txt)
