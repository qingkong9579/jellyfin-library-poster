"""
动态海报生成模块
将媒体库封面生成为动态GIF，三列图片像列车一样平行移动
"""

from PIL import Image, ImageFilter, ImageDraw, ImageFont
import os
import math
import config
from logger import get_module_logger
from gen_poster import (
    add_shadow,
    create_gradient_background,
    get_poster_primary_color,
    draw_text_on_image,
    draw_multiline_text_on_image,
    draw_color_block,
    get_random_color,
)

# 获取模块日志记录器
logger = get_module_logger("gen_animated_poster")


def create_extended_column(column_posters, cell_width, cell_height, margin, corner_radius):
    """
    创建扩展高度的列图片（将图片复制一份在下方），用于无缝循环动画
    
    参数:
        column_posters: 当前列的海报文件路径列表
        cell_width: 单张海报宽度
        cell_height: 单张海报高度
        margin: 海报间距
        corner_radius: 圆角半径
        
    返回:
        扩展后的列图片（高度翻倍）
    """
    rows = len(column_posters)
    single_column_height = rows * cell_height + (rows - 1) * margin
    
    # 阴影额外空间
    shadow_extra_width = 20 + 20 * 2
    shadow_extra_height = 20 + 20 * 2
    
    # 创建扩展高度的列画布（高度为原来的2倍 + 间距）
    extended_height = single_column_height * 2 + margin
    column_image = Image.new(
        "RGBA",
        (cell_width + shadow_extra_width, extended_height + shadow_extra_height),
        (0, 0, 0, 0),
    )
    
    # 放置两份图片（上下复制）
    for copy_index in range(2):
        base_y = copy_index * (single_column_height + margin)
        
        for row_index, poster_path in enumerate(column_posters):
            try:
                # 打开海报
                poster = Image.open(poster_path)
                
                # 调整海报大小为固定尺寸
                resized_poster = poster.resize(
                    (cell_width, cell_height), Image.LANCZOS
                )
                
                # 创建圆角遮罩（如果需要）
                if corner_radius > 0:
                    mask = Image.new("L", (cell_width, cell_height), 0)
                    draw = ImageDraw.Draw(mask)
                    draw.rounded_rectangle(
                        [(0, 0), (cell_width, cell_height)],
                        radius=corner_radius,
                        fill=255,
                    )
                    poster_with_corners = Image.new(
                        "RGBA", resized_poster.size, (0, 0, 0, 0)
                    )
                    poster_with_corners.paste(resized_poster, (0, 0), mask)
                    resized_poster = poster_with_corners
                
                # 添加阴影效果
                resized_poster_with_shadow = add_shadow(
                    resized_poster,
                    offset=(20, 20),
                    shadow_color=(0, 0, 0, 255),
                    blur_radius=20,
                )
                
                # 计算在列画布上的位置
                y_position = base_y + row_index * (cell_height + margin)
                
                # 粘贴到列画布上
                column_image.paste(
                    resized_poster_with_shadow,
                    (0, y_position),
                    resized_poster_with_shadow,
                )
                
            except Exception as e:
                logger.error(f"处理图片 {os.path.basename(poster_path)} 时出错: {e}")
                continue
    
    return column_image, single_column_height


def generate_animation_frame(
    gradient_bg, 
    extended_columns, 
    column_heights,
    frame_index, 
    total_frames,
    rotation_angle,
    start_x,
    start_y,
    column_spacing,
    cell_width,
    cell_height,
    cols,
    margin,
    scale_factor=1.0
):
    """
    生成单帧动画图片
    
    参数:
        gradient_bg: 渐变背景
        extended_columns: 扩展后的列图片列表
        column_heights: 单列高度列表
        frame_index: 当前帧索引
        total_frames: 总帧数
        其他参数: 布局配置
        
    返回:
        当前帧的完整图片
    """
    result = gradient_bg.copy()
    
    # 计算当前帧的偏移量（一个完整周期移动一个图片+间距的距离）
    # 使用传入的已缩放 margin，确保与 column_heights 计算一致
    move_distance = column_heights[0] + margin  # 一个循环周期的移动距离
    progress = frame_index / total_frames
    base_offset = int(progress * move_distance)
    
    for col_index, (extended_column, single_height) in enumerate(zip(extended_columns, column_heights)):
        if col_index >= cols:
            break
        
        # 根据列索引确定移动方向
        # 第1列(0): 向上, 第2列(1): 向下, 第3列(2): 向上
        if col_index == 1:
            offset = base_offset  # 向下移动（正偏移）
        else:
            offset = -base_offset  # 向上移动（负偏移）
        
        # 从扩展列中裁剪出当前帧需要显示的部分
        # 计算裁剪区域
        shadow_extra = 20 + 20 * 2
        
        # 调整偏移确保在有效范围内
        crop_y_start = single_height // 2 + offset
        crop_y_start = crop_y_start % (single_height + margin)
        
        # 裁剪出需要的部分
        cropped_column = extended_column.crop((
            0,
            crop_y_start,
            extended_column.width,
            crop_y_start + single_height + shadow_extra
        ))
        
        # 旋转列
        rotation_canvas_size = int(
            math.sqrt(
                cropped_column.width ** 2 + cropped_column.height ** 2
            ) * 1.5
        )
        rotation_canvas = Image.new(
            "RGBA", (rotation_canvas_size, rotation_canvas_size), (0, 0, 0, 0)
        )
        
        paste_x = (rotation_canvas_size - cropped_column.width) // 2
        paste_y = (rotation_canvas_size - cropped_column.height) // 2
        rotation_canvas.paste(cropped_column, (paste_x, paste_y), cropped_column)
        
        rotated_column = rotation_canvas.rotate(
            rotation_angle, Image.BICUBIC, expand=True
        )
        
        # 计算列在模板上的位置
        column_x = start_x + col_index * column_spacing
        column_center_y = start_y + single_height // 2
        column_center_x = column_x
        
        # 根据列索引调整位置 - 需要按比例缩放调整值
        # 这些值是基于原始1920x1080分辨率的调整
        if col_index == 1:
            column_center_x += cell_width - int(50 * scale_factor)
        elif col_index == 2:
            column_center_y += int(-155 * scale_factor)
            column_center_x += (cell_width) * 2 - int(40 * scale_factor)
        
        # 计算最终放置位置
        final_x = column_center_x - rotated_column.width // 2 + cell_width // 2
        final_y = column_center_y - rotated_column.height // 2
        
        # 粘贴旋转后的列到结果图像
        result.paste(rotated_column, (final_x, final_y), rotated_column)
    
    return result


def add_text_overlay(result, name, poster_files, scale_factor=1.0, color_block_color=None):
    """
    在图片上添加文字和装饰（从gen_poster借用逻辑）
    
    参数:
        result: 图片对象
        name: 媒体库名称
        poster_files: 海报文件列表
        scale_factor: 缩放比例，用于调整字体大小和位置
        color_block_color: 色块颜色，如果为None则自动获取
    """
    import random
    
    # 使用传入的色块颜色，或者获取第一张图片的随机点颜色
    if color_block_color is not None:
        random_color = color_block_color
    elif poster_files:
        first_image_path = poster_files[0]
        random_color = get_random_color(first_image_path)
    else:
        random_color = (
            random.randint(50, 200),
            random.randint(50, 200),
            random.randint(50, 200),
            255,
        )
    
    # 查找匹配的模板配置
    library_ch_name = name
    library_eng_name = ""
    
    matched_template = None
    for template in config.TEMPLATE_MAPPING:
        if template.get("library_name") == name:
            matched_template = template
            break
    
    if matched_template:
        if "library_ch_name" in matched_template:
            library_ch_name = matched_template["library_ch_name"]
        if "library_eng_name" in matched_template:
            library_eng_name = matched_template["library_eng_name"]
    
    style_name = "style1"
    style_config = next(
        (style for style in config.STYLE_CONFIGS if style.get("style_name") == style_name),
        None
    )
    
    # 获取文字阴影设置
    ch_shadow_enabled = style_config.get("style_ch_shadow", False) if style_config else False
    eng_shadow_enabled = style_config.get("style_eng_shadow", False) if style_config else False
    ch_shadow_offset = style_config.get("style_ch_shadow_offset", (2, 2)) if style_config else (2, 2)
    eng_shadow_offset = style_config.get("style_eng_shadow_offset", (2, 2)) if style_config else (2, 2)
    
    # 按比例缩放阴影偏移
    ch_shadow_offset = (int(ch_shadow_offset[0] * scale_factor), int(ch_shadow_offset[1] * scale_factor))
    eng_shadow_offset = (int(eng_shadow_offset[0] * scale_factor), int(eng_shadow_offset[1] * scale_factor))
    
    # 添加中文名文字 - 按比例缩放位置和字体大小
    fangzheng_font_path = os.path.join("myfont", style_config.get("style_ch_font")) if style_config else "font/ch.ttf"
    ch_position = (int(73.32 * scale_factor), int(427.34 * scale_factor))
    ch_font_size = int(163 * scale_factor)
    result = draw_text_on_image(
        result, library_ch_name, ch_position, fangzheng_font_path, "ch.ttf", ch_font_size,
        shadow_enabled=ch_shadow_enabled, shadow_offset=ch_shadow_offset
    )
    
    # 如果有英文名，添加英文名文字
    if library_eng_name:
        base_font_size = int(50 * scale_factor)
        line_spacing = int(5 * scale_factor)
        word_count = len(library_eng_name.split())
        max_chars_per_line = max([len(word) for word in library_eng_name.split()])
        
        if max_chars_per_line > 10 or word_count > 3:
            font_size = (
                base_font_size
                * (10 / max(max_chars_per_line, word_count * 3)) ** 0.8
            )
            font_size = max(font_size, int(30 * scale_factor))
        else:
            font_size = base_font_size
        
        melete_font_path = os.path.join("myfont", style_config.get("style_eng_font")) if style_config else "font/en.otf"
        eng_position = (int(124.68 * scale_factor), int(624.55 * scale_factor))
        result, line_count = draw_multiline_text_on_image(
            result,
            library_eng_name,
            eng_position,
            melete_font_path, "en.otf",
            int(font_size),
            line_spacing,
            shadow_enabled=eng_shadow_enabled,
            shadow_offset=eng_shadow_offset
        )
        
        # 根据行数调整色块高度 - 按比例缩放
        color_block_position = (int(84.38 * scale_factor), int(620.06 * scale_factor))
        color_block_height = int(55 * scale_factor) + (line_count - 1) * (int(font_size) + line_spacing)
        color_block_size = (int(21.51 * scale_factor), color_block_height)
        
        result = draw_color_block(
            result, color_block_position, color_block_size, random_color
        )
    
    return result


def gen_animated_poster_workflow(name):
    """
    生成动态GIF海报的主工作流
    
    参数:
        name: 媒体库名称
        
    返回:
        成功返回True，失败返回False
    """
    try:
        logger.info(
            f"[{config.JELLYFIN_CONFIG['SERVER_NAME']}][{name}] [3/4] 正在生成动态海报..."
        )
        logger.info("-" * 40)
        
        poster_folder = os.path.join(config.POSTER_FOLDER, name)
        output_path = os.path.join(config.OUTPUT_FOLDER, f"{name}.gif")
        
        # 清理旧的动图文件（GIF和WebP）
        old_gif = os.path.join(config.OUTPUT_FOLDER, f"{name}.gif")
        old_webp = os.path.join(config.OUTPUT_FOLDER, f"{name}.webp")
        for old_file in [old_gif, old_webp]:
            if os.path.exists(old_file):
                os.remove(old_file)
                logger.info(f"[{config.JELLYFIN_CONFIG['SERVER_NAME']}][{name}] 已删除旧文件: {old_file}")
        
        # 从配置获取参数
        cols = config.POSTER_GEN_CONFIG["COLS"]  # 固定3列
        rotation_angle = config.POSTER_GEN_CONFIG["ROTATION_ANGLE"]
        
        # 从动画配置获取图片数量，动态计算行数
        poster_count = config.ANIMATION_CONFIG.get("POSTER_COUNT", 9)
        rows = poster_count // cols
        if rows < 3:
            rows = 3  # 最少3行
        
        logger.info(f"[{config.JELLYFIN_CONFIG['SERVER_NAME']}][{name}] 使用 {rows}行×{cols}列 布局，共 {rows * cols} 张图片")
        
        # 动画参数
        frame_count = config.ANIMATION_CONFIG["FRAME_COUNT"]
        frame_duration = config.ANIMATION_CONFIG["FRAME_DURATION"]
        
        # 模板尺寸 - 使用720p以减小文件体积
        # 原始尺寸1920x1080，720p为1280x720
        original_width = 1920
        original_height = 1080
        template_width = config.ANIMATION_CONFIG.get("OUTPUT_WIDTH", 1280)
        template_height = config.ANIMATION_CONFIG.get("OUTPUT_HEIGHT", 720)
        
        # 计算缩放比例
        scale_factor = template_width / original_width
        
        # 按比例缩放所有尺寸参数
        margin = int(config.POSTER_GEN_CONFIG["MARGIN"] * scale_factor)
        corner_radius = int(config.POSTER_GEN_CONFIG["CORNER_RADIUS"] * scale_factor)
        start_x = int(config.POSTER_GEN_CONFIG["START_X"] * scale_factor)
        start_y = int(config.POSTER_GEN_CONFIG["START_Y"] * scale_factor)
        column_spacing = int(config.POSTER_GEN_CONFIG["COLUMN_SPACING"] * scale_factor)
        cell_width = int(config.POSTER_GEN_CONFIG["CELL_WIDTH"] * scale_factor)
        cell_height = int(config.POSTER_GEN_CONFIG["CELL_HEIGHT"] * scale_factor)
        
        logger.info(f"[{config.JELLYFIN_CONFIG['SERVER_NAME']}][{name}] 输出分辨率: {template_width}x{template_height}, 缩放比例: {scale_factor:.2f}")
        
        # 获取海报文件
        supported_formats = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp")
        
        # 根据实际图片数量生成排序顺序
        # 按照列优先的交替顺序排列：第1列、第2列、第3列...
        max_posters = rows * cols
        
        # 获取所有图片文件（按文件名数字排序）
        all_poster_files = []
        for f in os.listdir(poster_folder):
            if os.path.isfile(os.path.join(poster_folder, f)) and f.lower().endswith(supported_formats):
                try:
                    # 提取文件名中的数字
                    num = int(os.path.splitext(f)[0])
                    all_poster_files.append((num, os.path.join(poster_folder, f)))
                except ValueError:
                    continue
        
        # 按数字排序
        all_poster_files.sort(key=lambda x: x[0])
        poster_files = [f[1] for f in all_poster_files[:max_posters]]
        
        # 重新排列为列优先顺序（按列分组后交替排列）
        # 原始顺序: 1,2,3,4,5,6,7,8,9,10,11,12
        # 列优先: 第1列(1,4,7,10), 第2列(2,5,8,11), 第3列(3,6,9,12)
        # 最终顺序: 1,4,7,10, 2,5,8,11, 3,6,9,12
        reordered_files = []
        for col in range(cols):
            for row in range(rows):
                idx = row * cols + col
                if idx < len(poster_files):
                    reordered_files.append(poster_files[idx])
        poster_files = reordered_files
        
        if not poster_files:
            logger.error(
                f"[{config.JELLYFIN_CONFIG['SERVER_NAME']}][{name}] 错误: 在 {poster_folder} 中没有找到支持的图片文件"
            )
            return False
        
        # 分组为列
        grouped_posters = [
            poster_files[i : i + rows] for i in range(0, len(poster_files), rows)
        ]
        
        # 获取第一张图片的主色调并创建渐变背景
        first_image_path = os.path.join(poster_folder, "1.jpg")
        color = get_poster_primary_color(first_image_path)
        gradient_bg = create_gradient_background(template_width, template_height, name, color)
        
        # 创建扩展高度的列图片
        logger.info(f"[{config.JELLYFIN_CONFIG['SERVER_NAME']}][{name}] 正在创建扩展列图片...")
        extended_columns = []
        column_heights = []
        
        for col_index, column_posters in enumerate(grouped_posters):
            if col_index >= cols:
                break
            extended_col, single_height = create_extended_column(
                column_posters, cell_width, cell_height, margin, corner_radius
            )
            extended_columns.append(extended_col)
            column_heights.append(single_height)
        
        # 生成所有帧
        logger.info(f"[{config.JELLYFIN_CONFIG['SERVER_NAME']}][{name}] 正在生成 {frame_count} 帧动画...")
        frames = []
        
        # 预先计算色块颜色，确保所有帧使用相同颜色避免闪烁
        color_block_color = get_random_color(poster_files[0]) if poster_files else (128, 128, 128, 255)
        
        for frame_index in range(frame_count):
            frame = generate_animation_frame(
                gradient_bg,
                extended_columns,
                column_heights,
                frame_index,
                frame_count,
                rotation_angle,
                start_x,
                start_y,
                column_spacing,
                cell_width,
                cell_height,
                cols,
                margin,
                scale_factor
            )
            
            # 每一帧都添加文字覆盖层，使用预先计算的色块颜色
            frame = add_text_overlay(frame, name, poster_files, scale_factor, color_block_color)
            
            # 保持RGBA格式，在最后保存时统一处理
            frames.append(frame)
            
            if (frame_index + 1) % 10 == 0:
                logger.info(f"[{config.JELLYFIN_CONFIG['SERVER_NAME']}][{name}] 已生成 {frame_index + 1}/{frame_count} 帧")
        
        # 保存为GIF
        logger.info(f"[{config.JELLYFIN_CONFIG['SERVER_NAME']}][{name}] 正在保存GIF动画...")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 根据配置选择输出格式
        output_format = config.ANIMATION_CONFIG.get("OUTPUT_FORMAT", "GIF").upper()
        
        if output_format == "WEBP":
            # 使用WebP格式，支持更多颜色和更好的压缩
            output_path = output_path.replace(".gif", ".webp")
            
            # 转换帧为RGBX格式（WebP动画需要）
            webp_frames = []
            for frame in frames:
                # 转换为RGBX格式，移除alpha通道
                webp_frame = frame.convert("RGBX")
                webp_frames.append(webp_frame)
            
            # 保存为动态WebP
            webp_frames[0].save(
                output_path,
                format="WEBP",
                save_all=True,
                append_images=webp_frames[1:],
                duration=frame_duration,
                loop=0,
                quality=85,
                method=4,  # 压缩方法（0-6，越高越慢但压缩越好）
            )
            logger.info(f"[{config.JELLYFIN_CONFIG['SERVER_NAME']}][{name}] WebP动画已保存")
        else:
            # GIF格式 - 使用抖动来减少色带
            gif_colors = config.ANIMATION_CONFIG.get("GIF_COLORS", 128)
            gif_frames = []
            
            # 基于第一帧生成全局调色板，所有帧共享同一调色板以避免文字闪烁
            first_frame_rgb = frames[0].convert("RGB")
            global_palette = first_frame_rgb.quantize(colors=gif_colors, method=Image.Quantize.MEDIANCUT)
            
            for i, frame in enumerate(frames):
                # 先转换为RGB（移除alpha通道）
                frame_rgb = frame.convert("RGB")
                # 使用全局调色板进行量化，确保颜色一致性
                frame_p = frame_rgb.quantize(palette=global_palette, dither=Image.Dither.FLOYDSTEINBERG)
                gif_frames.append(frame_p)
            
            gif_frames[0].save(
                output_path,
                save_all=True,
                append_images=gif_frames[1:],
                duration=frame_duration,
                loop=0,
                optimize=False,  # 关闭优化以保持颜色一致性
            )
        
        logger.info(
            f"[{config.JELLYFIN_CONFIG['SERVER_NAME']}][{name}] 成功: 动态海报已保存到 {output_path}"
        )
        return True
        
    except Exception as e:
        logger.error(
            f"[{config.JELLYFIN_CONFIG['SERVER_NAME']}][{name}] 创建动态海报时出错: {e}",
            exc_info=True,
        )
        return False


if __name__ == "__main__":
    # 测试入口
    import sys
    
    # 如果没有配置测试数据，打印使用说明
    test_library = None
    
    # 检查是否有poster文件夹中的测试数据
    if os.path.exists(config.POSTER_FOLDER):
        libraries = [d for d in os.listdir(config.POSTER_FOLDER) 
                    if os.path.isdir(os.path.join(config.POSTER_FOLDER, d))]
        if libraries:
            test_library = libraries[0]
            print(f"找到测试媒体库: {test_library}")
    
    if test_library:
        print(f"正在生成动态海报: {test_library}")
        gen_animated_poster_workflow(test_library)
    else:
        print("未找到测试媒体库，请确保 poster 文件夹中有测试数据")
        print(f"poster文件夹路径: {config.POSTER_FOLDER}")
