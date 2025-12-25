"""
动态海报生成测试脚本
使用示例图片测试动画生成功能
"""

import os
import sys
from PIL import Image, ImageDraw
import random

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from gen_animated_poster import gen_animated_poster_workflow

def create_test_poster(output_path, index, size=(410, 610)):
    """创建一个带有编号的测试海报图片"""
    # 随机生成渐变颜色
    color1 = (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
    color2 = (min(255, color1[0] + 50), min(255, color1[1] + 50), min(255, color1[2] + 50))
    
    # 创建渐变图片
    img = Image.new('RGB', size, color1)
    draw = ImageDraw.Draw(img)
    
    # 绘制简单的渐变效果
    for y in range(size[1]):
        ratio = y / size[1]
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))
    
    # 在中心绘制编号
    draw = ImageDraw.Draw(img)
    text = str(index)
    
    # 使用简单的文本绘制
    text_bbox = draw.textbbox((0, 0), text)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    # 绘制白色描边
    for dx in [-2, -1, 0, 1, 2]:
        for dy in [-2, -1, 0, 1, 2]:
            draw.text((x + dx, y + dy), text, fill=(255, 255, 255))
    
    # 绘制黑色文字
    draw.text((x, y), text, fill=(0, 0, 0))
    
    img.save(output_path, 'JPEG', quality=95)
    print(f"创建测试海报: {output_path}")


def setup_test_environment():
    """设置测试环境，创建必要的文件夹和测试图片"""
    test_library_name = "TestLibrary"
    
    # 添加测试库的 template_mapping 配置
    # 检查是否已存在配置
    test_config_exists = any(
        t.get("library_name") == test_library_name 
        for t in config.TEMPLATE_MAPPING
    )
    if not test_config_exists:
        config.TEMPLATE_MAPPING.append({
            "library_name": test_library_name,
            "library_ch_name": "测试库",
            "library_eng_name": "TEST LIBRARY",
            "poster_sort": "DateCreated"
        })
        print(f"添加测试库配置: {test_library_name}")
    
    # 创建poster文件夹
    poster_folder = os.path.join(config.POSTER_FOLDER, test_library_name)
    if not os.path.exists(poster_folder):
        os.makedirs(poster_folder)
        print(f"创建测试文件夹: {poster_folder}")
    
    # 创建9张测试海报
    for i in range(1, 10):
        poster_path = os.path.join(poster_folder, f"{i}.jpg")
        if not os.path.exists(poster_path):
            create_test_poster(poster_path, i)
    
    # 创建output文件夹
    if not os.path.exists(config.OUTPUT_FOLDER):
        os.makedirs(config.OUTPUT_FOLDER)
        print(f"创建输出文件夹: {config.OUTPUT_FOLDER}")
    
    return test_library_name


def run_test():
    """运行测试"""
    print("=" * 50)
    print("动态海报生成测试")
    print("=" * 50)
    
    # 设置测试环境
    test_library = setup_test_environment()
    
    # 运行动画生成
    print(f"\n正在生成动态海报: {test_library}")
    result = gen_animated_poster_workflow(test_library)
    
    if result:
        output_path = os.path.join(config.OUTPUT_FOLDER, f"{test_library}.gif")
        file_size = os.path.getsize(output_path) / 1024 / 1024  # MB
        print(f"\n✓ 测试成功!")
        print(f"  输出文件: {output_path}")
        print(f"  文件大小: {file_size:.2f} MB")
    else:
        print(f"\n✗ 测试失败!")
        return False
    
    return True


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
