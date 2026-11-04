# nx-conexao · Ligar na TV

Página do QR no visual da [Saimo TV](https://saimo-tv.pages.dev/).

O celular envia para o Worker  
`https://raspy-sunset-1e1a.michellcosta1269.workers.dev`

## Se o Git entrou como Worker (sua tela atual)

Isso **não é Pages**. O gráfico com Bindings / Observability é um Worker.

1. Espere o deploy depois deste `wrangler.toml`
2. Abra o Worker **nx-conexao**
3. Em **Domínios e rotas** (ou Settings → Domains), **ative** o `workers.dev`
4. A URL fica `https://nx-conexao.michellcosta1269.workers.dev/ligar.html`

## Se quiser Pages de verdade

Não use “Create Worker” / conectar Git no Worker.

1. No menu: **Workers & Pages**
2. **Create** → escolha **Pages** (não Worker)
3. Connect to Git → `nx-conexao`
4. Framework: None · build vazio · output `/`

Se o nome `nx-conexao` já estiver ocupado pelo Worker, o Pages pode se chamar `nx-conexao-web`.

**Não** conecte este repo no projeto do `saimo-tv.pages.dev`.
