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
uv run pytest
uv run src/wasth/valida_yaml.py [PATH...]
```

No momento, apenas `src/wasth/valida_yaml.py` e `src/wasth/valida_xml.py` 
funcionam parcialmente.
`[PATH]` é relativo ao diretório de execução do comando e
aceita uma sequência de nomes de arquivos `*.md` separados por espaços
ou um nome de pasta contendo um ou mais arquivos.


## Roteiro de desenvolvimento

- [x] Lint formatação YAML;
- [x] Valida cabeçalhos YAML das fichas contra modelo de preenchimento;
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
