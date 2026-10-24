import json
import os
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

WBM_URL = "https://www.wbm.de/wohnungen-berlin/angebote/"
STATE_FILE = Path("gorulen_ilanlar.json")


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
                        baslik = adres.rstrip("/").split("/")[-1]
                        baslik = baslik.replace("-", " ")

                    ilanlar[adres] = {
                        "baslik": baslik,
                        "oda": oda_sayisi,
                        "url": adres,
                    }
                break

    if not ilanlar:
        raise RuntimeError(
            "Uygun ilan bulunamadi. Kontrol gerekli."
        )

    return ilanlar


def telegram_gonder(mesaj):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    cevap = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": mesaj},
        timeout=30,
    )
    cevap.raise_for_status()

    if not cevap.json().get("ok"):
        raise RuntimeError("Telegram mesaji gonderilemedi.")


def main():
    ilanlar = ilanlari_bul()
    print(f"{len(ilanlar)} uygun ilan bulundu.")

    if not STATE_FILE.exists():
        STATE_FILE.write_text(
            json.dumps(
                sorted(ilanlar.keys()),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print("Ilk kontrol: mevcut ilanlar kaydedildi.")
        return

    gorulen = set(
        json.loads(STATE_FILE.read_text(encoding="utf-8"))
    )

    yeni_ilanlar = [
        ilan
        for adres, ilan in ilanlar.items()
        if adres not in gorulen
    ]

    print(f"{len(yeni_ilanlar)} yeni ilan bulundu.")

    for ilan in yeni_ilanlar:
        mesaj = (
            "🏠 YENI WBM ILANI!\n\n"
            f"{ilan['baslik']}\n"
            f"Oda sayisi: {ilan['oda']:g}\n\n"
            f"{ilan['url']}"
        )
        telegram_gonder(mesaj)
        gorulen.add(ilan["url"])

        STATE_FILE.write_text(
            json.dumps(
                sorted(gorulen),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    print("Kontrol tamamlandi.")


if __name__ == "__main__":
    main()
