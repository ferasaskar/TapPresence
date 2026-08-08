"""Generate a synthetic but realistic business-card PNG (has text/edges/shadows)."""
from PIL import Image, ImageDraw, ImageFont
import base64, io, os

def make_card_png() -> bytes:
    W, H = 900, 520
    img = Image.new("RGB", (W, H), (245, 240, 230))
    d = ImageDraw.Draw(img)
    # Border + accent bar (edges)
    d.rectangle([0, 0, W-1, H-1], outline=(30, 30, 30), width=3)
    d.rectangle([0, 0, W, 70], fill=(24, 40, 72))
    d.rectangle([0, H-40, W, H], fill=(200, 170, 90))
    # Subtle shadow line
    d.line([(40, 460), (W-40, 460)], fill=(180, 170, 150), width=2)

    def load(size):
        for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
            if os.path.exists(p):
                try: return ImageFont.truetype(p, size)
                except Exception: pass
        return ImageFont.load_default()

    fb = load(46); fm = load(28); fs = load(24)
    d.text((40, 15), "ARIADNI GROUP", fill=(255, 255, 255), font=fm)
    d.text((40, 110), "Feras Askar", fill=(20, 20, 20), font=fb)
    d.text((40, 175), "Chief Executive Officer", fill=(60, 60, 60), font=fm)
    d.text((40, 250), "Ariadni Holdings LLC", fill=(30, 30, 30), font=fm)
    d.text((40, 310), "Email:  feras@ariadni.ae", fill=(30, 30, 30), font=fs)
    d.text((40, 350), "Phone:  +971 50 123 4567", fill=(30, 30, 30), font=fs)
    d.text((40, 390), "Web:    www.ariadni.ae", fill=(30, 30, 30), font=fs)
    d.text((40, 425), "Dubai, United Arab Emirates", fill=(80, 80, 80), font=fs)

    buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()

def make_card_b64() -> str:
    return base64.b64encode(make_card_png()).decode("ascii")

if __name__ == "__main__":
    out = "/app/test_reports/sample_card.png"
    with open(out, "wb") as f:
        f.write(make_card_png())
    print("wrote", out)
