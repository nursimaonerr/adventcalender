# Kutu Dizilim Doğrulama — Çalışma Raporu

## 1. Problem Analizi

İki ürün modeli arasındaki farklar: Body Attack kare, düzensiz "tuğla"
dizilim; More dikdörtgen, farklı en/boy oranı ve kutu boyutları. İkisi
geometrik olarak hiç benzemiyor. Bu yüzden sistem hiçbir sabit
grid/koordinat varsayımı içermemeli; her model için kutu konumları dışarıdan
(bir şablon dosyasından) okunmalı. Kod tek satır değişmeden yeni bir ürün
eklenebilmeli — tasarımın temel kısıtı bu oldu.

Kutu numaraları ne kadar güvenilir? More modelinde numaralar küçük, düşük
kontrastlı ve fon deseniyle karışıyor, bazı durumlarda okunaksız. Bu yüzden
"numarayı OCR ile oku ve karşılaştır" tek başına yeterli bir strateji değil;
sistemin numaraya hiç bakmadan, sadece basılı görselin kendisini
karşılaştırarak da karar verebilmesi gerekiyor. Geliştirdiğimiz sistem
bilinçli olarak OCR kullanmıyor — her kutunun içeriğini doğrudan referansla
görüntü olarak karşılaştırıyor. Numara, sadece kalibrasyon aşamasında insan
tarafından okunan bir etiket; algoritmanın kendisi numarayı görmek zorunda
değil.

Desen sürekliliği ikinci bir kanıt: yanlış yerleştirilmiş bir kutu genellikle
arka plandaki büyük deseni böler. Yöntemimiz bunu dolaylı olarak zaten
kullanıyor — bir kutunun içeriği referanstaki kendi konumuyla
karşılaştırıldığında düşük skor alıyorsa, bu "buradaki desen artık
referanstakiyle örtüşmüyor" demek; desen sürekliliği kontrolü, kutu-bazlı
karşılaştırmanın doğal bir sonucu.

Zorlaştıran koşullar: aydınlatma/gölge farkı, kameranın hafif kayması veya
açısı, kutuların yükseklik farkı, perspektif. Bunların hepsi test
fotoğraflarında gözlemlendi.

Hangi hata daha kritik? Hatalı bir paketi onaylamak, doğru bir paketi
reddetmekten çok daha maliyetli — biri doğrudan müşteriye kalite problemi
olarak gider, diğeri operatörün paketi elle tekrar kontrol etmesine yol açar.
Bu yüzden varsayılan hassasiyet eşiği temkinli (yüksek) seçildi, şüpheli
durumlarda sistem NOK'a yatkın; hizalama başarısız olursa sonuç asla OK
değil, "kontrol edilemedi" olarak işaretlenir.

Bir kutunun doğru konumda ve doğru yönde olduğunu söylemek için ölçülmesi
gereken şey: o konumdaki basılı içeriğin, referanstaki aynı konumun
içeriğiyle olan piksel-düzeyi benzerliği — döndürülmüş haller de dahil. Bu
benzerlik yeterince yüksekse doğru; değilse, aynı içerik başka bir konumda
yeterince yüksek benzerlik veriyorsa yer değişmiş; hiçbir yerde vermiyorsa
tanınmayan/yanlış yüz.

## 2. Yöntem ve Gerekçesi

Seçilen yöntem: klasik görüntü işleme (OpenCV) — öznitelik tabanlı hizalama
+ şablon/korelasyon karşılaştırması.

Adımlar:
1. Hizalama: ORB özellik noktaları + Hamming mesafeli eşleştirme (oran
   testiyle) + RANSAC homografi. Kameranın tam sabit olmadığı gerçek
   fotoğraflarda test edildi, hafif açı/kayma sorunsuz toleransla
   hizalanıyor.
2. Kutu bazlı karşılaştırma: şablondaki her kutu için, hizalanmış test
   görüntüsünden aynı bölge kesilir; histogram eşitleme ile aydınlatma farkı
   normalize edilir; referans kutuyla ve (olası yer değişimini yakalamak
   için) şablondaki tüm diğer kutularla, dört rotasyonda, normalize çapraz
   korelasyon ile karşılaştırılır. Bu çapraz karşılaştırma, doğru/rotasyon
   hatası/yer değişimi/tanınmayan içerik durumlarının hepsini tek işlemle
   ayırt etmeyi sağlıyor.
3. Karar: en yüksek benzerlik skoru eşik değerinin altındaysa kutu hatalı
   sayılır; üstündeyse ve en iyi eşleşme kendi konumundaysa OK, döndürülmüş
   haldeyse ROTATED, başka bir kutunun konumundaysa SWAPPED.
4. Görselleştirme: ters homografi ile kutu köşeleri orijinal fotoğraf
   koordinatına geri taşınır, hatalı kutular kırmızı çerçeve ile
   işaretlenir.

## 3. Denenen ve Vazgeçilen Yaklaşımlar

Kutu sınırlarını otomatik (tıklama olmadan) çıkarmak için üç farklı yöntem
denendi; üçü de bu ürünler için güvenilmez bulundu ve terk edildi:

1. Canny kenar + bağlı bileşen analizi: kutu dikişleri kadar güçlü kenarlar
   illüstrasyonun kendisinden de geliyor, bu yüzden her kutu kendi içinde
   onlarca sahte "bileşene" bölünüyor.
   (bkz. `rapor_gorseller/1_canny_kenar_haritasi.png`)
2. Hough doğru tespiti ile dikiş çizgisi bulma: gerçek kutu dikişleri tespit
   edilebiliyor, ama düzensiz ("tuğla") dizilim yüzünden dikişler görüntünün
   tamamını baştan sona kat etmiyor; boşluklu doğru parçaları kapalı
   bölgeler oluşturmuyor, bileşenler birbirine karışıyor.
   (bkz. `rapor_gorseller/2_hough_cizgi_tespiti.png`)
3. Kutu numarasının konumundan Voronoi bölütleme: kutular çok farklı boyut
   ve en/boy oranına sahip olduğu için üretilen bölgeler gerçek kutu
   sınırlarıyla örtüşmedi, bazı hücreler birden fazla gerçek kutuyu çapraz
   kesiyor. (bkz. `rapor_gorseller/3_voronoi_basarisiz.png`)

Sonuç: bu düzensiz dizilim için güvenilir otomatik segmentasyon, bu görevin
kapsamını aşan ayrı bir araştırma konusu. Bunun yerine yarı-otomatik bir
tasarıma karar verildi: bir mühendis, yeni bir ürün modeli geldiğinde
`kalibrasyon.py` aracıyla kutuları fare ile bir kez işaretler; bu, üretim
hattında nadiren olan bir olay (yeni ürün lansmanı) olduğu için
Uygulamanın kendisi bu şablonu okur, hiçbir manuel işlem gerektirmez. İki ürün için
(`bodyattack`, `more`) şablonlar bu şekilde elle çıkarılıp `templates/`
altına kaydedildi; Bölüm 4 ve 5'teki sonuçlar bu gerçek şablonlarla, gerçek
fotoğraflar üzerinde alınmıştır.


## 4. Doğruluk Özeti

Sonuçlar, kod içindeki bir varsayım değil, `templates/bodyattack` ve
`templates/more` altında elle kalibre edilmiş gerçek şablonlarla, gerçek
fotoğraflar üzerinde alınmıştır. Zemin gerçeği olarak iki kaynak kullanıldı:
Body Attack klasöründeki fotoğrafların hepsinin bilinen şekilde doğru
dizilim olması, ve More/v1 klasöründeki dosya adlarının hangi kutuların
hatalı olduğunu açıkça belirtmesi (`swap_11&22`, `swap_14&8` gibi).

Gerçek hata tespiti: `swap_11&22` olarak etiketlenen fotoğraflarda sistem
tam olarak 11 ve 22 numaralı kutuları SWAPPED olarak işaretledi — dosya
adındaki etiketle birebir örtüşüyor. (bkz.
`rapor_gorseller/4_gercek_swap_tespiti.png`)

`swap_14&8` etiketli fotoğraflarda 8 ve 14 numaralı kutular da hatalı
işaretlendi; ancak bu fotoğraflarda aynı anda kamera açısı da değiştiği için
sistem fazladan kutuları da hatalı işaretledi.

Gerçek yanlış pozitif — Body Attack: gerçekten doğru dizilmiş fotoğrafların
çoğunda kutu 3 (ve çoğunlukla kutu 23) tekrar eden şekilde hatalı
işaretlendi. (bkz. `rapor_gorseller/5_gercek_yanlis_pozitif.png`) Nedeni
araştırıldı: bu iki kutu, kalendarın en sağ kenarındaki dar, neredeyse
tamamen düz siyah/koyu gri renkte kutular. Ayırt edici deseni neredeyse hiç
olmayan, kenar bölgesindeki koyu bir yüzey, fotoğraftan fotoğrafa değişen
pozlama/gürültüye karşı hassas kalıyor. Bu, klasik korelasyon tabanlı
yöntemlerin bilinen bir zaafı.

Özet: gerçek bir hatayı (yer değiştirme) sistem güvenilir şekilde
yakalıyor. Buna karşılık düz/az detaylı kutularda gerçek bir hata yokken
bile NOK üretebiliyor — yani şu anki haliyle false-reject eğilimi,
false-accept eğiliminden belirgin şekilde yüksek. Bölüm 1'deki gerekçeyle
(false-accept'in false-reject'ten çok daha maliyetli olduğu) bu kabul
edilebilir bir yön hatası, ama üretimde kutu 3 ve 23 gibi kırılgan bölgelerin
yeniden kalibre edilmesi ya da eşiğin bu kutular için ayrı ayarlanması
gerekir.

## 5. Sistemin Sınırları

- Düz/az detaylı yüzeyler false-reject üretiyor: ayırt edici deseni az olan,
  koyu/tekdüze kutularda normalize korelasyon skoru fotoğraftan fotoğrafa
  geniş bir aralıkta oynayabiliyor, bu da gerçek hata olmadan NOK
  üretebiliyor. Yöntemin en somut, ölçülmüş sınırı bu.
- Kalibrasyon kalitesine bağımlı: kutu sınırları yanlış/gevşek
  işaretlenirse (ör. komşu kutuyu da içine alacak kadar geniş), yanlış
  pozitif/negatif oranı artar. `kalibrasyon.py` bunun için kutunun içine
  doğru bir pay uygular ama kaba hatalara karşı sınırlı koruma sağlar.
- Birden fazla değişken aynı anda değiştiğinde ayırt etme zorlaşıyor: hem
  kutu yer değişimi hem kamera açısı aynı anda değiştiğinde sistem gerçek
  hatayı yakalıyor ama fazladan kutuyu da hatalı işaretliyor. Tek değişkenli
  hatalarda (sadece swap, sadece rotasyon) sistem daha temiz sonuç veriyor.
- Aşırı bulanık, çok karanlık veya referansla neredeyse hiç örtüşmeyen
  fotoğraflarda hizalama başarısız olur; bu durumda sistem "kontrol
  edilemedi" der (asla sessizce OK vermez) ama otomasyonu kesintiye uğratır
  — fotoğrafı tekrar çekmesi gerekir.
- Kutu içi hasarlar (buruşma, leke) desen benzerliğini düşürüp yanlış yere
  NOK üretebilir; sistem "kutu yanlış yerde" ile "kutu hasarlı" ayrımını
  yapmaz, ikisini de aynı düşük skor olarak görür.
- Aynı görünen ama farklı kutular (ör. günlük sayı dışında tamamen
  simetrik/tekrarlayan bir baskı) teorik olarak ayırt edilemeyebilir — bu,
  yöntemin doğası gereği bir sınır, tasarım hatası değil.

## 6. Kullanım Notu

Bkz. `README.md` — kurulum, `kalibrasyon.py` ile yeni model tanımlama, ve
`streamlit run arayuz.py` ile operatör arayüzünü başlatma adımları.
