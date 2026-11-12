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
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
UA = "Mozilla/5.0 (WebOS; SaimoTV) AppleWebKit/537.36"
CATALOGO = "https://canais-saimo.pages.dev/catalogo.txt"
EPG_URLS = [
    "https://iptv-epg.org/files/epg-br.xml",
    "https://www.open-epg.com/files/brazil3.xml",
]
MAX_PROG = 14
MAX_DESC = 120
STOP = {"tv", "canal", "rede", "br", "the", "channel"}
UFS = {"sp", "rj", "mg", "df", "es", "go", "rs", "pr", "ba", "pe", "ce", "am", "pa"}
PREF = {
    "globo": ("globo sp", "tv globo sao paulo", "globo sao paulo", "rede globo"),
    "band": ("band", "band sp", "band brasil"),
    "sbt": ("sbt", "sbt sp", "sbt brasil"),
    "record": ("recordtv", "recordtv sp", "record br"),
    "cnn": ("cnn brasil",),
    "sony": ("sony", "sony channel"),
    "warner": ("warner", "warner channel"),
    "universal": ("universal", "universal tv", "universal channel"),
    "nickelodeon": ("nick",),
    "nicktoons": ("nick jr",),
    "agro mais": ("agromais", "agromais br"),
    "agro": ("agromais", "agromais br"),
}


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
    s = re.sub(r"\b(fhd|uhd|4k|8k|full hd|hd|sd|hevc|h265|h264|backup|option|feed)\b", " ", s)
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
        "hbo 2": "hbo2",
        "hbo mais": "hbo plus",
        "band sports": "bandsports",
        "band sports hd": "bandsports",
        "sport tv": "sportv",
        "sport tv 2": "sportv 2",
        "sport tv 3": "sportv 3",
        "discovery id": "investigacao discovery",
        "investigation discovery": "investigacao discovery",
        "nickelodeon": "nick",
        "nicktoons brasil": "nick jr",
        "nicktoons": "nick jr",
        "nickonline": "nick",
        "agro mais": "agromais",
        "canal agro": "agromais",
        "agro": "agromais",
        "record sp": "recordtv sp",
        "record rj": "record tv rj",
        "record go": "record tv goias",
    }
    return aliases.get(s, s)


def compact(s: str) -> str:
    t = (s or "").replace(" ", "")
    if t.endswith("br") and len(t) > 4:
        t = t[:-2]
    return t


def tokens_flex(s: str):
    out = []
    for t in (s or "").split():
        if t in STOP:
            continue
        if len(t) > 4 and t.endswith("tv"):
            t = t[:-2]
        out.append(t)
    return out


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


def escolher_xml_key(key: str, xml_keys) -> str | None:
    if not key:
        return None
    if key in xml_keys:
        return key
    ck = compact(key)
    for k in xml_keys:
        if compact(k) == ck:
            return k
    for pref in PREF.get(key, ()):
        if pref in xml_keys:
            return pref
        pk = compact(pref)
        for k in xml_keys:
            if compact(k) == pk:
                return k
    prefix = [k for k in xml_keys if k.startswith(key + " ")]
    if prefix:
        prefix.sort(key=lambda k: (len(k.split()), len(k)))
        return prefix[0]
    shorter = [k for k in xml_keys if key.startswith(k + " ") and len(k) >= 3]
    if shorter:
        shorter.sort(key=lambda k: -len(k))
        return shorter[0]
    ct = tokens_flex(key)
    iguais = [k for k in xml_keys if tokens_flex(k) == ct]
    if iguais:
        iguais.sort(key=len)
        return iguais[0]
    toks = [t for t in key.split() if t not in STOP]
    if not toks:
        return None
    scored = []
    for k in xml_keys:
        kt = tokens_flex(k)
        kset = set(kt)
        if ct and all(t in kset for t in ct):
            scored.append((0, len(kt), k))
            continue
        if len(ct) >= 2 and ct[-1] in UFS and ct[:-1] == kt:
            scored.append((1, len(kt), k))
            continue
        old = set(k.split())
        if all(t in old for t in toks):
            scored.append((2, len(k.split()) - len(toks), k))
    if scored:
        scored.sort()
        return scored[0][2]
    return None


def parse_xmltv(text: str):
    id_meta = {}
    for m in re.finditer(r'<channel id="([^"]+)">([\s\S]*?)</channel>', text):
        cid, body = m.group(1), m.group(2)
        dn = re.search(r"<display-name[^>]*>([^<]+)</display-name>", body)
        if not dn:
            continue
        raw = decode_ent(dn.group(1)).strip()
        key = norm_canal(raw)
        if key:
            id_meta[cid] = (key, raw)
    return id_meta


def programas_da_janela(text: str, id_meta, frm: int, to: int, dest: dict, nomes: dict):
    for m in re.finditer(r'<programme\s+([^>]+)>([\s\S]*?)</programme>', text):
        attrs, body = m.group(1), m.group(2)
        ch = re.search(r'channel="([^"]+)"', attrs)
        st = re.search(r'start="([^"]+)"', attrs)
        sp = re.search(r'stop="([^"]+)"', attrs)
        if not (ch and st and sp):
            continue
        meta = id_meta.get(ch.group(1))
        if not meta:
            continue
        key, raw = meta
        start = xmltv_date(st.group(1))
        stop = xmltv_date(sp.group(1))
        if not start or not stop or stop <= frm or start >= to:
            continue
        tm = re.search(r"<title[^>]*>([^<]+)</title>", body)
        if not tm:
            continue
        desc = re.search(r"<desc[^>]*>([^<]+)</desc>", body)
        d = decode_ent(desc.group(1) if desc else "").strip()
        if len(d) > MAX_DESC:
            d = d[: MAX_DESC - 3] + "…"
        lista = dest.setdefault(key, [])
        if len(lista) >= MAX_PROG:
            continue
        title = decode_ent(tm.group(1)).strip()
        if any(p["start"] == start and p["title"] == title for p in lista):
            continue
        lista.append({"title": title, "desc": d, "start": start, "stop": stop})
        nomes.setdefault(key, raw)


def gerar():
    nomes_cat = nomes_catalogo()

    agora = int(time.time() * 1000)
    frm, to = agora - 3600_000, agora + 6 * 3600_000
    progs = {}
    xml_nomes = {}
    algum = False
    for url in EPG_URLS:
        try:
            print("baixando", url)
            xml = baixar_bytes(url)
        except Exception as e:
            print("falhou", url, e)
            continue
        if b"<programme" not in xml:
            print("sem programme", url)
            continue
        algum = True
        text = xml.decode("utf-8", errors="replace")
        programas_da_janela(text, parse_xmltv(text), frm, to, progs, xml_nomes)
    if not algum or not progs:
        raise SystemExit("EPG remoto indisponível")

    xml_keys = list(progs.keys())
    canais = {}

    def colocar(rotulo: str, key: str):
        lista = progs.get(key)
        if not rotulo or not lista:
            return
        prev = canais.get(rotulo)
        if not prev or len(lista) > len(prev):
            canais[rotulo] = lista

    usados = set()
    for nome in nomes_cat:
        xml_key = escolher_xml_key(norm_canal(nome), xml_keys)
        if not xml_key:
            continue
        usados.add(xml_key)
        colocar(nome, xml_key)
        xml_nome = xml_nomes.get(xml_key)
        if xml_nome and xml_nome != nome:
            colocar(xml_nome, xml_key)

    for xml_key, xml_nome in xml_nomes.items():
        if xml_key in usados:
            continue
        if xml_key not in progs:
            continue
        rotulo = xml_nome or xml_key
        if rotulo not in canais:
            colocar(rotulo, xml_key)

    for lista in canais.values():
        lista.sort(key=lambda p: p["start"])

    saida = {"updated": agora, "janelaHoras": 6, "channels": canais}
    dest = RAIZ / "epg.json"
    dest.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(
        f"epg.json: {len(canais)} nomes, {len(usados)} do catálogo, "
        f"{sum(len(v) for v in canais.values())} programas, {dest.stat().st_size} bytes"
    )


if __name__ == "__main__":
    gerar()
