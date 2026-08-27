# Süreç Raporu — Kutu Dizilim Doğrulama Projesi

Bu metni, RAPOR.md'deki resmi bulguların dışında, projeyi geliştirirken
izlediğim yolu, hangi araçları neden seçtiğimi, nerelerde takıldığımı ve
neyi daha iyi yapabileceğimi anlatmak için hazırladım.

## 1. Hangi algoritmaları kullandım

Görevi okuduğumda ilk kararım, derin öğrenme yerine klasik görüntü
işleme ile ilerlemek oldu — çünkü elimde model başına tek bir doğru
referans fotoğraf vardı, bu da bir sinir ağı eğitmek için yeterli değildi.
Kullandığım yapı taşları şunlar:

- ORB (Oriented FAST and Rotated BRIEF) — referans ve test fotoğrafındaki
  belirgin noktaları (köşe/kenar gibi) bulmak için kullandım. Öznitelik
  tabanlı, ölçek ve rotasyona karşı nispeten dayanıklı bir dedektör.
- BFMatcher + oran testi — iki fotoğraftaki ORB noktalarını eşleştirip,
  şüpheli eşleşmeleri elemek için kullandım.
- RANSAC ile homografi (cv2.findHomography) — eşleşen noktalardan, test
  fotoğrafını referansın çerçevesine oturtan bir dönüşüm matrisi
  çıkarıyorum. Kameranın hafif kaymasını/açısını bu adımda tolere ediyorum.
- cv2.warpPerspective — bulduğum dönüşümle test görüntüsünü referans
  koordinat sistemine taşıyorum.
- Normalize Çapraz Korelasyon (NCC, cv2.matchTemplate + TM_CCOEFF_NORMED)
  — her kutunun içeriğini, referanstaki karşılığıyla piksel düzeyinde
  karşılaştırmak için kullandım. Doğrusal parlaklık/kontrast farklarına
  karşı zaten bağışık olduğu için ek bir normalizasyona ihtiyaç duymadım
  (bunu sonradan, yanlışlıkla ekleyip geri çıkardığım bir adımda öğrendim,
  aşağıda anlatıyorum).
- Çapraz benzerlik matrisi — her kutuyu sadece kendi referans konumuyla
  değil, şablondaki diğer tüm kutularla ve 4 rotasyonla (0/90/180/270°)
  karşılaştırıyorum. Tek bir mekanizmayla hem "doğru yerde mi", hem
  "döndürülmüş mü", hem "başka bir kutuyla yer mi değiştirmiş"
  sorularının cevabını aynı anda alabiliyorum.
- Yerel arama penceresi — sürecin sonlarına doğru eklediğim bir adım;
  aşağıda 2. bölümde ayrıntısıyla anlatıyorum.
- Streamlit — operatör arayüzünü Python'dan çıkmadan, ayrı bir
  web/arayüz dili öğrenmeden kurmamı sağladı.

Bilinçli olarak kullanmadığım bir şey de var: OCR (rakam okuma). Görev
tanımı zaten More modelinde rakamların bazen okunaksız olduğunu
vurguluyordu; ben de sistemi tamamen görsel desen karşılaştırmasına
dayandırdım, rakamı hiç görmek zorunda bırakmadım.

## 2. Süreç nasıl ilerledi

1. Önce PDF'i okuyup problemi anladım: iki farklı ürün modeli, sabit bir
   grid varsayımı kuramayacağım düzensiz kutu dizilimleri, ve rakamların
   her zaman güvenilir olmayacağı bir senaryo.
2. Kutu sınırlarını otomatik çıkarmayı denedim — sırasıyla Canny kenar
   + bağlı bileşen analizi, Hough doğru tespiti, ve kutu numaralarının
   konumundan Voronoi bölütleme. Üçü de bu düzensiz dizilim için
   güvenilmez çıktı (kanıtlarıyla RAPOR.md'de var). Bunun üzerine
   yarı-otomatik bir tasarıma karar verdim: kalibrasyon.py ile bir
   mühendisin ürün başına bir kez, fare ile 24 kutuyu işaretlemesi.
3. Çekirdek motoru (denetim/cekirdek.py) yazdım, önce kontrollü sentetik
   verilerle doğruluğunu kanıtladım.
4. Gerçek fotoğraflarla kalibrasyon yapıp gerçek veri üzerinde test
   etmeye başladım — burada işler karmaşıklaştı, detayları 3. bölümde
   anlatıyorum.
5. Operatör arayüzünü (tekli/toplu kontrol, hassasiyet ayarı) kurdum,
   gerçek kullanım senaryolarında test ettim.
6. Son aşamada projeyi GitHub'a yüklemeye hazırlarken kod/dosya
   temizliği yaptım (gereksiz önbellek dosyaları, kayıp .gitignore vb.).

## 3. Takıldığım noktalar

- Otomatik kutu segmentasyonu — en çok zaman harcadığım ve sonunda
  vazgeçtiğim nokta. Üç farklı yöntem denedim, hiçbiri düzensiz "tuğla"
  dizilimi için yeterince güvenilir olmadı. Bunu ayrı bir araştırma
  konusu olarak görüp yarı-otomatik kalibrasyona yöneldim.
- İkiz kutu problemi — More modelinde kutu 15 ve kutu 4'ün deseni
  (sadece ortadaki rakam hariç) neredeyse birebir aynı çıktı. Rakamın
  konumunu merkez alıp ek bir karşılaştırma denedim, ama rakamın kutu
  içindeki konumu kutudan kutuya değiştiği için (bazen kenara yakın,
  bazen merkeze yakın) bu genel bir çözüm olmadı, geri aldım. Bu hâlâ
  çözemediğim, yöntemin doğasından kaynaklanan bir sınır.
- Streamlit önbellek/ortam karmaşası — bir noktada hizalama hatası
  aldım, sebebini saatlerce (önbellek mi, OneDrive senkronizasyonu mu,
  farklı Python ortamı mı diye) araştırdım. Sonunda çok daha basit bir
  şeymiş: arayüzde yanlışlıkla "bodyattack" şablonu seçiliyken "More"
  fotoğraflarını test ediyormuşum. Bu bana, karmaşık bir açıklama
  aramadan önce en basit ihtimali kontrol etmeyi hatırlattı.
- Gerçek veri, sentetik veriden çok daha zorlu çıktı — sentetik
  testlerde yüksek doğruluk alıyordum, ama gerçek fotoğraflarda ilk
  denemede kutu başına ciddi yanlış pozitif oranları gördüm. Sentetik
  test algoritmanın mantığını doğrulamaya yaradı, ama gerçek dünyanın
  (farklı gün/oturumda çekim, kamera açısı, kutu derinliği) getirdiği
  zorlukları göstermedi.

## 4. Geliştirilebilecek alanlar

- Rakamı ek kanıt olarak kullanma — ikiz kutu sorununu tam çözebilmek
  için, sadece belirsiz durumlarda devreye giren hafif bir OCR katmanı
  eklenebilir (rakamın konumu da kalibrasyon sırasında ayrıca
  işaretlenerek).
- Lens/perspektif düzeltmesi — kamera kalibrasyonu eklenirse bu
  istikrarsızlık azalabilir.
- Kutu bazlı eşik değeri — veri modelinde bu alanı zaten ekledim
  (BoxDef.threshold), ama şu an sadece elle template.json düzenlenerek
  kullanılabiliyor; kalibrasyon aracına veya arayüze taşınıp kullanıcı
  dostu hale getirilebilir.
- Kalibrasyon kalite kontrolü — kalibrasyon.py şu an çizilen kutunun ne
  kadar ayırt edici, yeterli dokuya sahip olduğunu operatöre söylemiyor.
  Kutu 3/23, 4/15 gibi kırılgan bölgeleri kalibrasyon sırasında otomatik
  uyarabilecek bir kontrol eklenebilir.
- Daha fazla gerçek veriyle eşik ayarı — şu an tek bir genel eşik
  değeriyle çalışıyorum; daha büyük bir gerçek veri setiyle eşiği
  istatistiksel olarak (ör. ROC eğrisiyle) optimize etmek mümkün.

## 5. Bu süreçte düzelttiğim hatalar

Kalibrasyonu tekrarladıktan sonra gerçek verilerle test ederken
karşılaştığım ve çözdüğüm somut sorunlar:

- Kontrast eşitlemeyi (CLAHE + hafif bulanıklaştırma) kaldırdım. Bunu
  daha önce, düz/az detaylı kutulardaki gürültüyü azaltmak amacıyla
  eklemiştim. Ama gerçek verilerle ölçtüğümde, bazı ince detaylı
  kutularda (ör. kutu 18) skoru gereksiz yere düşürdüğünü gördüm. Dört
  farklı yöntemi (ham, equalizeHist, CLAHE+blur, sadece CLAHE) gerçek
  fotoğraflar üzerinde karşılaştırdım; hiçbir işlem yapmamak en iyi
  sonucu verdi. Kaldırdım.
- "Kutu 8 sürekli dönük çıkıyor" diye bir bug sandığım şeyi araştırdım,
  bug değilmiş. v2 fotoğraf setindeki her karede aynı kutu yüksek
  güvenle döndürülmüş işaretleniyordu. Yamaları büyütüp görsel olarak
  karşılaştırdığımda, o kutunun gerçekten fiziksel olarak ters basılı/
  yerleştirilmiş olduğunu gördüm; sistem hatalı değil, gerçek bir kusuru
  daha önce yakalayamadığı yerde artık doğru yakalıyordu.
- kalibrasyon.py'de u (geri al) tuşunu düzelttim. Bir kutu çizip
  numarasını henüz girmeden u'ya basıldığında hiçbir şey olmuyordu,
  çünkü tuş sadece zaten numaralandırılmış kutuları geri alıyordu.
  Artık numara bekleyen (henüz onaylanmamış) kutuyu da iptal edebiliyor.
- Kaybolan .gitignore dosyasını yeniden oluşturdum ve GitHub'a
  yüklemeden önce __pycache__ gibi gereksiz dosyaları temizledim.
