# Kutu Dizilim Doğrulama Sistemi (OpenCV)

Adventskalender kutularının doğru konumda ve doğru yönde dizilip
dizilmediğini fotoğraftan otomatik kontrol eden sistem. Detaylı problem
analizi, yöntem gerekçesi, denenen/vazgeçilen yaklaşımlar ve doğruluk
sonuçları için RAPOR.md dosyasına bakın.

## Hızlı Başlangıç 

```bash
git clone <bu-deponun-linki>
cd <depo-adı>/system
pip install -r requirements.txt
streamlit run arayuz.py
```

## 1) Yeni bir ürün modeli tanımlama (kalibrasyon — bir kere yapılır)

```bash
python kalibrasyon.py --image "referans_foto.jpg" --model bodyattack
```

- Referans, ürünün doğru dizilmiş fotoğrafı olmalı.
- Fare ile her kutunun etrafına dikdörtgen çizin, ardından klavyeden gün
  numarasını yazıp Enter'a basıp 24 kutunun tamamı için tekrarladım 
- `u` : son kutuyu geri al · `s` : kaydet ve çık · `ESC` : kaydetmeden çık.
- Şablon `templates/<model_adı>/` klasörüne kaydedilir 

- Yeni bir üçüncü model eklemek isterseniz yukarıdaki komutu kendi referans
  fotoğrafınızla ve yeni bir `--model` adıyla çalıştırmanız yeterli.

## 2) Operatör arayüzünü başlatma

```bash
streamlit run arayuz.py
```

Tarayıcıda açılan sayfada:
- Soldan ürün modelini seçin.
- Tekli Kontrol sekmesinde bir fotoğraf yükleyin ya da kamerayla çekin →
  büyük yeşil OK / kırmızı NOK sonucu ve hatalı kutuların kırmızı
  çerçeveyle işaretlendiği görüntüyü görürsünüz.
- Toplu Kontrol sekmesinde bir klasör yolu girip "işle" deyin → tüm
  görüntüler işlenir, özet tablo + CSV rapor + hatalı görüntülerin
  küçük resimleri gösterilir.
- Hassasiyet kaydırıcısı sol panel ne işe yaradığı açıklamalarıyla
  birlikte gösterilir; operatörün günlük kullanımda bu ayarla uğraşması
  gerekmez, varsayılan değer kullanıcı tarafından belirlenir.

## Proje Yapısı

```
system/
  denetim/cekirdek.py    # OpenCV cekirdegi: hizalama, kutu karsilastirma, karar mantigi
  kalibrasyon.py           # fare ile referans sablon olusturma araci
  arayuz.py                 # Streamlit operator arayuzu (tekli + toplu kontrol)
  templates/                 # kalibre edilmis urun sablonlari (bodyattack, more)
  rapor_gorseller/           # RAPOR.md icin kanit gorselleri
  referans_foto.JPG,         # kalibrasyon.py'ye girdi olarak verilen orijinal
  referans2.JPG              #   referans fotograflari (arsiv amacli)
  RAPOR.md                    # problem analizi, yontem gerekcesi, sonuclar, sinirlar
```
