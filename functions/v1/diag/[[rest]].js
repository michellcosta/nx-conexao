// Diagnóstico remoto das TVs Saimo TV.
// A TV faz POST /v1/diag/enviar com o buffer do HUD; o desenvolvedor lê em
// GET /v1/diag/{id} (ou pela página /log). Sem KV: caches.default, igual ao parear.

const ABC = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const TTL = 900; // 15 min; cada envio renova

function cors() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "content-type, accept",
  };
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...cors() },
  });
}

function idNovo() {
  let s = "";
  for (let i = 0; i < 6; i++) s += ABC[Math.floor(Math.random() * ABC.length)];
  return s;
}

function chave(id) {
  return new Request("https://diag.nx-conexao/" + String(id || "").toUpperCase());
}

async function gravar(id, obj) {
  await caches.default.put(
    chave(id),
    new Response(JSON.stringify(obj), {
      headers: {
        "content-type": "application/json",
        "Cache-Control": "max-age=" + TTL,
      },
    })
  );
}

async function ler(id) {
  const hit = await caches.default.match(chave(id));
  if (!hit) return null;
  try {
    return await hit.json();
  } catch (e) {
    return null;
  }
}

export async function onRequest(context) {
  const request = context.request;
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: cors() });
  }

  const rest = context.params.rest;
  const segs = Array.isArray(rest) ? rest : rest ? [rest] : [];
  const acao = String(segs[0] || "").toLowerCase();

  try {
    // POST /v1/diag/enviar  { tv, sistema, memoria, linhas[], eventos[] }
    if (acao === "enviar" && request.method === "POST") {
      let corpo = {};
      try {
        corpo = await request.json();
      } catch (e) {
        return json({ error: "json" }, 400);
      }
      let tv = String(corpo.tv || "").toUpperCase();
      if (!/^[A-Z0-9]{4,12}$/.test(tv)) {
        tv = idNovo();
      }
      const linhas = Array.isArray(corpo.linhas) ? corpo.linhas.slice(0, 30) : [];
      const eventos = Array.isArray(corpo.eventos) ? corpo.eventos.slice(0, 40) : [];
      const salvo = {
        tv: tv,
        sistema: String(corpo.sistema || "").slice(0, 120),
        memoria: String(corpo.memoria || "").slice(0, 40),
        versao: String(corpo.versao || "").slice(0, 40),
        linhas: linhas.map((l) => String(l || "").slice(0, 300)),
        eventos: eventos.map((e) => ({
          data: String((e && e.data) || "").slice(0, 30),
          tipo: String((e && e.tipo) || "").slice(0, 60),
          detalhe: String((e && e.detalhe) || "").slice(0, 300),
        })),
        recebido: new Date().toISOString(),
      };
      await gravar(tv, salvo);
      return json({ ok: true, tv: tv, expira: TTL });
    }

    if (!acao) return json({ error: "rota" }, 404);

    // GET /v1/diag/{id} — leitura NÃO apaga (diferente do parear): dá para
    // atualizar a página quantas vezes quiser enquanto a TV segue enviando.
    if (request.method === "GET") {
      const item = await ler(acao);
      if (!item) return json({ error: "nenhum log recente para este ID (a TV está ligada? enviando?)" }, 404);
      return json(item);
    }
  } catch (e) {
    return json({ error: String(e && e.message ? e.message : e) }, 500);
  }

  return json({ error: "método" }, 405);
}
