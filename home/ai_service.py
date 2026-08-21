import json
import random
import urllib.request
import urllib.error
import base64
import io
import re
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(env_path)

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

GROQ_KEY = os.environ.get("GROQ_KEY", "")
GROQ_KEY2 = os.environ.get("GROQ_KEY2", "")
GEMINI_KEY = os.environ.get("GEMINI_KEY", "")
GEMINI_KEY2 = os.environ.get("GEMINI_KEY2", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
OPENROUTER_KEY2 = os.environ.get("OPENROUTER_KEY2", "")


def _get_keys(name):
    """Read env var at call time so Render env changes take effect without restart."""
    return os.environ.get(name, "")


# Sends the messages to the Groq API and returns the reply text.
# If removed, Groq chat and challenge generation stop working.
# Add your Groq key in settings (user.groq_api_key) or in the .env file.
def _groq_request(messages, model="llama-3.3-70b-versatile", temperature=0.7, max_tokens=2048, custom_key=None):
    if custom_key:
        keys = [custom_key]
    else:
        keys = [_get_keys("GROQ_KEY"), _get_keys("GROQ_KEY2")]
    valid_keys = []
    for k in keys:
        if k:
            valid_keys.append(k)
    keys = valid_keys
    if not keys:
        return None
    for key in keys:
        try:
            data = json.dumps({
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }).encode()
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return result["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            import sys as _sys
            _sys.stderr.write(f"[GROQ ERROR] HTTP {e.code}: {e.read().decode()[:200]}\n")
            _sys.stderr.flush()
        except Exception as e:
            import sys as _sys
            _sys.stderr.write(f"[GROQ ERROR] {type(e).__name__}: {str(e)[:200]}\n")
            _sys.stderr.flush()
    return None


UA = "Mozilla/5.0"


# Calls the Gemini API with a prompt (can also send an image) and returns the text.
# If removed, the Gemini fallback and image judging stop working.
# Gemini key comes from settings or the .env file (GEMINI_KEY).
def _gemini_request(prompt, image_data=None, custom_key=None, model="gemini-2.5-flash", search=False):
    if custom_key:
        keys = [custom_key]
    else:
        keys = [_get_keys("GEMINI_KEY"), _get_keys("GEMINI_KEY2")]
    valid_keys = [k for k in keys if k]
    if not valid_keys:
        return None
    for key in valid_keys:
        try:
            contents = {"contents": [{"parts": [{"text": prompt}]}]}
            if search:
                contents["tools"] = [{"google_search": {}}]
            if image_data:
                contents["contents"][0]["parts"].insert(0, {
                    "inline_data": {"mime_type": "image/jpeg", "data": image_data}
                })
            data = json.dumps(contents).encode()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": UA},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            continue
    return None


# Generates an image from a text prompt using Pollinations and returns it as base64.
# If removed, text-to-image generation loses its online option.
# Change image size or style by editing the Pollinations URL here.
def _pollinations_generate(prompt):
    import urllib.parse
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            img_data = resp.read()
            if len(img_data) > 1000:
                return base64.b64encode(img_data).decode()
    except Exception as e:
        print(f"[POLLINATIONS] Failed: {str(e)[:200]}")
    return None


# Picks an art style (anime, neon, etc) based on words in the prompt.
# If removed, fallback images lose their style and default to anime.
# Add new style keywords in the if checks here.
def _detect_style_from_prompt(prompt):
    prompt_lower = prompt.lower()
    if 'anime' in prompt_lower: return 'anime'
    if 'neon' in prompt_lower: return 'neon'
    if 'vintage' in prompt_lower or 'retro' in prompt_lower or 'sepia' in prompt_lower: return 'vintage'
    if 'glitch' in prompt_lower: return 'glitch'
    if 'oil' in prompt_lower or 'impressionist' in prompt_lower: return 'oil'
    if 'pop-art' in prompt_lower or 'pop art' in prompt_lower or 'warhol' in prompt_lower: return 'pop-art'
    if 'cyberpunk' in prompt_lower: return 'cyberpunk'
    if 'watercolor' in prompt_lower: return 'watercolor'
    return 'anime'


# OpenCV helper: converts a base64 image string into an OpenCV BGR image.
# If removed, all local OpenCV fallback effects break.
# Only needed when cv2 is installed (HAS_CV2).
def _b64_to_cv2(b64_data):
    if ',' in b64_data:
        b64_data = b64_data.split(',')[1]
    img_bytes = base64.b64decode(b64_data)
    nparr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

# Converts a PIL image to an OpenCV BGR array.
# If removed, any PIL to OpenCV conversion breaks.
# Not used right now, kept for future use.
def _pil_to_cv2(pil_img):
    return cv2.cvtColor(np.array(pil_img.convert('RGB')), cv2.COLOR_RGB2BGR)

# Converts an OpenCV image back into a base64 PNG string.
# If removed, local fallback effects cant return an image to the frontend.
# Change the format (fmt) here if you need jpg instead.
def _cv2_to_b64(cv_img, fmt='.png'):
    _, buf = cv2.imencode(fmt, cv_img)
    return base64.b64encode(buf.tobytes()).decode()

# Draws a fake artistic portrait with OpenCV when no AI can make one.
# If removed, the text-to-image fallback returns nothing when offline.
# Tweak the drawing code here (colors, shapes, blur) to change the art.
def _gen_abstract_portrait(prompt, style):
    h, w = 512, 512
    style_colors = {
        'anime': [(255,200,220), (180,200,255), (220,180,255), (200,230,255)],
        'neon': [(255,0,128), (0,255,255), (128,0,255), (255,255,0)],
        'vintage': [(180,140,100), (200,160,120), (160,120,80), (140,100,70)],
        'glitch': [(255,0,0), (0,255,0), (0,0,255), (255,0,255)],
        'oil': [(180,150,120), (200,170,140), (160,130,100), (140,110,80)],
        'pop-art': [(255,50,50), (50,255,50), (50,50,255), (255,255,50)],
        'cyberpunk': [(255,0,128), (0,200,255), (50,0,100), (255,100,0)],
        'watercolor': [(200,220,200), (180,200,220), (220,200,200), (200,200,180)],
    }
    colors = style_colors.get(style, [(200,200,200), (180,180,180)])

    canvas = np.ones((h, w, 3), dtype=np.uint8) * 30
    # Gradient background
    for y in range(h):
        ratio = y / h
        r = int(30 + ratio * 60)
        g = int(30 + ratio * 40)
        b = int(60 + ratio * 30)
        canvas[y, :] = [b, g, r]

    # Draw silhouette-like shape
    center = (w//2, h//2 + 20)
    axes = (w//3, h//2 - 20)
    cv2.ellipse(canvas, center, axes, 0, 0, 360, (50, 50, 60), -1)

    # Draw face-like features
    face_color = colors[0]
    cv2.ellipse(canvas, center, (w//3 - 10, h//2 - 30), 0, 0, 360, face_color, -1)

    # Eyes
    eye_color = (30, 30, 40)
    eye_y = center[1] - 30
    cv2.circle(canvas, (center[0] - 40, eye_y), 12, eye_color, -1)
    cv2.circle(canvas, (center[0] + 40, eye_y), 12, eye_color, -1)
    # Eye highlights
    hl_color = (255, 255, 255)
    cv2.circle(canvas, (center[0] - 42, eye_y - 4), 4, hl_color, -1)
    cv2.circle(canvas, (center[0] + 38, eye_y - 4), 4, hl_color, -1)

    # Hair overlay (top half of head)
    if len(colors) > 1:
        hair_color = colors[1]
    else:
        hair_color = (100, 100, 120)
    overlay = canvas.copy()
    cv2.ellipse(overlay, (center[0], center[1] - 80), (w//2 + 10, h//3), 0, 180, 360, hair_color, -1)
    cv2.addWeighted(overlay, 0.8, canvas, 0.2, 0, canvas)

    # Accent color splashes
    for i in range(3):
        color = colors[i % len(colors)]
        x = np.random.randint(50, w-50)
        y = np.random.randint(50, h-50)
        r = np.random.randint(10, 30)
        cv2.circle(canvas, (x, y), r, color, -1)
        # blur it
        canvas = cv2.GaussianBlur(canvas, (5, 5), 0)

    # Apply style-specific post-processing
    if style == 'neon':
        hsv = cv2.cvtColor(canvas, cv2.COLOR_BGR2HSV)
        hsv[:,:,1] = cv2.add(hsv[:,:,1], 60)
        canvas = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    elif style == 'glitch':
        b, g, r = cv2.split(canvas)
        canvas = cv2.merge([np.roll(b, 5, axis=1), g, np.roll(r, -5, axis=1)])
    elif style == 'vintage':
        canvas = cv2.GaussianBlur(canvas, (3, 3), 0)
        noise = np.random.randint(0, 20, canvas.shape, dtype=np.uint8)
        canvas = cv2.add(canvas, noise)
    elif style == 'pop-art':
        data = canvas.reshape((-1, 3)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(data, 5, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        centers = centers.astype(np.uint8)
        canvas = centers[labels.flatten()].reshape(canvas.shape)
    elif style == 'watercolor':
        canvas = cv2.medianBlur(canvas, 7)
        canvas = cv2.bilateralFilter(canvas, 9, 50, 50)

    return canvas


# Style helper: applies an anime look to an image (smooth + quantized colors + edges).
# If removed, the anime style fallback stops working.
# Tune the blur and color count numbers here.
def _style_anime(img_bgr):
    smooth = cv2.bilateralFilter(img_bgr, 9, 75, 75)
    smooth = cv2.bilateralFilter(smooth, 9, 75, 75)
    data = smooth.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(data, 16, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    centers = centers.astype(np.uint8)
    quantized = centers[labels.flatten()].reshape(img_bgr.shape)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 2)
    edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    return cv2.addWeighted(quantized, 0.8, edges_colored, 0.2, 0)

# Applies a neon look: edge glow + high contrast + saturation.
# If removed, the neon style fallback stops working.
# Change glow strength in the addWeighted call here.
def _style_neon(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    kernel = np.ones((3,3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=2)
    glow = np.zeros_like(img_bgr)
    glow[:,:,0] = edges
    glow[:,:,2] = edges
    glow = cv2.GaussianBlur(glow, (9,9), 0)
    dark = cv2.convertScaleAbs(img_bgr, alpha=0.7, beta=0)
    result = cv2.addWeighted(dark, 1.0, glow, 0.6, 0)
    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
    hsv[:,:,1] = np.clip(hsv[:,:,1] + 50, 0, 255).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

# Applies a vintage sepia look with grain and vignette.
# If removed, the vintage style fallback stops working.
# Adjust the sepia matrix values here for a different tone.
def _style_vintage(img_bgr):
    sepia_k = np.array([[0.272, 0.534, 0.131],
                        [0.349, 0.686, 0.168],
                        [0.393, 0.769, 0.189]])
    sepia = cv2.transform(img_bgr, sepia_k)
    sepia = np.clip(sepia, 0, 255).astype(np.uint8)
    noise = np.random.randint(0, 25, sepia.shape, dtype=np.uint8)
    grainy = cv2.add(sepia, noise)
    h, w = grainy.shape[:2]
    kx = cv2.getGaussianKernel(w, w/3)
    ky = cv2.getGaussianKernel(h, h/3)
    denom = (ky @ kx.T).max()
    mask = (ky @ kx.T) / denom
    result = np.zeros_like(grainy)
    for i in range(3):
        result[:,:,i] = (grainy[:,:,i] * mask).astype(np.uint8)
    return result

# Applies a glitch look with RGB offset and random scanlines.
# If removed, the glitch style fallback stops working.
# Change the offset and strip counts here.
def _style_glitch(img_bgr):
    h, w = img_bgr.shape[:2]
    b, g, r = cv2.split(img_bgr)
    offset = max(1, w // 20)
    glitch = cv2.merge([np.roll(b, -offset, axis=1), g, np.roll(r, offset, axis=1)])
    for _ in range(15):
        y = np.random.randint(0, h-5)
        sh = np.random.randint(2, 10)
        so = np.random.randint(-w//6, w//6)
        glitch[y:y+sh, :] = np.roll(glitch[y:y+sh, :], so, axis=1)
    scanlines = np.zeros_like(glitch)
    scanlines[::3, :] = 40
    return cv2.subtract(glitch, scanlines)

# Applies an oil painting look using blur + quantization.
# If removed, the oil style fallback stops working.
# Tune the bilateral filter and kmeans color count here.
def _style_oil(img_bgr):
    result = img_bgr.copy()
    result = cv2.bilateralFilter(result, 7, 50, 50)
    result = cv2.bilateralFilter(result, 7, 50, 50)
    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 100)
    result = cv2.subtract(result, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR))
    data = result.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(data, 12, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    centers = centers.astype(np.uint8)
    return centers[labels.flatten()].reshape(img_bgr.shape)

# Applies a pop art look: 5 colors + boosted saturation.
# If removed, the pop-art style fallback stops working.
# Change the kmeans color count here (5 = classic pop art).
def _style_pop_art(img_bgr):
    data = img_bgr.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(data, 5, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    centers = centers.astype(np.uint8)
    result = centers[labels.flatten()].reshape(img_bgr.shape)
    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
    hsv[:,:,1] = np.clip(hsv[:,:,1] * 1.5, 0, 255).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

# Applies a cyberpunk look with teal/orange shift and magenta edges.
# If removed, the cyberpunk style fallback stops working.
# Adjust the hue shift and edge color here.
def _style_cyberpunk(img_bgr):
    result = img_bgr.copy()
    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
    hsv[:,:,0] = (hsv[:,:,0] + 20) % 180
    hsv[:,:,1] = np.clip(hsv[:,:,1] + 40, 0, 255).astype(np.uint8)
    result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    h, w = result.shape[:2]
    kx = cv2.getGaussianKernel(w, w/4)
    ky = cv2.getGaussianKernel(h, h/4)
    denom = (ky @ kx.T).max()
    mask = (ky @ kx.T) / denom
    for i in range(3):
        result[:,:,i] = (result[:,:,i] * (0.5 + 0.5 * mask)).astype(np.uint8)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, np.ones((2,2), np.uint8), iterations=1)
    result[edges > 0] = [255, 0, 255]
    return result

# Applies a soft watercolor look using blurs and paper grain.
# If removed, the watercolor style fallback stops working.
# Change the blur sizes and grain amount here.
def _style_watercolor(img_bgr):
    result = cv2.medianBlur(img_bgr, 7)
    result = cv2.medianBlur(result, 5)
    result = cv2.bilateralFilter(result, 9, 50, 50)
    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV)
    hsv[:,:,1] = (hsv[:,:,1] * 0.8).astype(np.uint8)
    result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    texture = np.random.randint(0, 15, result.shape, dtype=np.uint8)
    return cv2.add(result, texture)

STYLE_FUNCTIONS = {
    'anime': _style_anime,
    'neon': _style_neon,
    'vintage': _style_vintage,
    'glitch': _style_glitch,
    'oil': _style_oil,
    'pop-art': _style_pop_art,
    'cyberpunk': _style_cyberpunk,
    'watercolor': _style_watercolor,
}


# Picks a style from the prompt and applies it locally with OpenCV.
# If removed, image editing has no fallback when every AI fails.
# Add new styles to STYLE_FUNCTIONS and _detect_style_from_prompt.
def _apply_style_local(image_data, prompt):
    style = _detect_style_from_prompt(prompt)
    img_bgr = _b64_to_cv2(image_data)
    if img_bgr is None or img_bgr.size == 0:
        return None
    h, w = img_bgr.shape[:2]
    if h > 1024 or w > 1024:
        scale = 1024 / max(h, w)
        new_size = (int(w * scale), int(h * scale))
        img_bgr = cv2.resize(img_bgr, new_size, interpolation=cv2.INTER_AREA)
    fn = STYLE_FUNCTIONS.get(style)
    if fn:
        try:
            result = fn(img_bgr)
            return _cv2_to_b64(result)
        except Exception as e:
            print(f"[LOCAL STYLE {style}] Failed: {str(e)[:200]}")
    return None


# Tries the Gemini image models to transform a photo directly.
# If removed, image editing skips its best quality step.
# Add or remove model names in the models list here.
def _try_gemini_image_models(image_data, prompt, keys):
    models = ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]
    for key in keys:
        for model in models:
            for attempt in range(2):
                try:
                    contents = {
                        "contents": [{
                            "parts": [
                                {"inline_data": {"mime_type": "image/png", "data": image_data}},
                                {"text": prompt}
                            ]
                        }],
                        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
                    }
                    data = json.dumps(contents).encode()
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                    req = urllib.request.Request(
                        url,
                        data=data,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        result = json.loads(resp.read().decode())
                        candidates = result.get("candidates", [{}])
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            idata = part.get("inlineData") or part.get("inline_data")
                            if idata:
                                return idata["data"]
                except urllib.error.HTTPError as e:
                    body = e.read().decode()[:200]
                    if '429' in str(e.code) or 'quota' in body.lower() or 'RESOURCE_EXHAUSTED' in body:
                        import time
                        time.sleep(2 ** attempt)
                        continue
                    break
                except Exception:
                    break
    return None


# Describes the image with Gemini, then regenerates it via Pollinations.
# If removed, image editing loses its middle fallback step.
# Change the description prompt here to change the result.
def _try_describe_and_pollinations(image_data, prompt, keys):
    for key in keys:
        try:
            desc_prompt = "Describe this person's appearance briefly (hair, eyes, face shape, style). 1 sentence."
            desc_contents = {
                "contents": [{
                    "parts": [
                        {"inline_data": {"mime_type": "image/png", "data": image_data}},
                        {"text": desc_prompt}
                    ]
                }]
            }
            data = json.dumps(desc_contents).encode()
            model = "gemini-2.0-flash"
            desc_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            req = urllib.request.Request(
                desc_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                candidates = result.get("candidates", [{}])
                content = candidates[0].get("content", {})
                parts = content.get("parts", [{}])
                description = parts[0].get("text", "")
                if description:
                    style_hint = _detect_style_from_prompt(prompt)
                    combined = f"{description.strip()} in {style_hint} artistic style, {prompt[:100]}"
                    from urllib.parse import quote as uq
                    poll_url = f"https://image.pollinations.ai/prompt/{uq(combined)}"
                    preq = urllib.request.Request(poll_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(preq, timeout=60) as presp:
                        img_data = presp.read()
                        if len(img_data) > 1000:
                            return base64.b64encode(img_data).decode()
        except Exception as e:
            print(f"[DESCRIBE+POLLINATIONS] Failed: {str(e)[:200]}")
            continue
    return None


# Main image transform function: Gemini models, then describe+Pollinations, then OpenCV.
# If removed, all image editing endpoints break.
# Add new fallback steps here in order.
def _gemini_image_generate(image_data, prompt, custom_key=None):
    if custom_key:
        keys = [custom_key]
    else:
        keys = [_get_keys("GEMINI_KEY"), _get_keys("GEMINI_KEY2")]

    # Step 1: Try Gemini image models directly
    result = _try_gemini_image_models(image_data, prompt, keys)
    if result:
        return result

    # Step 2: Try describe + Pollinations
    result = _try_describe_and_pollinations(image_data, prompt, keys)
    if result:
        return result

    # Step 3: Fallback to local OpenCV artistic effects
    if HAS_CV2:
        try:
            result = _apply_style_local(image_data, prompt)
            if result:
                return result
        except Exception as e:
            print(f"[LOCAL FALLBACK] Failed: {str(e)[:200]}")

    return None


# Makes an image from text only, using Pollinations then local OpenCV art.
# If removed, text-to-image generation breaks.
# Change the fallback chain here.
def _gemini_text_to_image(prompt, custom_key=None):
    # Step 1: Try Pollinations
    result = _pollinations_generate(prompt)
    if result:
        return result

    # Step 2: Generate locally with OpenCV
    if HAS_CV2:
        try:
            style = _detect_style_from_prompt(prompt)
            canvas = _gen_abstract_portrait(prompt, style)
            result = _cv2_to_b64(canvas)
            if result:
                return result
        except Exception as e:
            print(f"[TEXT-TO-IMAGE LOCAL] Failed: {str(e)[:200]}")

    return None


# Sends the messages to the OpenRouter API and returns the reply text.
# If removed, the last-resort AI provider stops working.
# Add your OpenRouter key in settings or in the .env file.
def _openrouter_request(messages, model="openai/gpt-4o-mini", temperature=0.7, max_tokens=2048, custom_key=None):
    if custom_key:
        keys = [custom_key]
    else:
        keys = [_get_keys("OPENROUTER_KEY"), _get_keys("OPENROUTER_KEY2")]
    valid_keys = [k for k in keys if k]
    if not valid_keys:
        return None
    for key in valid_keys:
        try:
            data = json.dumps({
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }).encode()
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "User-Agent": UA,
                    "HTTP-Referer": "http://localhost:8000",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                return result["choices"][0]["message"]["content"].strip()
        except Exception:
            continue
    return None


# Same as _groq_request but streams the reply token by token.
# If removed, streaming challenge generation breaks (no live loading).
# Used by generate_challenges_stream.
def _groq_request_stream(messages, model="llama-3.3-70b-versatile", temperature=0.9, max_tokens=3000):
    valid_keys = [k for k in [_get_keys("GROQ_KEY"), _get_keys("GROQ_KEY2")] if k]
    if not valid_keys:
        return
    for key in valid_keys:
        try:
            data = json.dumps({
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }).encode()
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "User-Agent": UA,
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                buffer = ""
                while True:
                    chunk = resp.read(4096)
                    if not chunk:
                        break
                    buffer += chunk.decode()
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line or line.startswith(":"):
                            continue
                        if line.startswith("data: "):
                            payload = line[6:]
                            if payload == "[DONE]":
                                return
                            try:
                                obj = json.loads(payload)
                                delta = obj.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                pass
        except Exception:
            continue
    return None


# Local (no-AI) chat reply — used when no API key is configured so the
# chat still responds. If removed, chat needs an AI key to say anything.
def _local_chat_reply(user_message, challenge_context="", ai_name="ChillX"):
    import re
    msg = (user_message or "").lower()
    # Pull a hint out of the challenge context when it's about a challenge.
    hint = ""
    if challenge_context:
        m = re.search(r"(objective[^\n]*|target[^\n]*|hint[^\n]*)", challenge_context, re.I)
        if m:
            hint = m.group(1).strip()
    if re.search(r"\b(hi|hello|hey|yo|sup)\b", msg):
        return f"Hey! 👋 I'm {ai_name}, your ChillX companion. I'm running in offline mode right now (no AI key set), but I can still point you at your challenges and games. What are you working on?"
    if "challenge" in msg or "quest" in msg or "daily" in msg:
        if hint:
            return f"Your current challenge objective: **{hint}**. Head to the Challenges page, open the game link, and go for it! You've got this 💪"
        return "Your daily challenges are waiting on the Challenges page — open one, play the game, and submit proof when you hit the target. Good luck! 🎯"
    if "hint" in msg or "help" in msg or "stuck" in msg:
        if hint:
            return f"Here's a nudge: {hint}. Focus on the target, take your time, and try again — you're closer than you think!"
        return "Try breaking the task into smaller steps, or open the challenge's game link to see the mechanics. You've got this! 🚀"
    if "game" in msg or "play" in msg or "multiplayer" in msg:
        return "Head to the home page and hit **START** to jump into multiplayer, or open any game from the Games section. Want a tip for a specific game?"
    if re.search(r"\b(thank|thanks|thx|ty)\b", msg):
        return "You're welcome! 😊 Anything else you need help with?"
    if re.search(r"\b(who are you|what are you|your name)\b", msg):
        return f"I'm **{ai_name}**, your friendly AI companion on ChillX. I help with challenges, games, and staying motivated. (I'm in offline mode right now — add an AI key in Settings to unlock my full brain!)"
    return f"Got it! I'm running in offline mode (no AI key set), so my answers are basic — but I can still help you navigate challenges and games. What would you like to do?"


# Main chat function: takes the user message and returns the AI reply.
# If removed, the whole AI chat feature stops working.
# Change the system prompt below to change the AI personality.
def chat_response(user_message, challenge_context, history=None, ai_name="ChillX", personality="", custom_keys=None, models=None, image_data=None):
    if history is None:
        history = []
    if custom_keys is None:
        custom_keys = {}
    if models is None:
        models = {}
    # The chat system prompt: tells the AI its personality and when to refuse quiz answers.
    system_prompt = (
        f"You are {ai_name}, a friendly and encouraging AI companion on the ChillX platform. "
        "The user has daily challenges. Your personality:\n"
        "1. Be WARM, FRIENDLY, and HELPFUL at all times.\n"
        "2. NEVER give direct answers to quiz or riddle questions **that match the CURRENT QUIZ QUESTIONS list below**. For those, refuse playfully with a fresh response and give a hint instead. For ANY other general knowledge question not in that list, answer fully and freely — those are not quiz cheating.\n"
        "3. For everything else — give full detailed answers using your knowledge freely. When writing code, format it properly with ```language blocks.\n"
        "4. Keep responses under 4 sentences unless asked a detailed question.\n\n"
    )
    if personality:
        system_prompt += f"PERSONALITY & MEMORY: {personality}\n\n"
    system_prompt += (
        "USER CONTEXT:\n" + challenge_context + "\n\n"
        "REMEMBER: Only refuse answers for questions that match the CURRENT QUIZ QUESTIONS list above. For all other general knowledge questions, answer freely and fully. Don't be over-cautious."
    )
    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-10:]:
        messages.append(h)
    messages.append({"role": "user", "content": user_message})

    groq_key = custom_keys.get("groq") or None
    gemini_key = custom_keys.get("gemini") or None
    openrouter_key = custom_keys.get("openrouter") or None
    groq_model = models.get("groq", "llama-3.3-70b-versatile")
    gemini_model = models.get("gemini", "gemini-2.0-flash")
    openrouter_model = models.get("openrouter", "openai/gpt-4o-mini")

    if not groq_key and not _get_keys("GROQ_KEY") and not gemini_key and not _get_keys("GEMINI_KEY") and not openrouter_key and not _get_keys("OPENROUTER_KEY"):
        # No AI keys configured — answer from a small built-in brain so the
        # chat still works the moment someone opens the site.
        return _local_chat_reply(user_message, challenge_context, ai_name)

    if image_data:
        result = _gemini_request(system_prompt + "\n\n" + user_message, image_data=image_data, custom_key=gemini_key, model=gemini_model)
        if not result:
            result = _groq_request(messages, model=groq_model, temperature=0.8, max_tokens=2048, custom_key=groq_key)
    else:
        result = _groq_request(messages, model=groq_model, temperature=0.8, max_tokens=2048, custom_key=groq_key)
        if not result:
            result = _gemini_request(system_prompt + "\n\n" + user_message, custom_key=gemini_key, model=gemini_model)
    if not result:
        result = _openrouter_request(messages, model=openrouter_model, temperature=0.8, max_tokens=2048, custom_key=openrouter_key)
    return result or "I'm here to help! Ask me anything about your challenges."


# Builds the system + user prompts that ask the AI for new challenges.
# If removed, challenge generation has no prompt to send.
# Edit the system_prompt and user_prompt below to change the output format.
def _build_challenge_prompt(categories, difficulty, count=4, history=None, level=1, user_performance=None):
    import random
    if history is None:
        history = []
    if user_performance is None:
        user_performance = "USER IS NEW — no challenge history yet. Make challenges welcoming and easy to start."

    history_text = ""
    if history:
        history_text = "\n\nPREVIOUSLY GIVEN (DO NOT REPEAT these titles): " + ", ".join(history[-30:])

    level = max(1, level)

    # Pick a random creative twist to ensure variety across generations
    twists = [
        "Make it a SPEEDRUN challenge — tight time limit, high target.",
        "Focus on PRECISION — challenge requires near-perfect accuracy.",
        "Make it a GRIND challenge — repetitive but rewarding with high XP.",
        "Focus on CONSISTENCY — do well across multiple attempts.",
        "Make it a SINGLE-ATTEMPT challenge — one shot, no retries.",
        "Focus on IMPROVEMENT — user must beat their last result.",
        "Make it a PERFECT RUN — all or nothing, high risk high reward.",
        "Focus on ENDURANCE — sustain performance over a long session.",
    ]
    twist = random.choice(twists)

    # The main challenge prompt: rules for the AI on how to design challenges.
    system_prompt = (
        "You are ChillX's Master Challenge Architect — a creative quest designer. "
        "Generate specific, concrete challenges that the user can actually do right now. "
        "NEVER vague like 'Learn Python' or 'Practice drawing'. Always name real tools, real games, "
        "or specific measurable tasks with a working link.\n\n"

        "CHALLENGE DESIGN PHILOSOPHY:\n"
        "Think like a quest designer in an RPG. The best challenges are:\n"
        "  • OBJECTIVE-BASED — a specific in-game milestone (complete a word, hire an employee, "
        "    finish a level, reach a checkpoint, unlock a character, hit a combo, survive X waves)\n"
        "  • MEASURABLE — the user knows exactly when they've done it\n"
        "  • VARIED — every generation should feel DIFFERENT, not 'Score 500 then Score 1000 then Score 5000'\n"
        "  • GAME-FLAVORED — reflect what makes each game UNIQUE, not generic metrics\n"
        "  • FUN — would the user feel a small dopamine hit when they complete it?\n\n"

        "GOOD vs BAD CHALLENGES:\n"
        "BAD:  'Score 500 in Subway Surfers'  (just a number, feels like a test)\n"
        "GOOD: 'Complete a word by collecting all letters in Subway Surfers'  (a real in-game objective)\n"
        "BAD:  'Score 1000 in Monkey Mart'  (boilerplate)\n"
        "GOOD: 'Hire your first employee in Monkey Mart'  (the real beginner milestone)\n"
        "BAD:  'Score 5000 in Tetris'  (generic)\n"
        "GOOD: 'Clear a 4-line Tetris (the first real achievement)'  (the actual goal of Tetris)\n"
        "BAD:  'Score 200 in 2048'  (boring)\n"
        "GOOD: 'Reach the 256 tile in 2048'  (the actual game win condition)\n"
        "BAD:  'Win 3 matches in Smash Karts'  (fine, but bland)\n"
        "GOOD: 'Get your first win using the green shell in Smash Karts'  (specific, funny)\n\n"

        "IN-GAME MILESTONES (think creatively per game):\n"
        "When picking a game, ASK YOURSELF: what are the actual fun things to do in this game?\n"
        "  • Search the web, pick ANY free browser game, then name a real in-game objective:\n"
        "    complete a level, clear X lines, reach a tile/score, survive X seconds,\n"
        "    win a round, unlock something the game really has, beat a checkpoint.\n"
        "  • Vary the games constantly — never repeat a game across challenges or days.\n\n"
        "  • In-app games (typing/reaction/cps/memory/runner/tictactoe):\n"
        "      - typing: hit X WPM with X% accuracy, beat your previous score, sustain X WPM for full test\n"
        "      - reaction: average X ms across 5 attempts, get a sub-X ms best, beat your PB\n"
        "      - cps: hit X CPS in X seconds, sustain X CPS for the full time, beat your PB\n"
        "      - memory: reach level X, beat your previous best, hit a streak of X perfect rounds\n"
        "      - runner: run X meters, beat your PB, survive X seconds without dying\n"
        "      - tictactoe: win a match vs AI, get a 3-win streak, beat AI on hard\n\n"

        "TODAY'S CREATIVE TWIST:\n"
        f"{twist}\n\n"

        "LINKS AND GAME_KEY:\n"
        "For every challenge, output BOTH a category AND a game_key:\n"
        "  • game_key is the SPECIFIC game the challenge uses.\n"
        "  • IN-APP (built into ChillX): typing, reaction, cps, aim3d, memory, tictactoe, runner\n"
        "  • POKI games (PREFERRED for gaming) — pick ONLY from this verified "
        "list of games that exist on poki.com (the system builds the URL, and "
        "unlisted names 404): 2048, Age of War, Angry Birds, Basketball Master, "
        "Basketball Stars, Bottle Flip, Bubble Shooter, Chess, Crazy Cars, "
        "Cut the Rope, Drive Mad, Ducklife, Fireboy and Watergirl, Football Legends, "
        "Friday Night Funkin, Fruit Ninja, Geometry Dash, Gun Mayhem 2, Iron Snout, "
        "Learn to Fly 3, Love Balls, Merge Cakes, Minecraft Classic, Monkey Mart, "
        "Moto X3M, Mr Bullet, Paper.io 2, Parking Fury 3D, Penalty Shooters 2, "
        "Red Ball 4, Retro Bowl, Rooftop Snipers, Run 3, Shell Shockers, Slope, "
        "Smash Karts, Stack, Stickman Hook, Subway Surfers, Tag, Temple of Boom, "
        "Temple Run 2, Tetris, Traffic Mania, Tunnel Rush, World's Hardest Game. "
        "Set game_key to 'poki:<game_name>' (underscores, lowercase, no spaces, "
        "e.g. poki:knife_hit is NOT allowed, use poki:bubble_shooter). The system "
        "builds the poki.com URL from that name, so leave 'link' EMPTY for poki games. "
        "If the game you want is not in this list, do NOT invent a poki key — use an "
        "in-app game or a web: link instead.\n"
        "  • WEB games (non-poki, e.g. humanbenchmark.com) — game_key is 'web:<name>', "
        "and you MUST put the real playable game URL in the 'link' field (not empty). "
        "Choose freely, do not reuse games.\n"
        "  • OFFLINE (coding, art, fitness, quiz) — game_key is \"\"\n"
        "  • The TITLE must name the specific game AND an in-game objective:\n"
        "      GOOD 'Win a Tic Tac Toe match'        (game_key: tictactoe)\n"
        "      GOOD 'Clear a 4-line Tetris'          (game_key: poki:tetris)\n"
        "      GOOD 'Hire your first employee in Monkey Mart' (game_key: poki:monkey_mart)\n"
        "      GOOD 'Complete a word in Subway Surfers' (game_key: poki:subway_surfers)\n"
        "      GOOD 'Reach the 256 tile in 2048'     (game_key: poki:2048)\n"
        "  • Output link as \"\" (empty) for in-app/poki/offline. The system builds those.\n"
        "  • For non-poki web games ALWAYS output a real https link you found via search.\n\n"

        "POSSIBILITY RULES (STRICT):\n"
        "  • You have Google Search. Before choosing a game, search the web to make sure "
        "the game is real, free, and playable in a browser RIGHT NOW.\n"
        "  • NEVER invent game mechanics. Only set objectives that the game ACTUALLY has.\n"
        "  • If a game has no characters, do NOT say 'unlock a character'. If it has no "
        "level system, do NOT say 'reach level 5'. Use real milestones only.\n"
        "  • When unsure what a game supports, pick a safe measurable objective the game "
        "definitely tracks (score, distance, time survived, rounds won, lines cleared).\n"
        "  • Every challenge must be completable by a normal player at the user's level.\n\n"

        "TARGET SCALING (level-aware, AUTHORITATIVE for in-app games):\n"
        "  Level 1-4 (beginner):\n"
        "    typing=15 WPM, reaction=350ms, cps=4, aim3d=500, memory=2, runner=5, quiz=5\n"
        "  Level 5-14 (novice):\n"
        "    typing=25 WPM, reaction=280ms, cps=5, aim3d=1000, memory=4, runner=11, quiz=7\n"
        "  Level 15-29 (intermediate):\n"
        "    typing=35 WPM, reaction=220ms, cps=7, aim3d=2000, memory=6, runner=21, quiz=8\n"
        "  Level 30+ (advanced):\n"
        "    typing=50 WPM, reaction=180ms, cps=9, aim3d=3000, memory=10, runner=21, quiz=10\n"
        "  The system OVERRIDES your target with these level numbers when it builds the game link, "
        "so write your objective to match the level row above exactly.\n\n"

        "STRUCTURED CHALLENGE FIELDS (MANDATORY):\n"
        "Every challenge item MUST also include these fields so the system can display and verify the goal:\n"
        "  • objective: the measurable goal as a short action phrase, e.g. 'hit 7 clicks per second', "
        "'reach the 256 tile', 'score 35 wpm with 95% accuracy'\n"
        "  • metric: ONLY for in-app games — wpm|cps|ms|score|level|reps|time|distance|completion|win. "
        "Empty string for web and offline challenges.\n"
        "  • target: the numeric goal matching the metric — use the level-scaled number from the table above "
        "so the title, objective and target agree. Empty string for web/offline and for tictactoe "
        "(metric is 'win').\n"
        "  • unit: wpm|%|ms|cps|points|level|seconds|reps|km — must match the metric. Empty for web/offline.\n"
        "  • estimated_duration: how long it actually takes, e.g. '30 seconds', '3 minutes'.\n"
        "  • special_condition: an optional extra rule (e.g. 'no backspace', 'one attempt only', "
        "'eyes closed') or empty string.\n"
        "  • The title, objective and target MUST all describe the SAME goal — never contradict each other.\n\n"

        "DIFFICULTY AND XP/COIN REWARDS:\n"
        "  Easy       (5-15 min)  →  XP 25-50,   coins 5-10\n"
        "  Medium     (15-30 min) →  XP 50-100,  coins 10-25\n"
        "  Hard       (30-60 min) →  XP 100-250, coins 25-50\n"
        "  Nightmare  (60+ min)   →  XP 250-500, coins 50-100\n\n"

        "PROOF TYPE BY CATEGORY:\n"
        "  text: coding, tictactoe, fitness (sets/reps), quiz\n"
        "  image: art, gaming, cps, reaction, aim3d, memory, runner, quiz, fitness\n"
        "  both: creative projects (art + writeup, code + screenshot)\n\n"

        "USER PERFORMANCE ADAPTATION:\n"
        f"{user_performance}\n\n"

        "RULES:\n"
        "1. THINK PER-GAME — every game has UNIQUE fun milestones. Don't reuse the same template across games.\n"
        "2. NAME THE OBJECTIVE — title must describe WHAT you do in the game, not a score threshold\n"
        "3. BE SPECIFIC — every title is a DOABLE in-game action with a measurable outcome\n"
        "4. USE REAL GAME_KEYS — pick from the lists above\n"
        "5. SCALE TARGETS — match the user's level and trend\n"
        "6. DISTRIBUTE CATEGORIES EVENLY — this is critical. The user picks N interests; you MUST cover ALL of them across the batch (not just gaming). Math: at minimum 1 challenge per category the user selected. If they have 9 interests and you generate 9, each interest gets exactly 1. If they have 9 interests and you generate 18, each gets 2. NEVER let gaming dominate just because the gaming catalog is long — art, fitness, coding, typing, reaction, cps deserve equal airtime. Treat gaming as ONE category among many, not the default.\n"
        "7. ONE LONG CHALLENGE — if generating 3+, make 1 is_long=true (the Master Quest)\n"
        "8. NO REPEATS — never reuse a title from history. ALSO: never copy few-shot example titles verbatim — use them as STYLE inspiration only. Every challenge title must be ORIGINAL, not 'Complete a word in Subway Surfers' or anything from the examples list.\n"
        "9. APPLY TODAY'S CREATIVE TWIST — let it inspire the challenge designs\n"
        "10. DESCRIPTIONS TONE — write like a friend who's genuinely excited about the dare. Casual, punchy, 1-2 sentences. Vary the style (hype, challenge, funny, dare). Never use the pattern 'Play X on Poki and do Y. Screenshot Z.'\n"
        "10b. BANNED FILLER WORDS — never use any of: 'show off', 'spice up', 'test your', 'prove yourself', 'put your skills', 'time to shine', 'boost your', 'it's time for', 'how sweet', 'awesome', 'epic', 'master the', 'unleash', 'game time', 'let the games begin', 'are you ready', 'are you up for', 'challenge accepted', 'on your marks', 'get ready', 'dive into', 'embark on', 'impressive'. Avoid generic motivational openers entirely — START with the actual objective (the verb + the in-game thing). NEVER explain the game mechanic ('collect coins', 'stack blocks', 'merge tiles') — name the WIN CONDITION instead. The description should make someone immediately know what to DO, not feel vaguely inspired.\n"
        "11. NO SCORE-ONLY OR GENERIC PLAY CHALLENGES — every challenge must describe a specific in-game objective (complete a word, hire an employee, clear a Tetris), not a threshold or vague 'just play' instruction\n"
        "12. OUTPUT FORMAT — a JSON array only, no prose, no markdown fences\n\n"

        "VALID CATEGORIES (output `category` MUST be one of these):\n"
        "  • coding, art, gaming, fitness, quiz  (interest categories)\n"
        "  • typing, reaction, cps                          (in-app game interests)\n"
        "  NEVER invent a category. If the user did not pick 'gaming' but you want a poki link, use category=\"gaming\". "
        "If the user did not pick 'memory' or 'tictactoe' as an interest, do not assign those categories — instead use 'gaming' for those game_keys, or pick a different in-app game the user DID pick (typing/reaction/cps/quiz). The in-app game_keys are: typing, reaction, cps, aim3d, memory, tictactoe, runner, quiz, fitness — pick ONE whose category the user actually has.\n"
    )

    if categories:
        categories_text = ', '.join(categories)
        category_count = len(categories)
    else:
        categories_text = 'general'
        category_count = 0

    # User prompt: the user's interests, difficulty, level and the required JSON format.
    user_prompt = (
        f"User interests (categories to choose from): {categories_text}\n"
        f"Difficulty preference: {difficulty}\n"
        f"User level: {level}\n"
        f"Generate exactly {count} challenges."
        f"{history_text}\n\n"
        f"MANDATORY CATEGORY DISTRIBUTION — VIOLATING THIS IS A FAILURE:\n"
        f"  • User has {category_count} interests: {categories_text}\n"
        f"  • You are generating {count} challenges.\n"
        f"  • EVERY single interest above MUST appear at least once in the output. No exceptions.\n"
        f"  • If 9 interests and 9 challenges, each interest gets EXACTLY 1 challenge — no repeats.\n"
        f"  • If 9 interests and 18 challenges, each interest gets 2 — no repeats.\n"
        f"  • Do NOT add 4 gaming challenges to pad the count. Treat gaming as 1 of the {category_count} equal slots, not the default filler.\n"
        f"  • Plan the category assignment FIRST, then design each challenge to fit its assigned category.\n"
        f"\n\n"
        f"REMEMBER: Each title should describe a SPECIFIC IN-GAME OBJECTIVE (complete a word, "
        f"hire an employee, clear a 4-line Tetris, beat a level, unlock a character) — not just "
        f"'Score X in Y'. Make every challenge feel like a real quest with a clear win condition."
        f"\n\n"
        f"Output ONLY a valid JSON array — each item MUST include:\n"
        f'{{"title":"str (must name the specific game AND an in-game objective)",'
        f'"description":"str (1-2 sentences describing the exact objective, not just a score)",'
        f'"category":"str",'
        f'"game_key":"typing|reaction|cps|aim3d|memory|tictactoe|runner|quiz|fitness|poki:xxx|web:xxx|empty",'
        f'"proof_type":"text|image|both","xp_reward":int,"coin_reward":int,'
        f'"is_long":bool,"link":"real https URL ONLY for web games found via search, else empty",'
        f'"difficulty":"easy|medium|hard|nightmare",'
        f'"objective":"str (the measurable goal as an action phrase, e.g. hit 7 clicks per second)",'
        f'"metric":"wpm|cps|ms|score|level|reps|time|distance|completion|win — empty for web/offline",'
        f'"target":"numeric goal matching the level-scaled table — empty for web/offline/tictactoe",'
        f'"unit":"wpm|%|ms|cps|points|level|seconds|reps|km — matches metric, empty for web/offline",'
        f'"estimated_duration":"str e.g. 30 seconds",'
        f'"special_condition":"str or empty"}}'
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


# Fills in default fields on a challenge dict so it always has all the keys.
# If removed, generated challenges can be missing fields and break the UI.
# Add new default fields here if a challenge gets a new key.
def _normalize_challenge(obj, default_category="general"):
    obj.setdefault("proof_type", "text")
    obj.setdefault("is_long", False)
    obj.setdefault("xp_reward", 50)
    obj.setdefault("coin_reward", 10)
    obj.setdefault("category", default_category)
    obj.setdefault("link", "")
    obj.setdefault("game_key", "")
    obj.setdefault("objective", "")
    obj.setdefault("metric", "")
    obj.setdefault("target", None)
    obj.setdefault("unit", "")
    obj.setdefault("estimated_duration", "")
    obj.setdefault("special_condition", "")
    return obj


# Prepares level, history and user performance for the prompt.
# If removed, challenge generation loses the user context.
# Change the defaults here (level 1, empty history, etc).
def _resolve_prompt_context(user=None, level=1, history=None, user_performance=None):
    if level is None and user is not None:
        level = getattr(user, "level", 1) or 1
    level = max(1, level or 1)
    if user is not None and user_performance is None:
        try:
            from .user_performance import format_summary_for_prompt
            user_performance = format_summary_for_prompt(user)
        except Exception:
            user_performance = "User profile unavailable."
    if history is None:
        history = []
    if not user_performance:
        user_performance = ""
    return history, level, user_performance


# Non-streaming: asks the AI for challenges and returns the full list.
# If removed, normal challenge generation breaks everywhere.
# Used by views and challenge_gen. Calls Gemini (web search), then Groq, then OpenRouter.
def generate_challenges(categories, difficulty, count=4, history=None, level=1, user=None, user_performance=None):
    history, level, user_performance = _resolve_prompt_context(
        user=user, level=level, history=history,
        user_performance=user_performance,
    )
    messages = _build_challenge_prompt(
        categories, difficulty, count, history, level,
        user_performance=user_performance,
    )
    result = _gemini_request(messages[1]["content"], search=True)
    if not result:
        result = _groq_request(messages, temperature=0.9, max_tokens=4000)
    if not result:
        result = _openrouter_request(messages, temperature=0.9, max_tokens=4000)
    if result:
        try:
            idx = result.find("[")
            end = result.rfind("]")
            if idx >= 0 and end >= 0:
                data = json.loads(result[idx:end+1])
                if isinstance(data, list):
                    if categories:
                        default_cat = categories[0]
                    else:
                        default_cat = "general"
                    for obj in data:
                        _normalize_challenge(obj, default_cat)
                    return data
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # No AI key configured (or every provider failed) — build the batch
    # locally from the verified catalog so the site works with zero keys.
    try:
        from .challenge_catalog import local_generate_challenges
        local = local_generate_challenges(
            categories, difficulty, count, history, level,
            user=user,
        )
        if local:
            for obj in local:
                _normalize_challenge(obj, categories[0] if categories else "general")
            return local
    except Exception:
        pass
    return None


# Streaming version that yields challenges one by one as they come in.
# If removed, the live challenge loader breaks and falls back to non-streaming.
# It falls back to generate_challenges if the stream returns nothing.
def generate_challenges_stream(categories, difficulty, count=4, history=None, level=1, user=None, user_performance=None):
    history, level, user_performance = _resolve_prompt_context(
        user=user, level=level, history=history,
        user_performance=user_performance,
    )
    messages = _build_challenge_prompt(
        categories, difficulty, count, history, level,
        user_performance=user_performance,
    )
    if categories:
        default_cat = categories[0]
    else:
        default_cat = "general"

    # Try Gemini with web search first so games can use fresh found links
    yielded = 0
    gemini_results = _gemini_request(messages[1]["content"], search=True)
    if gemini_results:
        parsed = []
        try:
            idx = gemini_results.find("[")
            end = gemini_results.rfind("]")
            if idx >= 0 and end >= 0:
                data = json.loads(gemini_results[idx:end+1])
                if isinstance(data, list):
                    parsed = data
        except (json.JSONDecodeError, KeyError, TypeError):
            parsed = []
        for obj in parsed:
            _normalize_challenge(obj, default_cat)
            if obj.get("title"):
                yield obj
                yielded += 1
        if yielded > 0:
            return

    accumulated = ""
    yielded = 0
    try:
        for token in _groq_request_stream(messages, temperature=0.9, max_tokens=4000):
            if not token:
                continue
            accumulated += token
            # Find all complete JSON objects in accumulated text
            start = accumulated.find("{")
            while start >= 0:
                depth = 0
                for i in range(start, len(accumulated)):
                    c = accumulated[i]
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            obj_str = accumulated[start:i+1]
                            try:
                                obj = json.loads(obj_str)
                                _normalize_challenge(obj, default_cat)
                                if obj.get("title"):
                                    yield obj
                                    yielded += 1
                            except json.JSONDecodeError:
                                pass
                            accumulated = accumulated[i+1:]
                            start = accumulated.find("{")
                            break
                else:
                    break
    except Exception:
        pass

    # Fallback: if nothing yielded from stream, use non-streaming
    if yielded == 0:
        challenges = generate_challenges(
            categories, difficulty, count, history, level,
            user=user, user_performance=user_performance,
        )
        if challenges:
            for ch in challenges:
                yield ch


# Checks if the submitted text has impossible numbers for that game type.
# If removed, fake results like 9999 WPM pass the AI judge.
# Add new game checks here (reaction, cps, typing, etc).
def _game_specific_check(challenge_title, user_text):
    import re
    title_lower = challenge_title.lower()
    text_lower = user_text.lower()

    # Reaction challenge: check for realistic ms values
    if "reaction" in title_lower or ("ms" in title_lower and "reaction" in title_lower):
        ms_numbers = re.findall(r'(\d{2,4})\s*ms', text_lower)
        # Impossibly fast (<50ms) or impossibly slow (>2000ms for single, >500 avg)
        for n in ms_numbers:
            v = int(n)
            if v < 50 or v > 5000:
                return True
        # Sane format: should mention ms
        if not ms_numbers and ("reaction" not in text_lower or "ms" not in text_lower):
            return True

    # CPS challenge: check for realistic CPS values
    if "cps" in title_lower or "click" in title_lower:
        cps_numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(?:cps|cps?|clicks? per second)', text_lower)
        for n in cps_numbers:
            v = float(n)
            if v < 0.5 or v > 30:
                return True
        clicks = re.findall(r'(\d+)\s*(?:click|cps)', text_lower)
        for n in clicks:
            v = int(n)
            if v < 1 or v > 1000:
                return True

    # Typing challenge: check for realistic WPM (supports digits and written numbers)
    if "typing" in title_lower or "wpm" in title_lower or "monkeytype" in title_lower:
        wpm_numbers = re.findall(r'(\d{1,3})\s*(?:wpm|wpm?|words? per minute)', text_lower)
        for n in wpm_numbers:
            v = int(n)
            if v < 5 or v > 300:
                return True
        # Also catch written-out numbers like "forty two"
        word_map = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
            'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
            'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40,
            'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80,
            'ninety': 90, 'hundred': 100,
        }
        has_written_wpm = False
        for w in ['word', 'wpm', 'typing', 'type', 'keyboard']:
            if w in text_lower:
                has_written_wpm = True
                break
        has_number_word = False
        for w in word_map:
            if w in text_lower:
                has_number_word = True
                break
        if not wpm_numbers and not has_number_word and not has_written_wpm:
            return True

    # Memory challenge: check for realistic level
    if "memory" in title_lower or "card" in title_lower or "match" in title_lower:
        level_numbers = re.findall(r'(?:level|round|pair|match)\s*(\d+)', text_lower)
        for n in level_numbers:
            v = int(n)
            if v < 1 or v > 100:
                return True

    # Runner: check for realistic distance
    if "runner" in title_lower or "run" in title_lower or "dinosaur" in title_lower:
        dist_numbers = re.findall(r'(\d{1,5})\s*(?:m|meter|metre|score)', text_lower)
        if dist_numbers:
            for n in dist_numbers:
                v = int(n)
                if v < 1 or v > 50000:
                    return True

    return False


# Judges a text submission for a challenge and returns score/passed/feedback.
# If removed, text challenge submission stops working.
# Change the prompt below to change how the AI judges.
def check_submission_text(challenge_title, challenge_desc, user_text, target=None, unit=None, objective=""):
    # Quick game-specific validation (catches impossible numbers early)
    suspicious = _game_specific_check(challenge_title, user_text)
    if suspicious:
        suspicious_note = "Note: the numbers in this submission look unrealistic for this game — sanity-check them. "
    else:
        suspicious_note = ""

    goal = objective or challenge_desc or challenge_title
    target_line = ""
    if target not in (None, "", 0, "0"):
        unit = unit or ""
        target_line = f"TARGET: {target}{(' ' + unit) if unit else ''}\n"

    # Prompt that asks the AI to judge a text submission.
    prompt = (
        f"CHALLENGE: {challenge_title}\n"
        f"GOAL: {goal}\n"
        f"{target_line}"
        f"\n"
        f"USER SAYS:\n{user_text}\n\n"
        f"{suspicious_note}"
        f"Judge this like a reasonable human friend would — not a robot, not a pushover:\n"
        f"  • If the user clearly completed the goal, PASS. Give them the win.\n"
        f"  • A genuine attempt that lands just below the target still earns a pass at a low score — "
        f"real effort gets real credit.\n"
        f"  • Only FAIL for clear nonsense: gibberish, obviously fake numbers, a one-line "
        f"'I did it' with zero detail, or text that ignores the actual goal.\n"
        f"  • Vague but sincere = low score, still passed. Hits the goal with detail = high score.\n"
        f"Score 1-10: 8-10 clearly completed, 5-7 genuine effort or borderline, 1-4 fake or nonsense.\n\n"
        f"Output ONLY valid JSON:\n"
        f"{{\"score\": 1-10, \"feedback\": \"one short casual sentence, like a friend reacting\", \"passed\": true/false}}"
    )
    result = _groq_request([
        {"role": "user", "content": prompt}
    ], temperature=0.2, max_tokens=500)
    if not result:
        result = _openrouter_request([
            {"role": "user", "content": prompt}
        ], temperature=0.2, max_tokens=500)
    if result:
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return {"score": 5, "feedback": "AI judge unavailable. Giving benefit of doubt — marking completed.", "passed": True}


# Judges an image submission for a challenge and returns score/passed/feedback.
# If removed, image challenge submission stops working.
# Uses Gemini first, then falls back to OpenRouter text-only judging.
def check_submission_image(challenge_title, challenge_desc, image_base64, target=None, unit=None, objective=""):
    if image_base64 and "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]

    goal = objective or challenge_desc or challenge_title
    target_line = ""
    if target not in (None, "", 0, "0"):
        unit = unit or ""
        target_line = f"TARGET: {target}{(' ' + unit) if unit else ''}\n"

    # Prompt that asks the AI to judge an image submission.
    prompt = (
        f"CHALLENGE: {challenge_title}\n"
        f"GOAL: {goal}\n"
        f"{target_line}"
        f"\n"
        f"USER SUBMITTED A SCREENSHOT/IMAGE. Look at it like a reasonable human friend:\n"
        f"  • Read any score, level, WPM, time, number of wins, etc. shown in the image.\n"
        f"  • If the result clearly meets the goal, PASS.\n"
        f"  • A real attempt that's close but slightly under still gets a low-score pass — effort counts.\n"
        f"  • FAIL only if the image is unrelated to the challenge, blank/error page, screenshot of the "
        f"wrong game, or shows a result far below the goal.\n"
        f"Score 1-10: 8-10 clearly completed, 5-7 close/effort, 1-4 unrelated or obviously fake.\n\n"
        f"Output ONLY valid JSON:\n"
        f"{{\"score\": 1-10, \"feedback\": \"one short casual sentence, like a friend reacting\", \"passed\": true/false}}"
    )
    try:
        result_gemini = _gemini_request(prompt, image_data=image_base64)
    except Exception:
        result_gemini = None

    result = result_gemini

    if not result:
        # AI with image failed — try an OpenRouter model that accepts images.
        fallback_prompt = (
            f"CHALLENGE: {challenge_title}\n"
            f"DESCRIPTION: {challenge_desc}\n\n"
            f"NOTE: The user submitted an image but I can't see it. "
            f"If the user's text submission is empty or gibberish -> score 1, passed=false.\n"
            f"If they wrote something genuine -> score 6, passed=true (give benefit of doubt).\n\n"
            f"Feedback style: casual and cool, like a friend reacting.\n"
            f"Output ONLY valid JSON:\n"
            f"{{\"score\": 1-10, \"feedback\": \"casual one sentence reaction\", \"passed\": true/false}}"
        )
        result = _openrouter_request([
            {"role": "user", "content": fallback_prompt}
        ], temperature=0.2, max_tokens=500)

    if result:
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    # AI unavailable — user submitted an image, don't auto-reject
    return {"score": 5, "feedback": "Image submitted. AI judge temporarily unavailable — marking as completed.", "passed": True}


# Checks a coding challenge submission: the user pastes their code and the
# AI judges whether it actually solves the challenge. Instead of dumping raw
# compiler errors, it replies with friendly HINTS about what to fix.
# If removed, code submissions fall back to the plain text judge.
# Tune the prompt here (strictness, hint style) without touching the view.
def check_submission_code(challenge_title, challenge_desc, user_code, objective=""):
    goal = objective or challenge_desc or challenge_title
    prompt = (
        f"CHALLENGE: {challenge_title}\n"
        f"GOAL: {goal}\n"
        f"\n"
        f"USER'S CODE:\n{user_code}\n\n"
        f"Judge this code like a friendly mentor would:\n"
        f"  • Does the code actually solve the challenge? If yes, PASS it.\n"
        f"  • A real attempt that is close but has a small bug still earns a pass "
        f"at a low score — effort counts.\n"
        f"  • FAIL only for obvious nonsense: unrelated code, a copy-paste of the "
        f"question, one line that ignores the goal, or placeholder text.\n"
        f"  • NEVER dump raw compiler error text. If something is wrong, give a "
        f"SHORT HINT about what to look at (e.g. 'your loop condition looks off — "
        f"check what happens on the last item'), not the exact error.\n"
        f"Score 1-10: 8-10 clearly solves it, 5-7 close/effort, 1-4 nonsense.\n\n"
        f"Output ONLY valid JSON:\n"
        f"{{\"score\": 1-10, \"feedback\": \"one short casual sentence — a hint if not perfect, praise if solved\", \"passed\": true/false}}"
    )
    result = _groq_request([{"role": "user", "content": prompt}], temperature=0.2, max_tokens=500)
    if not result:
        result = _openrouter_request([{"role": "user", "content": prompt}], temperature=0.2, max_tokens=500)
    if result:
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return {"score": 5, "feedback": "Code submitted. AI judge unavailable — giving benefit of doubt.", "passed": True}


# Gives a short energetic fitness reaction from the AI.
# If removed, workout submissions get no AI feedback.
# Change the prompt or the fallback lines below.
def fitness_feedback(exercise, actual, target, mode, elapsed_secs=0):
    # Prompt asking the AI for one energetic fitness sentence.
    prompt = (
        f"Fitness workout result:\n"
        f"Exercise: {exercise}\n"
        f"Completed: {int(actual)} {mode}\n"
        f"Target: {int(target)} {mode}\n"
        f"Time: {elapsed_secs} seconds\n\n"
        f"Write ONE short, energetic sentence (max 15 words) reacting to this result "
        f"like a personal trainer. Be encouraging but real. "
        f"Don't use emojis. Don't use quotes.\n"
        f"Output ONLY: {{\"feedback\": \"your sentence here\"}}"
    )
    result = _groq_request([{"role": "user", "content": prompt}], temperature=0.4, max_tokens=100)
    if not result:
        result = _openrouter_request([{"role": "user", "content": prompt}], temperature=0.4, max_tokens=100)
    if result:
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end]).get("feedback", "")
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    passed = actual >= target
    if passed:
        fallbacks = [
            "Solid work — keep pushing those limits!",
            "Nailed it — that's what consistency looks like.",
            "Crushed it — every rep builds greatness.",
        ]
    else:
        fallbacks = [
            "Close one — next time you'll crush it.",
            "Good effort — progress is still progress.",
            "You showed up — that's the hardest part.",
        ]
    return fallbacks[int(actual) % len(fallbacks)]


# Asks the AI for a fresh C++ practice problem.
# If removed, the coding challenge feature breaks.
# Change the difficulty descriptions and rules below.
def generate_coding_problem(difficulty="easy", avoid=None):
    diff_desc = {
        "easy": "basic C++ concepts — variables, input/output, conditionals, simple loops. Suitable for a complete beginner.",
        "medium": "intermediate C++ — loops, arrays, strings, functions, simple algorithms.",
        "hard": "advanced C++ — pointers, recursion, complex algorithms, data structures.",
    }
    desc = diff_desc.get(difficulty, diff_desc["easy"])
    twists = [
        "involving number theory or digit manipulation",
        "about pattern printing or ASCII art",
        "working with character strings or text transformation",
        "performing mathematical series or sequences",
        "based on array traversal or manipulation",
        "using conditional logic with multiple branches",
        "involving counting or tallying specific items",
        "about validation or checking properties of numbers",
        "working with time, distance, or measurement conversion",
        "involving game-like logic (win/lose/turn-based)",
        "about generating or computing statistical values",
        "using nested loops for matrix-like operations",
        "involving search or find operations on data",
        "about formatting or transforming output in a specific way",
        "working with user interaction and input validation",
    ]
    twist = random.choice(twists)
    avoid_str = ""
    if avoid and isinstance(avoid, list) and len(avoid) > 0:
        avoid_pool = []
        for a in avoid:
            if a:
                avoid_pool.append(a)
        if avoid_pool:
            avoid_pool = avoid_pool[:5]
            avoid_str = "ABSOLUTELY DO NOT generate any problem similar to these recent problems:\n"
            for a in avoid_pool:
                avoid_str += f"- {a}\n"
    # Prompt asking the AI for a unique C++ problem.
    prompt = (
        f"Generate a unique C++ programming problem at {difficulty} difficulty.\n"
        f"{desc}\n\n"
        f"Style requirement: {twist}\n\n"
        f"{avoid_str}"
        "Rules:\n"
        "- Problem must be completable in under 20 lines of code\n"
        "- Must have a clear single correct output for given input\n"
        "- Do NOT reuse: Hello World, sum of two numbers, even/odd check, print 1 to 10, factorial, or largest of three\n"
        "- Do NOT generate problems involving prime numbers, palindromes, or Fibonacci\n"
        "- Be creative — generate something fresh and different from anything above\n\n"
        "Output ONLY valid JSON with no other text:\n"
        '{"problem": "Write a C++ program that ..."}'
    )
    result = _openrouter_request([{"role": "user", "content": prompt}], temperature=0.95, max_tokens=400)
    if result:
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(result[start:end])
                if data.get("problem"):
                    return data["problem"]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    fallbacks = {
        "easy": "Write a C++ program that takes an integer N and prints a right-angled triangle of asterisks N rows tall.",
        "medium": "Write a C++ program that reads a sentence and counts how many words in it start with a vowel.",
        "hard": "Write a C++ program that takes a string and compresses it by replacing consecutive repeated characters with the character followed by the count.",
    }
    return fallbacks.get(difficulty, fallbacks["easy"])


# Asks the AI to check if a user's C++ code solves the problem.
# If removed, coding submissions cant be verified.
# Change the prompt below to change what gets checked.
def check_cpp_code(code, problem):
    # Prompt asking the AI to check a C++ solution.
    prompt = (
        f"PROBLEM: {problem}\n\n"
        f"USER'S C++ CODE:\n```cpp\n{code}\n```\n\n"
        "Evaluate if this C++ code would compile and correctly solve the problem.\n"
        "Check for:\n"
        "- Syntax errors (missing semicolons, mismatched brackets, etc.)\n"
        "- Missing includes or main function\n"
        "- Logical correctness (does it produce the expected output?)\n\n"
        "Output ONLY valid JSON:\n"
        '{"passed": true/false, "feedback": "brief 1-sentence explanation of what is wrong or that it is correct"}'
    )
    result = _groq_request([
        {"role": "user", "content": prompt}
    ], temperature=0.1, max_tokens=500)
    if not result:
        result = _openrouter_request([
            {"role": "user", "content": prompt}
        ], temperature=0.1, max_tokens=500)
    if result:
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return {"passed": True, "feedback": "AI judge unavailable — marking as correct."}


# Reads two typing screenshots with Gemini and picks the winner.
# If removed, multiplayer typing screenshot battles break.
# Compare logic (WPM then accuracy) is in the if/else below.
def compare_typing_screenshots(screenshot_a, screenshot_b, player_a_name, player_b_name):
    # Prompt asking Gemini to read WPM and accuracy from a screenshot.
    prompt = (
        "Examine this typing test result screenshot. Identify the WPM (words per minute) "
        "and accuracy percentage displayed. "
        "Output ONLY valid JSON with this exact format:\n"
        '{"wpm": number, "accuracy": number}'
    )
    result_a = _gemini_request(prompt, image_data=screenshot_a, model="gemini-2.0-flash")
    parsed_a = None
    if result_a:
        try:
            start = result_a.find("{")
            end = result_a.rfind("}") + 1
            if start >= 0 and end > start:
                parsed_a = json.loads(result_a[start:end])
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    result_b = _gemini_request(prompt, image_data=screenshot_b, model="gemini-2.0-flash")
    parsed_b = None
    if result_b:
        try:
            start = result_b.find("{")
            end = result_b.rfind("}") + 1
            if start >= 0 and end > start:
                parsed_b = json.loads(result_b[start:end])
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    wpm_a = (parsed_a or {}).get('wpm', 0)
    wpm_b = (parsed_b or {}).get('wpm', 0)
    acc_a = (parsed_a or {}).get('accuracy', 0)
    acc_b = (parsed_b or {}).get('accuracy', 0)

    if wpm_a == 0 and wpm_b == 0:
        return {"winner": None, "reason": "Could not read results from screenshots"}

    if wpm_a > wpm_b:
        winner = player_a_name
        reason = f"{player_a_name}: {wpm_a} WPM {acc_a}% vs {player_b_name}: {wpm_b} WPM {acc_b}%"
    elif wpm_b > wpm_a:
        winner = player_b_name
        reason = f"{player_b_name}: {wpm_b} WPM {acc_b}% vs {player_a_name}: {wpm_a} WPM {acc_a}%"
    else:
        if acc_a > acc_b:
            winner = player_a_name
            reason = f"Tie WPM ({wpm_a}), {player_a_name} wins on accuracy: {acc_a}% vs {acc_b}%"
        elif acc_b > acc_a:
            winner = player_b_name
            reason = f"Tie WPM ({wpm_b}), {player_b_name} wins on accuracy: {acc_b}% vs {acc_a}%"
        else:
            winner = "draw"
            reason = f"Perfect tie: both {wpm_a} WPM {acc_a}%"

    return {
        "winner": winner,
        "reason": reason,
        "wpm_a": wpm_a,
        "wpm_b": wpm_b,
        "acc_a": acc_a,
        "acc_b": acc_b,
    }

