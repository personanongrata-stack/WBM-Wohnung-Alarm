import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WBM_URL = "https://www.wbm.de/wohnungen-berlin/angebote/"

def ilanlari_bul():
    cevap = requests.get(
        WBM_URL,
        headers={"User-Agent": "WBM-Wohnung-Alarm/1.0"},
        timeout=30,
    )
    cevap.raise_for_status()

    sayfa = BeautifulSoup(cevap.text, "html.parser")
    ilanlar = {}

    for link in sayfa.select('a[href*="/angebote/details/"]'):
        adres = urljoin(WBM_URL, link.get("href", ""))
        if adres in ilanlar:
            continue

        kutu = link
        for _ in range(6):
            if kutu.parent is None:
                break
            kutu = kutu.parent
            metin = kutu.get_text(" ", strip=True)

            oda = re.search(
                r"(\d+(?:[,.]\d+)?)\s*Zimmer\b",
                metin,
                re.IGNORECASE,
            )

            if oda and len(metin) < 1800:
                oda_sayisi = float(
                    oda.group(1).replace(",", ".")
                )

                if oda_sayisi >= 3:
                    baslik = link.get_text(" ", strip=True)
                    if not baslik or len(baslik) < 8:
                        baslik = adres.rsplit("/", 2)[-2]

                    ilanlar[adres] = {
                        "baslik": baslik,
                        "oda": oda_sayisi,
                        "url": adres,
                    }
                break

    if not ilanlar:
        raise RuntimeError(
            "Uygun ilan bulunamadi. Sayfa yapisi kontrol edilmeli."
        )

    return ilanlar


if __name__ == "__main__":
    ilanlar = ilanlari_bul()
    print(f"{len(ilanlar)} uygun ilan bulundu.")

    for ilan in ilanlar.values():
        print(ilan["oda"], "oda:", ilan["url"])
