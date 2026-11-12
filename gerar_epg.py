#!/usr/bin/env python3
"""Gera epg.json magro (6 h) para a TV. Roda no GitHub Action; o Pages publica."""
from __future__ import annotations

import gzip
import io
import json
import re
import time
import unicodedata
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
UA = "Mozilla/5.0 (WebOS; SaimoTV) AppleWebKit/537.36"
CATALOGO = "https://canais-saimo.pages.dev/catalogo.txt"
EPG_URLS = [
    "https://iptv-epg.org/files/epg-br.xml",
    "https://www.open-epg.com/files/brazil3.xml",
]


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return s


def decode_ent(s: str) -> str:
    return (
        (s or "")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&apos;", "'")
    )


def norm_canal(s: str) -> str:
    s = fold(decode_ent(s))
    s = re.sub(r"^(tv|canal|rede|br)\s+", "", s)
    s = re.sub(r"\b(fhd|uhd|4k|8k|full hd|hd|sd|hevc|h265|h264)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+brasil$", "", s)
    aliases = {
        "a e": "ae",
        "globo news": "globonews",
        "globonews": "globonews",
        "cnn": "cnn brasil",
        "band brasil": "band",
        "band sp": "band",
        "premiere fc": "premiere clubes",
        "universal tv": "universal",
        "universal channel": "universal",
        "warner channel": "warner",
        "sony channel": "sony",
        "record tv": "record",
    }
    return aliases.get(s, s)


def pedir_texto(url: str, timeout: int = 90) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read().decode("utf-8", errors="replace")


def baixar_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=90) as res:
        data = res.read()
        if res.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
            try:
                data = gzip.decompress(data)
            except Exception:
                data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
        return data


def xmltv_date(s: str):
    s = (s or "").strip()
    if len(s) < 14:
        return None
    try:
        dt = datetime.strptime(s[:14], "%Y%m%d%H%M%S")
    except ValueError:
        return None
    tz = s[15:] if len(s) > 15 else "-0300"
    m = re.match(r"([+-])(\d{2})(\d{2})", tz.replace(":", ""))
    if m:
        sign = 1 if m.group(1) == "+" else -1
        dt = dt.replace(tzinfo=timezone(sign * timedelta(hours=int(m.group(2)), minutes=int(m.group(3)))))
    else:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=-3)))
    return int(dt.timestamp() * 1000)


def nomes_catalogo():
    nomes = []
    try:
        for line in pedir_texto(CATALOGO, 25).splitlines():
            if line.lower().startswith("canal:"):
                n = line.split(":", 1)[1].strip()
                if n:
                    nomes.append(n)
    except Exception as e:
        print("catalogo remoto falhou", e)
    return nomes


def gerar():
    nomes = nomes_catalogo()
    wanted = {}
    for n in nomes:
        wanted.setdefault(norm_canal(n), n)

    xml = b""
    for url in EPG_URLS:
        try:
            print("baixando", url)
            xml = baixar_bytes(url)
            if b"<programme" in xml:
                break
        except Exception as e:
            print("falhou", url, e)
            xml = b""
    if not xml:
        raise SystemExit("EPG remoto indisponível")

    text = xml.decode("utf-8", errors="replace")
    name_to_ids = {}
    for m in re.finditer(r'<channel id="([^"]+)">([\s\S]*?)</channel>', text):
        cid, body = m.group(1), m.group(2)
        dn = re.search(r"<display-name[^>]*>([^<]+)</display-name>", body)
        if not dn:
            continue
        key = norm_canal(dn.group(1))
        name_to_ids.setdefault(key, []).append(cid)

    xml_to_ours = {}
    if wanted:
        for key, nome in wanted.items():
            ids = name_to_ids.get(key)
            if not ids:
                cands = [k for k in name_to_ids if k.startswith(key + " ") or key.startswith(k + " ")]
                if len(cands) == 1:
                    ids = name_to_ids[cands[0]]
            if ids:
                for i in ids:
                    xml_to_ours[i] = nome
    else:
        for key, ids in name_to_ids.items():
            for i in ids:
                xml_to_ours[i] = key

    agora = int(time.time() * 1000)
    frm, to = agora - 3600_000, agora + 6 * 3600_000
    canais = {}
    for m in re.finditer(r'<programme\s+([^>]+)>([\s\S]*?)</programme>', text):
        attrs, body = m.group(1), m.group(2)
        ch = re.search(r'channel="([^"]+)"', attrs)
        st = re.search(r'start="([^"]+)"', attrs)
        sp = re.search(r'stop="([^"]+)"', attrs)
        if not (ch and st and sp):
            continue
        nosso = xml_to_ours.get(ch.group(1))
        if not nosso:
            continue
        start = xmltv_date(st.group(1))
        stop = xmltv_date(sp.group(1))
        if not start or not stop or stop <= frm or start >= to:
            continue
        tm = re.search(r"<title[^>]*>([^<]+)</title>", body)
        if not tm:
            continue
        desc = re.search(r"<desc[^>]*>([^<]+)</desc>", body)
        d = decode_ent(desc.group(1) if desc else "").strip()
        if len(d) > 120:
            d = d[:117] + "…"
        lista = canais.setdefault(nosso, [])
        if len(lista) >= 14:
            continue
        lista.append({
            "title": decode_ent(tm.group(1)).strip(),
            "desc": d,
            "start": start,
            "stop": stop,
        })

    for lista in canais.values():
        lista.sort(key=lambda p: p["start"])
    saida = {"updated": agora, "janelaHoras": 6, "channels": canais}
    dest = RAIZ / "epg.json"
    dest.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"epg.json: {len(canais)} canais, {sum(len(v) for v in canais.values())} programas, {dest.stat().st_size} bytes")


if __name__ == "__main__":
    gerar()
