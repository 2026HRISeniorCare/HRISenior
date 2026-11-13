"""一次性生成三张 logo(方形logo,横版文字logo, favicon)并覆盖旧的小智图片。
   要求: 已装 Pillow → pip install Pillow
   用法: python gen_logos.py"""

import math
from PIL import Image, ImageDraw, ImageFont

COLOR_PRIMARY = "#FF7A59"
COLOR_DARK = "#3d4566"
COLOR_LIGHT = "#fff2ec"
OUT_DIR = "public"

# ── 工具 ────────────────────────────────────────────────────────
def _circle_mask(draw, cx, cy, r, fill):
    """画实心圆(Pillow 无内置 circle,手工光栅)"""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)

def _rounded_rect(draw, x, y, w, h, r, fill):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill)

# ── 1. 方形 logo (128x128) 替换 src/assets/xiaozhi-logo.png ─────
def make_square_logo():
    sz = 128
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    r = sz // 2
    # 珊瑚圆底
    _circle_mask(draw, r, r, r - 2, COLOR_PRIMARY)
    # 中心白色区域做"灵犀"抽象: 两个交叠的心形简化
    # 用两个弧 + 一个三角合成一个简笔心, 居中偏上
    cx, cy = r, r - 8
    hs = 18  # 心形半宽
    # 左弧
    draw.arc([cx - hs * 2, cy - hs, cx + 2, cy + hs], 60, 300, fill="white", width=6)
    # 右弧
    draw.arc([cx - 2, cy - hs, cx + hs * 2, cy + hs], 240, 480, fill="white", width=6)
    # 下三角尖端
    draw.polygon([(cx - hs * 2 + 7, cy + hs // 2), (cx + hs * 2 - 7, cy + hs // 2), (cx, cy + hs + 10)], fill="white")
    path = f"{OUT_DIR}/xiaozhi-logo.png"
    img.save(path)
    print(f"square logo → {path}")


# ── 2. 横版文字 logo (400x96) 替换 src/assets/xiaozhi-ai.png ────
def make_text_logo():
    w, h = 500, 110
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    # 左侧圆形标识(跟着放大)
    cx, cr = 55, 42
    _circle_mask(draw, cx, 55, cr, COLOR_PRIMARY)
    draw.polygon([(cx - 8, 45), (cx + 8, 45), (cx, 67)], fill="white")
    # 主标题(放大到 56px)
    try:
        fn = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 56)
    except Exception:
        try:
            fn = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 56)
        except Exception:
            fn = ImageFont.load_default()
    draw.text((112, 18), "智岁灵犀", fill=COLOR_DARK, font=fn)
    # 副标题
    try:
        fns = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    except Exception:
        fns = fn
    draw.text((116, 76), "安安 · 情感交流机器人", fill=COLOR_PRIMARY, font=fns)
    path = f"{OUT_DIR}/xiaozhi-ai.png"
    img.save(path)
    print(f"text logo → {path}")


# ── 3. favicon (32x32) ──────────────────────────────────────────
def make_favicon():
    sz = 32
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    r = sz // 2
    _circle_mask(draw, r, r, r - 2, COLOR_PRIMARY)
    # 内白三角(抽象山峰/灵犀角)
    draw.polygon([(11, 16), (21, 16), (16, 6)], fill="white")
    img.save(f"{OUT_DIR}/favicon.ico", format="ICO", sizes=[(sz, sz)])
    print(f"favicon → {OUT_DIR}/favicon.ico")

if __name__ == "__main__":
    make_square_logo()
    make_text_logo()
    make_favicon()
