# Kalibrasyon araci: referans fotograf uzerinde kutulari fare ile isaretleyip
# sablon (template.json + ref.png) olusturur. Urun basina bir kez calistirilir.
#
# Kullanim:  python kalibrasyon.py --image referans_foto.jpg --model bodyattack
# Fare: surukle -> kutu ciz. Sonra klavyeden gun numarasini yazip Enter.
# u: geri al   s: kaydet ve cik   ESC: kaydetmeden cik
import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from denetim.cekirdek import Template, BoxDef, imread_u  # noqa: E402

WIN = "Kalibrasyon - kutu bolgelerini isaretleyin"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="Referans (dogru dizilmis) urun fotografi")
    ap.add_argument("--model", required=True, help="Urun modeli adi (ornek: bodyattack)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "templates"))
    ap.add_argument("--max-width", type=int, default=1400, help="Ekranda gosterilecek maksimum genislik")
    args = ap.parse_args()

    img = imread_u(args.image)  # orijinal boyutta referans fotograf
    if img is None:
        print(f"Görüntü okunamadı: {args.image}")
        sys.exit(1)

    # ekrana buyuk fotograflar sığmayabilir, kucultüp goster
    scale = min(1.0, args.max_width / img.shape[1])
    disp = cv2.resize(img, None, fx=scale, fy=scale) if scale < 1.0 else img.copy()

    boxes = []          # orijinal cözünurlukte BoxDef listesi
    drawing = {"start": None, "cur": None}
    pending_box = {"rect": None}  # cizilmis ama henüz numara girilmemis kutu (orijinal koordinat)

    def to_orig(pt):
        # ekrandaki (kucultlmüs) koordinati orijinal fotograf koordinatina cevir
        return int(pt[0] / scale), int(pt[1] / scale)

    def redraw():
        vis = disp.copy()
        for b in boxes:
            x, y, w, h = int(b.x * scale), int(b.y * scale), int(b.w * scale), int(b.h * scale)
            cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 200, 0), 2)
            cv2.putText(vis, str(b.id), (x + 4, y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        if drawing["start"] and drawing["cur"]:
            cv2.rectangle(vis, drawing["start"], drawing["cur"], (0, 165, 255), 2)
        if pending_box["rect"]:
            x, y, w, h = pending_box["rect"]
            x, y, w, h = int(x * scale), int(y * scale), int(w * scale), int(h * scale)
            cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 165, 255), 2)
            cv2.putText(vis, "numara yaz + ENTER", (x, max(20, y - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
        info = f"Kutu: {len(boxes)}/24   [u]geri al  [s]kaydet  [ESC]iptal"
        cv2.rectangle(vis, (0, 0), (vis.shape[1], 30), (30, 30, 30), -1)
        cv2.putText(vis, info, (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imshow(WIN, vis)

    def on_mouse(event, x, y, flags, userdata):
        if pending_box["rect"] is not None:
            return  # once bekleyen kutuya numara girilmeli
        if event == cv2.EVENT_LBUTTONDOWN:
            # fareye basildi: dikdortgenin baslangic kösesi
            drawing["start"] = (x, y)
            drawing["cur"] = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE and drawing["start"]:
            # fare surukleniyor: gecici dikdortgeni ekranda guncelle
            drawing["cur"] = (x, y)
            redraw()
        elif event == cv2.EVENT_LBUTTONUP and drawing["start"]:
            # fare birakildi: dikdortgen tamamlandi, orijinal koordinata cevir
            x0, y0 = to_orig(drawing["start"])
            x1, y1 = to_orig((x, y))
            x0, x1 = sorted((x0, x1))  # kose siralamasi ters olabilir, duzelt
            y0, y1 = sorted((y0, y1))
            drawing["start"] = None
            drawing["cur"] = None
            if x1 - x0 > 5 and y1 - y0 > 5:  # cok kucuk/yanlissik tiklamalari yok say
                pending_box["rect"] = (x0, y0, x1 - x0, y1 - y0)
            redraw()

    cv2.namedWindow(WIN)
    cv2.setMouseCallback(WIN, on_mouse)
    number_buf = ""
    redraw()

    while True:
        key = cv2.waitKey(20) & 0xFF
        if key == 255:
            continue
        if pending_box["rect"] is not None:
            if key in (13, 10):  # ENTER
                if number_buf.strip().isdigit():
                    bid = int(number_buf.strip())
                    x, y, w, h = pending_box["rect"]
                    boxes.append(BoxDef(id=bid, x=x, y=y, w=w, h=h))
                pending_box["rect"] = None
                number_buf = ""
                redraw()
            elif key in (8, 127):  # backspace
                number_buf = number_buf[:-1]
            elif chr(key).isdigit():
                number_buf += chr(key)
            continue

        if key == 27:  # ESC
            print("İptal edildi, kaydedilmedi.")
            break
        elif key == ord('u'):
            if boxes:
                boxes.pop()
                redraw()
        elif key == ord('s'):
            if len(boxes) == 0:
                print("Hiç kutu işaretlenmedi.")
                continue
            tpl = Template(model_name=args.model, ref_image=img, boxes=boxes)
            folder = os.path.join(args.out, args.model)
            tpl.save(folder)
            print(f"Kaydedildi: {folder}  ({len(boxes)} kutu)")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
