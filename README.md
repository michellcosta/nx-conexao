# Saimo TV · Ligar na TV

Página do QR (`/ligar.html`) no visual da [Saimo TV](https://saimo-tv.pages.dev/).

O celular manda Xtream / M3U para o Worker  
`https://raspy-sunset-1e1a.michellcosta1269.workers.dev`  
e a TV puxa o código.

## Cloudflare Pages (importante)

**Não ligue este repositório no projeto que já publica `saimo-tv.pages.dev`.**  
Isso apagaria o catálogo. Crie um **projeto Pages novo**, ou envie só o `ligar.html` no projeto antigo.

### Projeto novo
1. Cloudflare → Workers & Pages → Create → Pages → Connect to Git
2. Repositório: `saimo-ligar`
3. Framework: None · Build: vazio · Output: `/`
4. Depois do deploy, a URL fica tipo `https://saimo-ligar.pages.dev/ligar.html`

Se quiser o endereço `https://saimo-tv.pages.dev/ligar.html`, faça upload só deste `ligar.html` (e do `icon-512.png`) no projeto Pages **já existente**, sem trocar o Git do site.

## Local
Abra `ligar.html` no navegador. Sem o `?c=` da TV aparece “sem código”.
