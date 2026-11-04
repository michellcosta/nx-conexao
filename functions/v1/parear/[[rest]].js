const ABC = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

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

function codigoNovo() {
  let s = "";
  for (let i = 0; i < 6; i++) s += ABC[Math.floor(Math.random() * ABC.length)];
  return s;
}

function chave(code) {
  return new Request("https://parear.nx-conexao/" + String(code || "").toUpperCase());
}

async function gravar(code, obj, ttl) {
  await caches.default.put(
    chave(code),
    new Response(JSON.stringify(obj), {
      headers: {
        "content-type": "application/json",
        "Cache-Control": "max-age=" + (ttl || 360),
      },
    })
  );
}

async function ler(code) {
  const hit = await caches.default.match(chave(code));
  if (!hit) return null;
  try {
    return await hit.json();
  } catch (e) {
    return null;
  }
}

async function apagar(code) {
  try {
    await caches.default.delete(chave(code));
  } catch (e) {}
}

export async function onRequest(context) {
  const request = context.request;
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: cors() });
  }

  const rest = context.params.rest;
  const segs = Array.isArray(rest) ? rest : rest ? [rest] : [];
  const acao = String(segs[0] || "").toUpperCase();

  try {
    if (acao === "CRIAR" && request.method === "POST") {
      let code = "";
      for (let i = 0; i < 8; i++) {
        code = codigoNovo();
        if (!(await ler(code))) break;
      }
      await gravar(code, { pending: true }, 360);
      return json({ code: code, expira: 360 });
    }

    if (!acao || acao === "CRIAR") return json({ error: "rota" }, 404);

    const code = acao;
    if (request.method === "GET") {
      const item = await ler(code);
      if (!item) return json({ error: "código inválido ou vencido" }, 404);
      if (item.pending) return json({ pending: true, code: code });
      await apagar(code);
      return json(item);
    }

    if (request.method === "POST") {
      const item = await ler(code);
      if (!item) return json({ error: "código inválido ou vencido" }, 404);
      let corpo = {};
      try {
        corpo = await request.json();
      } catch (e) {
        return json({ error: "json" }, 400);
      }
      const tipo = String(corpo.tipo || "");
      if (tipo !== "xtream" && tipo !== "m3u_url" && tipo !== "m3u_txt") {
        return json({ error: "tipo inválido" }, 400);
      }
      const salvo = { tipo: tipo, pending: false };
      if (tipo === "xtream") {
        salvo.host = String(corpo.host || "");
        salvo.user = String(corpo.user || "");
        salvo.pass = String(corpo.pass || "");
      } else if (tipo === "m3u_url") {
        salvo.url = String(corpo.url || "");
      } else {
        const texto = String(corpo.texto || "");
        if (texto.length > 400000) return json({ error: "arquivo grande demais" }, 413);
        salvo.nome = String(corpo.nome || "lista.m3u");
        salvo.texto = texto;
      }
      await gravar(code, salvo, 360);
      return json({ ok: true });
    }
  } catch (e) {
    return json({ error: String(e && e.message ? e.message : e) }, 500);
  }

  return json({ error: "método" }, 405);
}
