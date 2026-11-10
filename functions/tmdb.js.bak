// Proxy TMDB para o Saimo TV (mesmo contrato do worker antigo):
// GET /tmdb?p=/search/movie&language=pt-BR&query=X
// A chave vive em env TMDB_CHAVE (dashboard do Pages), nunca no git.
// Cache curto em caches.default: buscas repetidas não batem na TMDB.

function cors() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
    "Access-Control-Allow-Headers": "content-type, accept",
  };
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...cors() },
  });
}

function chaveCache(url) {
  return new Request("https://tmdb.nx-conexao/" + url);
}

export async function onRequest(context) {
  const request = context.request;
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: cors() });
  }
  if (request.method !== "GET") return json({ error: "método" }, 405);

  const chave = (context.env && context.env.TMDB_CHAVE) || "";
  if (!chave) return json({ error: "defina a env TMDB_CHAVE no Cloudflare Pages" }, 503);

  const url = new URL(request.url);
  const p = url.searchParams.get("p") || "";
  if (!/^\/[a-z0-9._/-]+$/i.test(p)) return json({ error: "p inválido" }, 400);

  // repassa todos os params menos o p; api_key entra só aqui
  const destino = new URL("https://api.themoviedb.org/3" + p);
  url.searchParams.forEach(function (v, k) {
    if (k !== "p") destino.searchParams.set(k, v);
  });
  destino.searchParams.set("api_key", chave);

  const alvo = destino.toString();

  // cache de 10 min por URL (placar/tabela/search repetem muito entre boots)
  const ck = chaveCache(alvo);
  try {
    const hit = await caches.default.match(ck);
    if (hit) return new Response(hit.body, { headers: { "content-type": "application/json; charset=utf-8", ...cors() } });
  } catch (e) {}

  let res;
  try {
    res = await fetch(alvo, { headers: { accept: "application/json" } });
  } catch (e) {
    return json({ error: "TMDB inacessível" }, 502);
  }
  const corpo = await res.text();
  if (!res.ok) return new Response(corpo, { status: res.status, headers: { "content-type": "application/json; charset=utf-8", ...cors() } });

  try {
    await caches.default.put(
      ck,
      new Response(corpo, {
        headers: { "content-type": "application/json", "Cache-Control": "max-age=600" },
      })
    );
  } catch (e2) {}
  return new Response(corpo, { headers: { "content-type": "application/json; charset=utf-8", ...cors() } });
}
