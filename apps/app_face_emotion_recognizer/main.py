from maix import nn, camera, display, image, time, touchscreen, app, sys, uart, pinmap, err
import math
import json

pressed_flag = [False, False, False]
learn_id = 0

# 情绪映射配置
# 原始模型7类标签顺序：0:angry,1:disgust,2:fear,3:happy,4:sad,5:surprise,6:neutral
origin_labels = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
# 最终保留4类显示标签
target_labels = ["angry", "happy", "sad", "neutral"]
# 原始索引 → 最终4类索引映射
emo_map = {
    0: 0,   # angry → angry
    1: 3,   # disgust → neutral
    2: 3,   # fear → neutral
    3: 1,   # happy → happy
    4: 2,   # sad → sad
    5: 3,   # surprise → neutral
    6: 3    # neutral → neutral
}

PROTOCOL_VERSION = 1
TRIAL_ID = "unassigned"
UART_DEVICE = "/dev/ttyS0"
UART_BAUD = 115200
UART_TX_PIN = "A16"
UART_RX_PIN = "A17"
UART_TX_FUNCTION = "UART0_TX"
UART_RX_FUNCTION = "UART0_RX"
VISION_SEND_INTERVAL_MS = 180


def monotonic_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def crc8(data):
    value = 0
    for byte in data:
        value ^= byte
        for _ in range(8):
            if value & 0x80:
                value = ((value << 1) ^ 0x07) & 0xFF
            else:
                value = (value << 1) & 0xFF
    return value


def encode_packet(packet):
    payload = json.dumps(packet, separators=(",", ":"))
    checksum = crc8(payload[:-1].encode("ascii"))
    return payload[:-1] + ',"crc":"' + '{:02X}'.format(checksum) + '"}\n'


def send_vision_packet(ser, seq, face, bbox, emo_probs, quality, other_mass):
    packet = {
        "v": PROTOCOL_VERSION,
        "type": "vision_emotion",
        "seq": seq,
        "ts": monotonic_ms(),
        "trial": TRIAL_ID,
        "face": face,
        "bbox": bbox,
        "emo": [round(value, 6) for value in emo_probs],
        "quality": round(quality, 6),
        "other_mass": round(other_mass, 6),
        "lat_ms": {
            "capture": 0,
            "detect": 0,
            "align": 0,
            "fer": 0,
            "total": 0,
        },
        "pitch": 0.0,
        "roll": 0.0,
        "trk": False,
    }
    ser.write(encode_packet(packet).encode("ascii"))


def initialize_uart():
    err.check_raise(pinmap.set_pin_function(UART_TX_PIN, UART_TX_FUNCTION), "UART TX pin mapping failed")
    err.check_raise(pinmap.set_pin_function(UART_RX_PIN, UART_RX_FUNCTION), "UART RX pin mapping failed")
    return uart.UART(UART_DEVICE, UART_BAUD)


def get_back_btn_img(width):
    ret_width = int(width * 0.1)
    img_back = image.load("/maixapp/share/icon/ret.png")
    w, h = (ret_width, img_back.height() * ret_width // img_back.width())
    if w % 2 != 0:
        w += 1
    if h % 2 != 0:
        h += 1
    img_back = img_back.resize(w, h)
    return img_back

def main(disp):
    global pressed_flag, learn_id
    # 创建图像后用实心矩形填充黑色背景
    img = image.Image(disp.width(), disp.height())
    img.draw_rect(0, 0, img.width(), img.height(), image.COLOR_BLACK, thickness=-1)
    msg = "loading ..."
    size = image.string_size(msg, scale=2, thickness=2)
    img.draw_string((img.width() - size.width()) // 2, (img.height() - size.height()) // 2, msg, color=image.COLOR_WHITE, scale=2, thickness=2)
    disp.show(img)

    # ========== 初始化串口（连接ESP32） ==========
    ser = initialize_uart()
    

    # 人脸检测+识别模型初始化
    face_detect_model = "/root/models/yolo11s_face.mud" if sys.device_name().lower() == "maixcam2" else "/root/models/yolov8n_face.mud"
    recognizer = nn.FaceRecognizer(detect_model=face_detect_model, feature_model = "/root/models/insghtface_webface_r50.mud", dual_buff=True)

    # 情绪识别模型初始化
    landmarks_detector = nn.FaceLandmarks(model="")  # 仅用于人脸对齐裁剪，不加载模型
    classifier = nn.Classifier(model="/root/models/face_emotion.mud", dual_buff=False)
    emotion_conf_th = 0.5
    crop_scale = 0.9
    max_face_num = -1  # -1表示处理所有人脸

    cam = camera.Camera(recognizer.input_width(), recognizer.input_height(), recognizer.input_format())
    ts = touchscreen.TouchScreen()

    # 情绪详情绘制参数（改用4类标签计算宽度）
    max_labels_length = 0
    for label in target_labels:
        size = image.string_size(label)
        if size.width() > max_labels_length:
            max_labels_length = size.width()
    max_score_length = cam.width() / 4

    back_btn_pos = (0, 0, 70, 30) # x, y, w, h
    learn_btn_pos = (0, recognizer.input_height() - 30, 60, 30)
    clear_btn_pos = (recognizer.input_width() - 60, recognizer.input_height() - 30, 60, 30)
    back_btn_disp_pos = image.resize_map_pos(cam.width(), cam.height(), disp.width(), disp.height(), image.Fit.FIT_CONTAIN, back_btn_pos[0], back_btn_pos[1], back_btn_pos[2], back_btn_pos[3])
    learn_btn_disp_pos = image.resize_map_pos(cam.width(), cam.height(), disp.width(), disp.height(), image.Fit.FIT_CONTAIN, learn_btn_pos[0], learn_btn_pos[1], learn_btn_pos[2], learn_btn_pos[3])
    clear_btn_disp_pos = image.resize_map_pos(cam.width(), cam.height(), disp.width(), disp.height(), image.Fit.FIT_CONTAIN, clear_btn_pos[0], clear_btn_pos[1], clear_btn_pos[2], clear_btn_pos[3])

    def draw_btns(img : image.Image):
        img.draw_rect(back_btn_pos[0], back_btn_pos[1], back_btn_pos[2], back_btn_pos[3], image.Color.from_rgb(255, 255, 255), 2)
        img.draw_string(back_btn_pos[0] + 4, back_btn_pos[1] + 8, "< back", image.COLOR_WHITE)
        img.draw_rect(learn_btn_pos[0], learn_btn_pos[1], learn_btn_pos[2], learn_btn_pos[3], image.Color.from_rgb(255, 255, 255), 2)
        img.draw_string(learn_btn_pos[0] + 4, learn_btn_pos[1] + 8, "learn", image.COLOR_WHITE)
        img.draw_rect(clear_btn_pos[0], clear_btn_pos[1], clear_btn_pos[2], clear_btn_pos[3], image.Color.from_rgb(255, 255, 255), 2)
        img.draw_string(clear_btn_pos[0] + 4, clear_btn_pos[1] + 8, "clear", image.COLOR_WHITE)

    def is_in_button(x, y, btn_pos):
        return x > btn_pos[0] and x < btn_pos[0] + btn_pos[2] and y > btn_pos[1] and y < btn_pos[1] + btn_pos[3]

    def on_touch(x, y, pressed):
        '''
            Return learn, clear, ret
        '''
        global pressed_flag, learn_id
        if pressed:
            if is_in_button(x, y, back_btn_disp_pos):
                pressed_flag[2] = True
            elif is_in_button(x, y, learn_btn_disp_pos):
                pressed_flag[0] = True
            elif is_in_button(x, y, clear_btn_disp_pos):
                pressed_flag[1] = True
            else: # cancel
                pressed_flag = [False, False, False]
        else:
            if pressed_flag[0]:
                print("learn btn click")
                pressed_flag[0] = False
                return True, False, False
            if pressed_flag[1]:
                print("clear btn click")
                pressed_flag[1] = False
                learn_id = 0
                return False, True, False
            if pressed_flag[2]:
                print("back btn click")
                pressed_flag[2] = False
                return False, False, True
        return False, False, False

    last_learn_img = None
    last_learn_t = 0
    seq = 0
    last_vision_send_ms = monotonic_ms() - VISION_SEND_INTERVAL_MS

    while not app.need_exit():
        x, y, pressed = ts.read()
        learn, clear, back = on_touch(x, y, pressed)
        if back:
            break
        elif clear:
            for i in range(len(recognizer.labels) - 1):
                recognizer.remove_face(0)
        img = cam.read()
        faces = recognizer.recognize(img, 0.5, 0.45, 0.85, learn, learn)
        now_ms = monotonic_ms()
        send_due = (now_ms - last_vision_send_ms) >= VISION_SEND_INTERVAL_MS

        # ========== 无人脸时向ESP32发送标记 ==========
        if len(faces) == 0 and send_due:
            send_vision_packet(ser, seq, False, [0, 0, 0, 0], [0.0, 0.0, 1.0, 0.0], 0.0, 0.0)
            seq = (seq + 1) & 0xFFFFFFFF
            last_vision_send_ms = now_ms
        # ===========================================

        # 第一张人脸的情绪详情数据
        first_img_std = None
        first_emotion_res = None
        first_target_idx = -1  # 映射后4类情绪索引
        first_target_score = 0.0
        face_count = 0

        for obj in faces:
            # 单个人脸情绪识别
            emotion_label = "neutral"
            emotion_score = 0
            img_std = landmarks_detector.crop_image(
                img, obj.x, obj.y, obj.w, obj.h, obj.points,
                classifier.input_width(), classifier.input_height(), crop_scale
            )
            if img_std:
                img_std_gray = img_std.to_format(image.Format.FMT_GRAYSCALE)
                res = classifier.classify(img_std_gray, softmax=True)
                # 原始最高分索引
                raw_idx = res[0][0]
                raw_score = res[0][1]
                # 映射到4类情绪
                t_idx = emo_map[raw_idx]
                emotion_label = target_labels[t_idx]
                emotion_score = raw_score

                # 保存第一张人脸的详情，用于左上角显示
                if face_count == 0:
                    first_img_std = img_std
                    first_emotion_res = res
                    first_target_idx = t_idx
                    first_target_score = raw_score
                face_count += 1
                if max_face_num > 0 and face_count >= max_face_num:
                    break

            # 绘制：身份 + 情绪双行显示
            color = image.COLOR_RED if obj.class_id == 0 else image.COLOR_GREEN
            img.draw_rect(obj.x, obj.y, obj.w, obj.h, color = color)
            radius = math.ceil(obj.w / 10)
            img.draw_keypoints(obj.points, color, size = radius if radius < 5 else 4)

            identity_msg = f'{recognizer.labels[obj.class_id]}: {obj.score:.2f}'
            emotion_msg = f'{emotion_label}: {emotion_score:.1f}'
            msg = f"{identity_msg}\n{emotion_msg}"
            img.draw_string(obj.x, obj.y - 24, msg, color = color)

            if learn and obj.class_id == 0: # unknown face, we add it
                name = f"id_{learn_id}"
                print("add face:", name)
                recognizer.add_face(obj, name)
                learn_id += 1
            if learn:
                last_learn_img = obj.face
                last_learn_t = time.ticks_s()

        # 左上角显示逻辑
        if last_learn_img and time.ticks_s() - last_learn_t < 5:
            img.draw_image(0, 0, last_learn_img)
        elif first_img_std and first_emotion_res:
            # 绘制对齐人脸图
            img.draw_image(0, 0, first_img_std)
            # 统计4类情绪总分
            score_buf = [0.0, 0.0, 0.0, 0.0]
            other_mass = 0.0
            for raw_idx, s in first_emotion_res:
                if raw_idx in (1, 2, 5):
                    other_mass += s
                    continue
                t_idx = emo_map[raw_idx]
                score_buf[t_idx] += s

            # ========== 发送4类情绪置信度到ESP32 ==========
            # 协议格式：EMO:生气值,开心值,难过值,平静值\n
            selected_mass = sum(score_buf)
            if selected_mass > 0:
                score_buf = [value / selected_mass for value in score_buf]
            # ESP32 fusion expects [happy, sad, neutral, anger].
            emo_probs = [score_buf[1], score_buf[2], score_buf[3], score_buf[0]]
            bbox = [0, 0, 0, 0]
            if faces:
                bbox = [int(faces[0].x), int(faces[0].y), int(faces[0].w), int(faces[0].h)]
            if send_due:
                send_vision_packet(ser, seq, True, bbox, emo_probs, selected_mass, other_mass)
                seq = (seq + 1) & 0xFFFFFFFF
                last_vision_send_ms = now_ms
            # ============================================

            # 只绘制4种目标情绪柱状图
            for j in range(len(target_labels)):
                label = target_labels[j]
                score = score_buf[j]
                bar_color = image.COLOR_GREEN if score >= emotion_conf_th else image.COLOR_RED
                img.draw_string(0, first_img_std.height() + j * 16, label, image.COLOR_WHITE)
                img.draw_rect(max_labels_length, int(first_img_std.height() + j * 16),
                              int(score * max_score_length), 8, bar_color, -1)
                img.draw_string(int(max_labels_length + score * max_score_length + 2),
                                int(first_img_std.height() + j * 16), f"{score:.1f}", image.COLOR_RED)

        if learn:
            recognizer.save_faces("/root/faces.bin")
        draw_btns(img)
        disp.show(img)


disp = display.Display()
try:
    main(disp)
except Exception:
    import traceback
    msg = traceback.format_exc()
    print(msg)
    # 异常报错画面
    img = image.Image(disp.width(), disp.height())
    img.draw_rect(0, 0, img.width(), img.height(), image.COLOR_BLACK, thickness=-1)
    img.draw_string(0, 0, msg, image.COLOR_WHITE)
    disp.show(img)
    while not app.need_exit():
        time.sleep_ms(100)
