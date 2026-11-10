// Config remota do Saimo TV: versão mínima e mensagem da home,
// trocáveis sem gerar IPK.
//
// GET  /v1/config          → { versaoMinima, mensagem, aviso, atualizado }
// POST /v1/config/definir  { segredo, versaoMinima, mensagem, aviso }
//                              (segredo = env SEGREDO_CONFIG no Pages)

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
  return new Request("https://config.nx-conexao/LIST");
}

async function gravar(obj) {
  await caches.default.put(
    chave(),
    new Response(JSON.stringify(obj), {
      headers: {
        "content-type": "application/json",
        "Cache-Control": "max-age=86400",
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
      if (!item) return json({ vazio: true });
      return json(item);
    }

    if (acao === "definir" && request.method === "POST") {
      const segredo = (context.env && context.env.SEGREDO_CONFIG) || "";
      if (!segredo) return json({ error: "defina a env SEGREDO_CONFIG no Cloudflare Pages" }, 503);
      let corpo = {};
      try {
        corpo = await request.json();
      } catch (e) {
        return json({ error: "json" }, 400);
      }
      if (String(corpo.segredo || "") !== segredo) return json({ error: "segredo inválido" }, 403);
      const salvo = { atualizado: new Date().toISOString() };
      const vm = String(corpo.versaoMinima || "").trim();
      if (vm) salvo.versaoMinima = vm.slice(0, 20);
      const msg = String(corpo.mensagem || "").trim();
      if (msg) salvo.mensagem = msg.slice(0, 200);
      const aviso = String(corpo.aviso || "").trim();
      if (aviso) salvo.aviso = aviso.slice(0, 200);
      await gravar(salvo);
      return json({ ok: true, salvo });
    }
  } catch (e) {
    return json({ error: String(e && e.message ? e.message : e) }, 500);
  }

  return json({ error: "método" }, 405);
}
