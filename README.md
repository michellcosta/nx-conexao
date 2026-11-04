# nx-conexao · Ligar na TV

Site estático para **Cloudflare Pages** (`*.pages.dev`). Não é Worker.

O celular envia para  
`https://raspy-sunset-1e1a.michellcosta1269.workers.dev`

## Publicar no Pages

1. Apague o **Worker** `nx-conexao` (Settings → Delete). O GitHub fica.
2. Cloudflare → **Workers & Pages** → **Create application**
3. Aba **Pages** (não Worker)
4. **Connect to Git** / **Import an existing Git repository**
5. Repositório: `michellcosta/nx-conexao`
6. Configuração:
   - Production branch: `master`
   - Framework preset: **None**
   - Build command: vazio (ou `exit 0`)
   - Build output directory: `/`
7. **Save and Deploy**

URL: `https://nx-conexao.pages.dev/ligar`

Não conecte este repo no projeto do `saimo-tv.pages.dev`.
