# Hat — canlı haber akışı

Onlarca kaynaktan gelen haberleri tek bir zaman hattında toplayan haber panosu.

🔗 **Canlı site:** https://31madaracollet.github.io/haber-hatti/

---

## Ne yapıyor

- Bölümler: **Akış, Gündem, Dünya, Ekonomi, Teknoloji, Spor, Bilim, Kültür**
- Manşet seçimi: son 6 saatteki haberler arasından görseli olan en taze başlık öne çıkar
- Son 20 dakikada gelen bir haber varsa manşet kırmızı çizgiyle **"Son dakika"** olarak işaretlenir
- Yeni düşen başlıklar **"yeni"** etiketi alır ve yavaşça sönümlenir
- Sol rayda canlı saat, 60 saniyelik yenileme sayacı ve kaynak sağlık çubukları
- Arama, "daha fazla başlık" ile sayfalama, bölümler arası anlık geçiş

### Klavye kısayolları

| Tuş | İşlev |
| --- | --- |
| `/` | Aramaya odaklan |
| `R` | Şimdi yenile |
| `1`–`8` | Bölümler arasında geçiş |
| `Esc` | Aramayı temizle |

---

## Mimari

```
GitHub Actions (her 5 dakika)
        │
        │  RSS akışlarını sunucu tarafında çeker
        ▼
  scripts/build_feed.py  ──►  feed.json  ──►  depoya commit
                                                  │
                                                  │ aynı origin
                                                  ▼
                                            index.html
                                     (her 60 saniyede yoklar)
```

**Neden böyle?** Tarayıcılar farklı alan adlarındaki RSS akışlarını doğrudan çekemez (CORS).
İlk sürüm bu yüzden genel CORS proxy'leri kullanıyordu; ancak bu servisler güvenilmez çıktı:

- `corsproxy.io` → `401` (artık API anahtarı istiyor)
- `api.codetabs.com` → `503` (aşırı yüklenmiş)
- `api.allorigins.win` → aralıklı çalışıyor, bazen CORS başlığı olmadan dönüyor

16 akış tek çalışan proxy'ye yüklenince hız sınırına takılıyor ve sayfa boş kalıyordu.
Şimdi akışlar **sunucu tarafında** derleniyor, sayfa kendi origin'inden tek bir JSON okuyor.
CORS engeli tamamen devreden çıktı.

### Tazelik

| Katman | Aralık | Ne yapar |
| --- | --- | --- |
| GitHub Actions | ~5 dk | Tüm kaynakları derleyip `feed.json`'ı güncellemek |
| Sayfa yoklaması | 60 sn | `feed.json`'ı yeniden okumak |
| Canlı katman | 60 sn | Manşet akışını doğrudan çekip listenin başına eklemek |

`feed.json` her zaman birincil kaynak; **canlı katman isteğe bağlıdır ve hata verse bile sayfayı etkilemez.**

> GitHub Actions'ın zamanlanmış işler için izin verdiği en kısa aralık 5 dakikadır.
> Gerçek dakikalık tazelik isteniyorsa araya bir Cloudflare Worker (Cron Trigger, minimum 1 dk) konabilir.

---

## Kaynaklar

RSS akışı sunan 50+ kaynak kullanılıyor.

**Türkiye:** NTV, Hürriyet, TRT Haber, Cumhuriyet, Habertürk, Anadolu Ajansı, BBC Türkçe, DW Türkçe, Euronews Türkçe, Bloomberg HT
**Dünya:** BBC World, Al Jazeera, The Guardian, New York Times, DW
**Teknoloji:** TechCrunch, The Verge, Ars Technica, Hacker News
**Diğer:** ESPN, ScienceDaily, Phys.org
**Ayrıca:** Google News'in kendi kaynak havuzundan gelen başlıklar

---

## Yerelde çalıştırma

```bash
git clone https://github.com/31madaracollet/haber-hatti.git
cd haber-hatti

# veriyi bir kez derle
python3 scripts/build_feed.py

# servis et (feed.json ile aynı origin olması için sunucu şart)
python3 -m http.server 8000
```

Ardından http://localhost:8000 adresini açın.

> `index.html`'i doğrudan `file://` ile açmak çalışmaz; `fetch` aynı origin ister.

---

## Kaynak ekleme / çıkarma

`scripts/build_feed.py` içindeki `SECTIONS` sözlüğünü düzenleyin:

```python
SECTIONS = {
    "gundem": [
        gn(),                                      # Google News manşetleri
        "https://www.ntv.com.tr/son-dakika.rss",   # doğrudan RSS adresi
        # ...
    ],
}
```

Yeni kaynağın görünen adını `NAMES` sözlüğüne ekleyin; eklenmezse alan adı gösterilir.

---

## Lisans

Kod MIT lisansı altındadır. Haber başlıkları, özetleri ve görselleri ilgili yayıncılara aittir;
bağlantılar doğrudan kaynağa gider.
