# WASTH : Web App para a documentação de Sítios Tradicionais e Históricos

## Finalidade

Este projeto visa a fornecer uma interface intuitiva para a inserção e 
edição de informações dos [Documentários de arquitetura tradicional][1].
Os dados dos Documentários são conformes ao padrão [LIDO],
um subconjunto do [CIDOC/CRM] e portanto compatível com a
norma ISO 21127:2023.


## Como usar

A plataforma de teste deste aplicativo deve ser configurada com [UV]:

```
uv sync
uv pip install -e .
uv run wasth <comando> [PATH...]
```

### Comandos

- `wasth geojson [ARQUIVO OU PASTA] [ARQUIVO DE SAÍDA]`
  gera um arquivo .geojson que pode ser aberto no QGIS,
  a partir das fichas de edificações ou lugares em formato Markdown
  no arquivo ou pasta indicado.

Para obter ajuda, `uv run wasth --help`.

No momento, apenas `wasth geojson` funciona.
`[PATH]` é relativo ao diretório de execução do comando e
aceita um nome de arquivo `*.md`
ou um nome de pasta contendo um ou mais arquivos, dependendo do comando.


## Roteiro de desenvolvimento

- [x] Lint formatação YAML;
- [x] Normaliza cabeçalhos YAML das fichas para sintaxe, não contra esquema;
- [x] Valida cabeçalhos YAML das fichas contra esquema de preenchimento;
- [x] Gera Open Location Code a partir de coordenadas;
- [ ] Converte bibliographiCitation DCMI para LIDO;
- [ ] Valida fichas preenchidas contra especificação XSD do LIDO;
- [ ] Interface de criação de novas fichas;
- [ ] Interface de edição de fichas existentes;
- [ ] Interface de georreferenciamento das fichas;
- [ ] Integração dos vocabulários controlados na interface de preenchimento.

* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

[1]: https://github.com/arqtrad
[LIDO]: https://icom-documentation.mini.icom.museum/working-groups/lido/
[CIDOC/CRM]: https://cidoc-crm.org
[UV]: https://github.com/astral-sh/uv

WASTH (c) 2026 by Pedro P. Palazzo is licensed under MIT License.
