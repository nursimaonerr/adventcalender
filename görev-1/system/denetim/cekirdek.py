# Kutu dizilim kontrolu icin cekirdek mantik.
#
# Referans goruntudeki kutu konumlari bir sablonda (bkz. kalibrasyon.py) tutulur.
# Kontrol edilecek goruntu once ORB + RANSAC homografi ile referans cercevesine
# hizalanir, sonra her kutu bolgesi referanstaki tum kutularla (0/90/180/270
# donusumde) karsilastirilir. Boylece kutunun kendi yerinde mi, donuk mu, baska
# bir kutuyla yer mi degistirmis, yoksa hic taninmiyor mu oldugu belirlenir.
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

import numpy as np
import cv2

ROTATIONS = (0, 90, 180, 270)
PATCH_SIZE = 96          # capraz karsilastirma icin standart yama boyutu
DEFAULT_MARGIN = 0.14    # kutu kenarlarindan icine dogru pay(dikis/golge etkisini azaltir
MIN_GOOD_MATCHES = 12    # hizalama icin gereken en az iyi ozellik eslesmesi


# --------------------------------------------------------------------------- #
# Windows'ta Turkce/unicode yol desteği icin guvenli okuma/yazma
# --------------------------------------------------------------------------- #
def imread_u(path: str) -> Optional[np.ndarray]:
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def imwrite_u(path: str, img: np.ndarray) -> None:
    ext = os.path.splitext(path)[1] or ".png"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise IOError(f"Goruntu kodlanamadi: {path}")
    buf.tofile(path)


# --------------------------------------------------------------------------- #
# Sablon 
# --------------------------------------------------------------------------- #
@dataclass
class BoxDef:
    id: int
    x: int
    y: int
    w: int
    h: int


@dataclass
class Template:
    model_name: str
    ref_image: np.ndarray
    boxes: List[BoxDef] = field(default_factory=list)

    @property
    def size(self) -> Tuple[int, int]:
        h, w = self.ref_image.shape[:2]
        return w, h

    def save(self, folder: str) -> None:
        os.makedirs(folder, exist_ok=True)
        imwrite_u(os.path.join(folder, "ref.png"), self.ref_image)  # referans fotografi kaydet
        meta = {
            "model_name": self.model_name,
            "boxes": [b.__dict__ for b in self.boxes],  # her kutuyu dict'e cevir
        }
        with open(os.path.join(folder, "template.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)  # kutu listesini json olarak yaz

    @classmethod
    def load(cls, folder: str) -> "Template":
        with open(os.path.join(folder, "template.json"), "r", encoding="utf-8") as f:
            meta = json.load(f)  # kutu koordinatlarini oku
        ref_image = imread_u(os.path.join(folder, "ref.png"))  # referans fotografi oku
        boxes = [BoxDef(**b) for b in meta["boxes"]]
        return cls(model_name=meta["model_name"], ref_image=ref_image, boxes=boxes)


def list_templates(templates_root: str) -> List[str]:
    if not os.path.isdir(templates_root):
        return []
    out = []
    for name in sorted(os.listdir(templates_root)):
        folder = os.path.join(templates_root, name)
        if os.path.isfile(os.path.join(folder, "template.json")):
            out.append(name)
    return out


# --------------------------------------------------------------------------- #
# Hizalama 
# --------------------------------------------------------------------------- #
def _gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def align_to_reference(ref_bgr: np.ndarray, test_bgr: np.ndarray):
    """test_bgr goruntusunu ref_bgr cercevesine hizalayan homografiyi doner.
    Basarisiz olursa (None, sebep) doner."""
    ref_gray = _gray(ref_bgr)
    test_gray = _gray(test_bgr)

    orb = cv2.ORB_create(nfeatures=5000)  # her iki goruntude de belirgin noktalari bul
    kp1, des1 = orb.detectAndCompute(ref_gray, None)
    kp2, des2 = orb.detectAndCompute(test_gray, None)
    if des1 is None or des2 is None or len(kp1) < MIN_GOOD_MATCHES or len(kp2) < MIN_GOOD_MATCHES:
        return None, "Görüntüde yeterli özellik noktası bulunamadı (bulanık/çok karanlık olabilir)."

    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = bf.knnMatch(des2, des1, k=2)  # test noktalarini referanstakilerle eslestir
    good = [m for pair in matches if len(pair) == 2 for m, n in [pair] if m.distance < 0.75 * n.distance]  # supheli eslesmeleri ele

    if len(good) < MIN_GOOD_MATCHES:
        return None, f"Yetersiz eşleşme ({len(good)}). Görüntü referans ürünle örtüşmüyor olabilir."

    src = np.float32([kp2[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)  # test goruntusundeki noktalar
    dst = np.float32([kp1[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)  # bunlarin referanstaki karsiligi
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)  # test->referans donusum matrisi
    if H is None:
        return None, "Homografi hesaplanamadı (kamera açısı/perspektif çok farklı)."
    inliers = int(mask.sum()) if mask is not None else 0  # donusume uyan nokta sayisi
    if inliers < MIN_GOOD_MATCHES:
        return None, f"Hizalama güvenilir değil (yalnızca {inliers} tutarlı nokta)."
    return H, f"OK ({inliers}/{len(good)} nokta tutarlı)"


# --------------------------------------------------------------------------- #
# Yama islemleri
# --------------------------------------------------------------------------- #
def _rotate(img: np.ndarray, angle: int) -> np.ndarray:
    if angle == 0:
        return img
    if angle == 90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    if angle == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    raise ValueError(angle)


def _extract_patch(img: np.ndarray, box: BoxDef, margin: float = DEFAULT_MARGIN) -> np.ndarray:
    H, W = img.shape[:2]
    mx, my = int(box.w * margin), int(box.h * margin)  # kenarlardan icine dogru pay
    x0 = max(0, box.x + mx)
    y0 = max(0, box.y + my)
    x1 = min(W, box.x + box.w - mx)
    y1 = min(H, box.y + box.h - my)
    if x1 <= x0 or y1 <= y0:  # pay cok buyukse kutuyu kucultmeden kullan
        x0, y0, x1, y1 = box.x, box.y, box.x + box.w, box.y + box.h
    patch = img[y0:y1, x0:x1]  # kutu bolgesini kes
    if patch.size == 0:
        return np.zeros((PATCH_SIZE, PATCH_SIZE), np.uint8)
    gray = _gray(patch)
    gray = cv2.equalizeHist(gray)  # aydınlatma/kontrast farklarına karşı normalize et
    return cv2.resize(gray, (PATCH_SIZE, PATCH_SIZE), interpolation=cv2.INTER_AREA)  # herkes ayni boyutta olsun


def _ncc(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float32)
    b = b.astype(np.float32)
    res = cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED)
    return float(res[0, 0])


# --------------------------------------------------------------------------- #
# Denetim sonucu
# --------------------------------------------------------------------------- #
@dataclass
class BoxResult:
    id: int
    status: str          # OK | ROTATED | SWAPPED | MISMATCH
    score: float
    detail: str
    matched_with: Optional[int] = None
    rotation: int = 0


@dataclass
class InspectionResult:
    ok: bool
    align_message: str
    boxes: List[BoxResult] = field(default_factory=list)
    annotated: Optional[np.ndarray] = None
    error: Optional[str] = None


def inspect(template: Template, test_bgr: np.ndarray, threshold: float = 0.55,
            margin: float = DEFAULT_MARGIN) -> InspectionResult:
    H, msg = align_to_reference(template.ref_image, test_bgr)  # once hizala
    if H is None:
        return InspectionResult(ok=False, align_message=msg, error=msg,
                                 annotated=test_bgr.copy())

    Wt, Ht = template.size
    warped = cv2.warpPerspective(test_bgr, H, (Wt, Ht))  # test goruntusunu referans cercevesine tasi

    boxes = template.boxes
    n = len(boxes)
    ref_patches = [_extract_patch(template.ref_image, b, margin) for b in boxes]  # referanstaki 24 kutu
    test_patches = {r: [_rotate(_extract_patch(warped, b, margin), r) for b in boxes] for r in ROTATIONS}  # test kutulari, her rotasyonda

    # S[i, j, r] = test kutusu i'nin (r derece dondurulmus) referans kutusu j ile benzerligi
    S = np.zeros((n, n, len(ROTATIONS)), dtype=np.float32)
    for ri, r in enumerate(ROTATIONS):
        tp = test_patches[r]
        for i in range(n):
            for j in range(n):
                S[i, j, ri] = _ncc(tp[i], ref_patches[j])

    results: List[BoxResult] = []
    for i, b in enumerate(boxes):
        own_scores = S[i, i, :]  # bu kutunun kendi referans konumuyla benzerligi (4 rotasyonda)
        own_best_ri = int(np.argmax(own_scores))
        own_best = float(own_scores[own_best_ri])
        own_best_rot = ROTATIONS[own_best_ri]

        flat = S[i, :, :]  # bu kutunun TUM referans kutularla benzerligi
        j_star, r_star_idx = np.unravel_index(np.argmax(flat), flat.shape)  # en iyi eslesen kutu/rotasyon
        global_best = float(flat[j_star, r_star_idx])
        j_star = int(j_star)
        r_star = ROTATIONS[int(r_star_idx)]

        if own_best >= threshold and own_best_rot == 0:  # kendi yerinde, dogru yonde
            results.append(BoxResult(b.id, "OK", own_best, "Doğru konum, doğru yön.", None, 0))
        elif own_best >= threshold and own_best_rot != 0:  # kendi yerinde ama donuk
            results.append(BoxResult(
                b.id, "ROTATED", own_best,
                f"Doğru konumda ama {own_best_rot}° döndürülmüş.", None, own_best_rot))
        elif j_star != i and global_best >= threshold:  # baska bir kutunun icerigi burada
            other_id = boxes[j_star].id
            results.append(BoxResult(
                b.id, "SWAPPED", global_best,
                f"Bu konumda kutu {other_id} bulundu (yer değişmiş olabilir).",
                other_id, r_star))
        else:  # hicbir kutuyla yeterince eslesmedi
            results.append(BoxResult(
                b.id, "MISMATCH", global_best,
                "Hiçbir referans kutusuyla yeterince eşleşmedi (yanlış yüz / farklı ürün / okunamıyor).",
                None, 0))

    ok = all(r.status == "OK" for r in results)
    annotated = _annotate(test_bgr, template, H, results)
    return InspectionResult(ok=ok, align_message=msg, boxes=results, annotated=annotated)


def _annotate(test_bgr: np.ndarray, template: Template, H: np.ndarray,
              results: List[BoxResult]) -> np.ndarray:
    vis = test_bgr.copy()
    Hinv = np.linalg.inv(H)  # referans->test yonune ters donusum
    by_id = {b.id: b for b in template.boxes}
    for r in results:
        b = by_id[r.id]
        corners = np.float32([
            [b.x, b.y], [b.x + b.w, b.y], [b.x + b.w, b.y + b.h], [b.x, b.y + b.h]
        ]).reshape(-1, 1, 2)  # kutunun 4 kosesi (referans koordinatinda)
        pts = cv2.perspectiveTransform(corners, Hinv).reshape(-1, 2).astype(int)  # orijinal fotografa tasi
        color = (0, 170, 0) if r.status == "OK" else (0, 0, 255)  # yesil: OK, kirmizi: hatali
        cv2.polylines(vis, [pts], True, color, 4)
        if r.status != "OK":
            label = f"{r.id}:{r.status}"
            org = tuple(pts[0])
            cv2.putText(vis, label, (org[0], max(20, org[1] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(vis, label, (org[0], max(20, org[1] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
    return vis
