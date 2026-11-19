# Roteiro do vídeo (até 5 minutos)

Gravação de tela com narração. Tempo-alvo: 4min50. Ensaie uma vez com cronômetro.

Antes de gravar: painel aberto na aba Visão geral, navegador em tela cheia com zoom de 110%, e um terminal
pronto na pasta do projeto, com o ambiente ativo e o comando `python -m pytest tests -q` já digitado.

## 1. Abertura (0:00 a 0:25)

**Tela:** aba Visão geral, topo.
**Mostrar:** o nome ZelaSP e o título. Não role ainda.
**Fala:** "Grupo 67, Jocasta Bortolacci e Pedro Henrique Souza. Este é o ZelaSP, uma prova de conceito de plataforma de inteligência
urbana. O problema: quem pede um serviço de zeladoria em São Paulo não sabe quanto tempo vai esperar. E a
gestão, com centenas de milhares de pedidos por trimestre, precisa de uma leitura clara de prioridades: onde
agir primeiro para atender mais gente. O público são moradores e gestores das subprefeituras."

## 2. O problema em números (0:25 a 0:55)

**Tela:** aba Visão geral.
**Mostrar:** os cinco números do topo, parando em "54 dias". Depois as barras de volume e atraso.
**Fala:** "Usei dados abertos reais do SP156: 433 mil pedidos de zeladoria, de janeiro a setembro de 2026.
Metade é resolvida em 4 dias, mas um em cada cinco espera mais de 54. E o atraso não está espalhado: três
serviços, tapa-buraco, poda de árvore e guias e sarjetas, somam 35% do volume e 63% do atraso."

## 3. Tratamento dos dados (0:55 a 1:20)

**Tela:** aba Método. Abra o painel "Dados e tratamento".
**Mostrar:** a coluna de formato de data, em que a terceira linha difere das outras. Depois o funil.
**Fala:** "O tratamento foi a parte mais crítica. Os arquivos do portal têm formatos diferentes: um deles traz
as datas no padrão mês/dia. O programa detecta o formato de cada arquivo e interrompe a carga se houver
dúvida. Os dados vão para um banco relacional, com modelo dimensional e restrições de integridade."

## 4. Método e equidade (1:20 a 1:50)

**Tela:** aba Distritos.
**Mostrar:** os cinco números do topo. Passe o mouse em dois círculos do mapa. Role até os três perfis.
**Fala:** "17% dos pedidos ainda estão em aberto, então usei Kaplan-Meier em vez de média. E como distritos
pedem serviços diferentes, criei um índice que compara cada um com o esperado para o seu conjunto de
serviços. Resultado: 44 dos 96 distritos resolvem menos que o esperado, e isso não é centro contra periferia.
O K-Means separa três perfis de distrito."

## 5. Onde está a desigualdade (1:50 a 2:10)

**Tela:** aba Serviços.
**Mostrar:** o gráfico de barras do topo. Depois os quatro números da poda de árvore.
**Fala:** "No mesmo serviço, o distrito pode mudar o resultado em mais de 40 pontos. Em poda de árvore, um
distrito finaliza 26% em 30 dias e outro, 79%. Remoção de entulho é igual na cidade toda."

## 6. Valor para a gestão (2:10 a 2:55)

**Tela:** aba Onde agir.
**Mostrar:** os quatro números. Arraste "Frentes a priorizar" de 50 para 100. Role até o Alerta antecipado e
aponte, no gráfico da direita, a barra dourada e o traço branco em cada data.
**Fala:** "Para a gestão, o sistema propõe uma ordem de prioridade. Cem frentes de serviço e distrito
concentram 66% do atraso evitável. E há um alerta antecipado: um modelo de sobrevivência estima quais pedidos
em aberto vão passar de 30 dias, considerando há quanto tempo cada um já espera. Simulei em seis datas
passadas, e o total previsto ficou a no máximo 5% do real. A taxa histórica simples erra 30%."

## 7. Valor para o morador (2:55 a 3:30)

**Tela:** aba Abrir pedido.
**Mostrar:** digite `galho de árvore encostando na fiação, precisa podar` e aperte Enter. Aponte os três
serviços, os quatro números e o gráfico "De onde vem a estimativa". Troque o distrito uma vez.
**Fala:** "Para o morador: ele descreve o problema com as próprias palavras. Um recomendador com TF-IDF e
similaridade de cosseno sugere o serviço, e o sistema mostra o prazo no distrito dele, com o histórico e a
estimativa do modelo. Dados pessoais são mascarados. A orientação pode ser redigida por IA generativa, com
uma trava: se a resposta trouxer um número que o sistema não calculou, ela é descartada."

## 8. Modelos (3:30 a 3:50)

**Tela:** aba Método.
**Mostrar:** o gráfico de AUC por modelo e a calibração.
**Fala:** "Comparei regressão logística, gradient boosting e rede neural, com validação temporal. Só o tipo
de serviço já dá AUC de 0,82. Com o distrito, 0,84. A rede neural empatou com o gradient boosting."

## 9. Testes (3:50 a 4:05)

**Tela:** terminal.
**Mostrar:** aperte Enter no comando já digitado e espere aparecer "51 passed".
**Fala:** "São 51 testes automatizados, cobrindo leitura dos arquivos, cálculos estatísticos, o alerta,
integridade do banco, injeção de SQL e as travas da IA."

## 10. Limitações e fechamento (4:05 a 4:45)

**Tela:** aba Método. Abra o painel "Limitações".
**Mostrar:** a lista inteira.
**Fala:** "Limitações: finalizado é encerramento no sistema, não execução confirmada. A base só tem o que foi
registrado. O alerta foi validado por simulação, não em operação. E a IA generativa não foi validada com um
provedor real. O projeto integra tratamento de dados, banco SQL, estatística, aprendizado supervisionado e
não supervisionado, redes neurais, recomendação, IA generativa, segurança e visualização. Contribui para os
ODS 11, 10 e 16, e o impacto se mede pela diferença de prazo entre distritos no mesmo serviço. Obrigada."

## Se passar de 5 minutos

Corte nesta ordem: o bloco 8, a troca de distrito no bloco 7, e a rolagem até os perfis no bloco 4.

## Antes de publicar

- YouTube em modo Não listado. Teste o link em janela anônima.
- Não diga a frase de participação na competição: a entrega é só para nota.
- Se a IA generativa não estiver configurada, o painel mostra "redação padrão". Diga "pode ser redigida por
  IA generativa", como está no roteiro, e não que ela está rodando.
