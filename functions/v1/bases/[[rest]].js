// Bases VOD (fontes Xtream) servidas da nuvem para o Saimo TV.
// Assim as credenciais não precisam ficar dentro do IPK — podem ser
// trocadas/revogadas sem gerar pacote novo.
//
// GET  /v1/bases          → { bases: { "0": "http://...", ... } }
// POST /v1/bases/definir  { segredo, bases }   (segredo = env SEGREDO_BASES)
//
// O segredo vive em variável de ambiente do Cloudflare Pages
// (nx-conexao → Settings → Environment variables), nunca no git.

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

function chave() {
  return new Request("https://bases.nx-conexao/LIST");
}

async function gravar(obj) {
  await caches.default.put(
    chave(),
    new Response(JSON.stringify(obj), {
      headers: {
        "content-type": "application/json",
        "Cache-Control": "max-age=86400", // 24 h; renovado a cada definir
      },
    })
  );
}

async function ler() {
  const hit = await caches.default.match(chave());
  if (!hit) return null;
  try {
    return await hit.json();
  } catch (e) {
    return null;
  }
}

function basesValidas(b) {
  if (!b || typeof b !== "object" || Array.isArray(b)) return false;
  let n = 0;
  for (const k in b) {
    if (!Object.prototype.hasOwnProperty.call(b, k)) continue;
    const v = String(b[k] || "");
    if (v && /^https?:\/\/.{4,300}$/i.test(v)) n++;
    else if (v) return false;
  }
  return n > 0;
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
    if (!acao && request.method === "GET") {
      const item = await ler();
      if (!item) return json({ error: "bases ainda não definidas" }, 404);
      // TTL deslizante: cada consulta da TV renova os 24 h — as bases só
      // expiram se NENHUM aparelho pedir por um dia inteiro.
      await gravar(item);
      return json(item);
    }

    if (acao === "definir" && request.method === "POST") {
      const segredo = (context.env && context.env.SEGREDO_BASES) || "";
      if (!segredo) return json({ error: "defina a env SEGREDO_BASES no Cloudflare Pages" }, 503);
      let corpo = {};
      try {
        corpo = await request.json();
      } catch (e) {
        return json({ error: "json" }, 400);
      }
      if (String(corpo.segredo || "") !== segredo) return json({ error: "segredo inválido" }, 403);
      if (!basesValidas(corpo.bases)) return json({ error: "bases inválidas (objeto { id: url })" }, 400);
      await gravar({ bases: corpo.bases, atualizado: new Date().toISOString() });
      let n = 0;
      for (const k in corpo.bases) if (corpo.bases[k]) n++;
      return json({ ok: true, fontes: n });
    }
  } catch (e) {
    return json({ error: String(e && e.message ? e.message : e) }, 500);
  }

  return json({ error: "método" }, 405);
}
