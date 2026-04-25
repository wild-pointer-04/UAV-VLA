import os
import json
import logging
from time import time
import torch
import gc
from PIL import Image
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from transformers import AutoModelForCausalLM, AutoProcessor, GenerationConfig

# 导入你现有的底层模块
from parser_for_coordinates import parse_points
from draw_circles import draw_dots_and_lines_on_image
from recalculate_to_latlon import recalculate_coordinates, read_coordinates_from_csv
from config import step_1_template, step_3_template, example_objects

logger = logging.getLogger(__name__)

# --- 全局变量声明 ---
processor = None
model = None

def process_flight_mission(command: str, image_path: str):
    global processor, model
    
    # --- 延迟加载：第一次点击时才把模型塞进 GPU ---
    if processor is None or model is None:
        logger.info("Initializing Molmo VLM Model into memory...")
        processor = AutoProcessor.from_pretrained('cyan2k/molmo-7B-O-bnb-4bit', trust_remote_code=True, torch_dtype='auto', device_map='auto')
        model = AutoModelForCausalLM.from_pretrained('cyan2k/molmo-7B-O-bnb-4bit', trust_remote_code=True, torch_dtype='auto', device_map='auto')

    try:
        api_key = os.environ.get("api_key") 
        if not api_key:
            return False, "API key not found! 请确认终端执行了 export api_key='...'"

        llm = ChatOpenAI(
            api_key=api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4/",
            model="glm-4",
            temperature=0
        )
        
        # ================= Step 1: 语义解析 (GLM-4) =================
        step_1_prompt = PromptTemplate(input_variables=["command"], template=step_1_template)
        object_types_response = (step_1_prompt | llm).invoke({"command": command})
        find_objects_json_input = object_types_response.content.replace("`", "").replace("json","")
        find_objects_json_input_2 = json.loads(find_objects_json_input)
        
        search_string = "".join(find_objects_json_input_2["object_types"])

        # ================= Step 2: 视觉定位 (Molmo) =================
        inputs = processor.process(
            images=[Image.open(image_path)],
            text=f'This is the satellite image of a city. Please, point all the next objects: {search_string}'
        )
        inputs = {k: v.to(model.device).unsqueeze(0) for k, v in inputs.items()}
        
        output = model.generate_from_batch(
            inputs,
            GenerationConfig(max_new_tokens=2000, stop_strings="<|endoftext|>"),
            tokenizer=processor.tokenizer
        )
        generated_tokens = output[0,inputs['input_ids'].size(1):]
        generated_text = processor.tokenizer.decode(generated_tokens, skip_special_tokens=True)
        
        # ================= Step 3: 坐标解析与换算 =================
        parsed_points = parse_points(generated_text)
        
        csv_file_path = 'benchmark-UAV-VLPA-nano-30/parsed_coordinates.csv'
        coordinates_dict = read_coordinates_from_csv(csv_file_path)
        
        base_name = os.path.basename(image_path).replace("temp_", "")
        
        if base_name in coordinates_dict:
            result_coordinates = recalculate_coordinates(parsed_points, base_name, coordinates_dict)
        elif base_name.split('.')[0] in coordinates_dict:
            result_coordinates = recalculate_coordinates(parsed_points, base_name.split('.')[0], coordinates_dict)
        else:
            logger.warning(f"CSV 中找不到 {base_name} 的 GPS 锚点！使用测试坐标系兜底。")
            mock_dict = { "mock": (34.05, -118.24, 34.04, -118.23) }
            result_coordinates = recalculate_coordinates(parsed_points, "mock", mock_dict)

        os.makedirs("identified_new_data", exist_ok=True)
        output_image_path = f'identified_new_data/ui_result_{int(time())}.jpg'
        draw_dots_and_lines_on_image(image_path, parsed_points, output_path=output_image_path)

        # ================= Step 4: 生成飞行计划 (GLM-4) =================
        step_3_prompt = PromptTemplate(input_variables=["command", "objects"], template=step_3_template)
        flight_plan_response = (step_3_prompt | llm).invoke({
            "command": command,
            "objects": result_coordinates
        })
        mission_code = str(flight_plan_response.content)

        # ================= Step 5: 组装返回值 =================
        real_waypoints = []
        for obj_id, obj_data in result_coordinates.items():
            real_waypoints.append(obj_data['coordinates'])

        # 释放显存，防止连续跑任务崩掉
        del inputs, output, generated_tokens
        gc.collect()
        torch.cuda.empty_cache()

        final_result = {
            "parsed_targets": find_objects_json_input_2["object_types"],
            "vlm_image_result": output_image_path,
            "mission_code": mission_code,
            "waypoints": real_waypoints
        }
        
        return True, final_result

    except Exception as e:
        logger.error(f'Error processing UI task: {str(e)}')
        return False, str(e)