# Hat — canlı haber akışı

Onlarca kaynaktan gelen haberleri tek bir zaman hattında toplayan, **her 60 saniyede kendini yenileyen** tarayıcı tabanlı haber panosu.

🔗 **Canlı site:** https://31madaracollet.github.io/haber-hatti/

---

## Ne yapıyor

- Bölümler: **Akış, Gündem, Dünya, Ekonomi, Teknoloji, Spor, Bilim, Kültür**
- Manşet seçimi: son 6 saatteki haberler arasından görseli olan en taze başlık öne çıkar
- Son 20 dakikada gelen bir haber varsa manşet **kırmızı çizgiyle "Son dakika"** olarak işaretlenir
- Her yenilemede yeni düşen başlıklar **"yeni"** etiketi alır ve yavaşça sönümlenir
- Sol rayda canlı saat, 60 saniyelik geri sayım halkası ve kaynak sağlık çubukları
- Arama, "daha fazla başlık" ile sayfalama, bölümler arası anlık geçiş

### Klavye kısayolları

| Tuş | İşlev |
| --- | --- |
| `/` | Aramaya odaklan |
| `R` | Şimdi yenile |
| `1`–`8` | Bölümler arasında geçiş |
| `Esc` | Aramayı temizle |

---

## Kaynaklar

RSS akışı sunan 45+ kaynak kullanılıyor.

**Türkiye:** NTV, Hürriyet, TRT Haber, Cumhuriyet, Habertürk, Anadolu Ajansı, BBC Türkçe, DW Türkçe, Euronews Türkçe, Bloomberg HT
**Dünya:** BBC World, Al Jazeera, The Guardian, New York Times, DW
**Teknoloji:** TechCrunch, The Verge, Ars Technica, Hacker News
**Diğer:** ESPN, ScienceDaily, Phys.org
**Ayrıca:** Google News'in kendi kaynak havuzundan gelen başlıklar

---

## Nasıl çalışıyor

Tek bir `index.html` dosyası — derleme adımı, sunucu, bağımlılık yok.

Tarayıcılar güvenlik nedeniyle farklı alan adlarındaki RSS akışlarını doğrudan çekemez. Bu yüzden istekler genel CORS proxy'lerinden geçer ve biri yanıt vermezse otomatik olarak sıradakine geçilir:

1. `api.allorigins.win`
2. `corsproxy.io`
3. `api.codetabs.com`

Gelen XML `DOMParser` ile ayrıştırılır (hem RSS 2.0 hem Atom desteklenir), başlıklar normalize edilerek tekrarlar temizlenir ve tarihe göre sıralanır.

> **Not:** Genel proxy'ler ücretsiz ve paylaşımlıdır; yoğun kullanımda geçici olarak sınırlandırılabilirler. Kalıcı/kritik bir kurulum için kendi proxy'nizi (örneğin bir Cloudflare Worker) araya koymanız önerilir.

---

## Yerelde çalıştırma

```bash
git clone https://github.com/31madaracollet/haber-hatti.git
cd haber-hatti
python3 -m http.server 8000
```

Ardından http://localhost:8000 adresini açın.

---

## Kaynak ekleme / çıkarma

`index.html` içindeki `FEEDS` nesnesini düzenleyin:

```js
var FEEDS = {
  gundem: [
    GN(''),                                    // Google News manşetleri
    'https://www.ntv.com.tr/son-dakika.rss',   // doğrudan RSS adresi
    // ...
  ]
};
```

Yeni bir kaynağın görünen adını da `NAMES` nesnesine ekleyin; eklenmezse alan adı gösterilir.

---

## Lisans

Kod MIT lisansı altındadır. Haber başlıkları, özetleri ve görselleri ilgili yayıncılara aittir; bağlantılar doğrudan kaynağa gider.
