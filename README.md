# nx-conexao · Ligar na TV

Página + API de pareamento no Cloudflare Pages.

- Site: `https://nx-conexao.pages.dev/ligar`
- API: `https://nx-conexao.pages.dev/v1/parear/criar`
- /v1/bases: fontes VOD remotas (segredo em env SEGREDO_BASES)
- /v1/config: versao minima e mensagem remota (env SEGREDO_CONFIG)
- /v1/diag + /log: diagnostico remoto das TVs
- /epg.json: grade de 6 h para a TV (Action a cada 4 h)
- /tmdb: proxy TMDB com chave em env TMDB_CHAVE (substitui o worker saimo-webos, que serve 1042)
- redepoy p/ ativar TMDB_CHAVE
