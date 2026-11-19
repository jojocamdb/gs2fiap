# Roteiro do vídeo (até 5 minutos)

Gravação de tela com narração. Deixe o painel aberto e o terminal pronto antes de gravar.
Tempo-alvo: 4min55, sem folga. Ensaie uma vez com cronômetro. Se passar de 5min, corte o bloco de agrupamento e modelos e o exemplo do CPF.

## 0:00 a 0:20 · Abertura (câmera ou capa do PDF)

"Grupo 67, Jocasta Bortolacci.
Este é o ZelaSP, uma plataforma de inteligência urbana: transparência para quem vive, inteligência para quem cuida.
A pergunta de partida: o mesmo pedido de zeladoria leva o mesmo tempo em qualquer distrito de São Paulo?"

## 0:20 a 0:55 · Problema e dado (aba Visão geral, rolando devagar)

"Quem abre um pedido no SP156 não sabe quanto tempo ele costuma levar, nem se seria atendido mais rápido em outro bairro.
Usei os dados abertos do SP156: 433 mil pedidos de zeladoria, de janeiro a setembro de 2026, nos 96 distritos.
Na cidade, 75% são finalizados em 30 dias. Entre distritos, vai de 58 a 88%."

Pare no bloco "O mesmo buraco, dois distritos".

"O mesmo pedido de tapa-buraco: em um distrito, metade é finalizada em 6 dias. Em outro, em 70."

Desça até o gráfico de pontos.

"E a diferença não está em todo serviço. Entulho é igual na cidade inteira. Guias, galerias e poda de árvore, não."

## 0:55 a 1:45 · Decisões de método (aba Método, depois aba Distritos)

Mostre a tabela de arquivos lidos e o funil.

"Três decisões sustentam o resultado.
Primeira: os arquivos do portal têm formatos diferentes. O terceiro trimestre vem com data no padrão mês/dia. Lido sem validação, ele troca datas sem dar erro. O ETL detecta o formato de cada arquivo e para se houver ambiguidade.
Segunda: 17% das demandas ainda estão em aberto. Média só das finalizadas subestima o prazo. Usei Kaplan-Meier, que aproveita as abertas.
Terceira: distritos pedem serviços diferentes. Comparar taxa bruta mistura desempenho com tipo de pedido. O índice de equidade compara cada distrito com o esperado para o mix dele."

Vá para a aba Distritos e passe o mouse em dois distritos no mapa.

## 1:45 a 2:35 · Resultado principal (aba Serviços)

"O resultado: a desigualdade existe, é estável entre trimestres e está concentrada em poucos serviços.
Remoção de entulho é praticamente igual na cidade inteira. Poda de árvore vai de 26% em um distrito a 79% em outro."

Selecione Tapa-buraco e mostre a curva de dois distritos.

"E um resultado que contrariou minha hipótese: não é centro contra periferia. A correlação com a distância ao centro é fraca e de sinal contrário. Isso não prova que a periferia é mais bem atendida, porque a base só tem o que foi registrado, e finalizada não é o mesmo que resolvida."

## 2:35 a 3:10 · Onde agir primeiro (aba Onde agir)

"Saber o prazo não reduz o prazo. Por isso a segunda aba é para a prefeitura.
Se cada combinação de serviço e distrito abaixo da referência alcançasse o distrito mediano, seriam 14 mil pedidos a mais finalizados em 30 dias. E 100 combinações concentram 66% disso."

Mova o controle de 50 para 100 e mostre a tabela.

"Aqui está a fila de pedidos que já passaram do prazo típico do próprio serviço, por subprefeitura. E aqui, os pontos onde vários moradores pedem a mesma coisa a menos de 100 metros: uma ida da equipe resolve vários pedidos."

"Um cuidado: priorizar por volume favorece quem reclama mais. Por isso a comparação é sempre com a referência do próprio serviço."

## 3:10 a 3:25 · Agrupamento e modelos (aba Método, painel Modelos)

"Nos modelos, com validação temporal, só o tipo de serviço já dá AUC 0,82, e o distrito leva a 0,84. A rede neural empata com o gradient boosting. O K-Means separa três grupos de distritos, com silhueta baixa, que eu reporto."

## 3:25 a 4:10 · Demonstração para o morador (aba Abrir pedido)

Digite: `galho de árvore encostando na fiação, precisa podar`. Escolha um distrito.

"O morador descreve o problema com as palavras dele. O recomendador, com TF-IDF e similaridade de cosseno, sugere o serviço certo. O sistema mostra o prazo naquele distrito: metade finalizada em tantos dias, oito em cada dez em tantos."

Troque o distrito e mostre os números mudando.

Se estiver apertado de tempo, pule o exemplo do CPF e só mencione.

Digite um texto com CPF fictício: `buraco na rua, meu cpf é 123.456.789-09`.

"Dado pessoal é mascarado antes de qualquer uso. A orientação é redigida a partir de uma ficha de fatos. Com IA generativa ativa, a resposta é conferida: se trouxer um número que não está na ficha, é descartada."

Abra o expansor da ficha de fatos.

## 4:10 a 4:30 · Banco e testes (terminal)

Rode `python -m pytest tests -q` e mostre o resultado.

"Os dados ficam em um banco relacional com modelo dimensional e restrições de integridade. Endereço não é armazenado. São 47 testes automatizados, incluindo injeção de SQL e as travas da IA."

## 4:30 a 4:55 · Integração, ODS e fechamento

"O projeto integra tratamento de dados, banco SQL, estatística, aprendizado supervisionado e não supervisionado, redes neurais, recomendação, IA generativa, segurança e visualização interativa.
Contribui para os ODS 11, 10 e 16. O impacto se mede pela diferença de prazo entre distritos no mesmo serviço, recalculada a cada trimestre.
Limitações e próximos passos estão no PDF. ZelaSP: uma cidade melhor começa com uma gestão mais inteligente. Obrigada."

## Antes de publicar

- YouTube em modo Não listado.
- Não diga a frase de participação na competição: a entrega é só para nota.
- Se a IA generativa não estiver configurada, o painel mostra "redação padrão". Nesse caso, diga "quando a IA generativa está ativa" em vez de afirmar que ela está rodando.
