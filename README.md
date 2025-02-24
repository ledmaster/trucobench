# 🏆 TrucoBench: O Campo de Batalha Definitivo para a AGI

Enquanto grandes laboratórios perdem tempo ensinando LLMs a jogar xadrez ou resolver equações diferenciais, eu descobri *o verdadeiro caminho para a SuperInteligência Artificial*:  

**DOMINAR O TRUCO!** 🤯🎉

Mas sério, eu queria encontrar uma tarefa em português que exigisse:
- ✅ Conhecimento cultural que esteja majoritariamente em português em textos na internet (Têm mais materiais sobre pôquer do que truco em inglês)
- ✅ Não possa ser respondido apenas com conhecimentos gerais (por exemplo, "Quem descobriu o Brasil?")
- ✅ Exija "raciocínio" estratégico, planejamento. Quero saber se o modelo consegue entender as regras ao ponto de planejar maneiras de vencer o jogo

Algumas inspirações:
- [Tweet do Karpathy](https://x.com/karpathy/status/1885740680804504010) sugerindo a superioridade de testar LLMs usando jogos
- [SnakeBench](https://snakebench.com/): LLMs jogando o jogo da cobrinha entre eles
- [Minecraft](https://x.com/hamptonism/status/1849537031568781424): você encontra vários tweets de usuários comparando quais modelos constróem estruturas melhores no Minecraft

## Resultados

**⭐ Tá gostando? Deixe uma estrela!**

Os LLMs jogaram diversas partidas entre si.

Abaixo, confira a tabela com os resultados e depois explore algumas análises que destacam os pontos fortes e as peculiaridades de cada modelo.


| Modelo                              | Pontuação | Vit | Der | % Vit |
|-------------------------------------|-----------|------|--------|----------|
| claude-3.5-sonnet                   | 2.59      | 26   | 11     | 70.3     |
| qwen-plus                           | 2.45      | 23   | 12     | 65.7     |
| o3-mini                             | 2.03      | 18   | 14     | 56.2     |
| gpt-4o                              | 1.98      | 19   | 16     | 54.3     |
| qwen-max                            | 1.96      | 23   | 17     | 57.5     |
| qwen-turbo                          | 1.95      | 16   | 16     | 50.0     |
| deepseek-r1                         | 1.86      | 19   | 18     | 51.4     |
| gemini-2.0-flash-thinking-exp-01-21 | 1.77      | 15   | 16     | 48.4     |
| claude-3.5-haiku                    | 1.74      | 18   | 22     | 45.0     |
| gemini-1.5-pro                      | 1.71      | 18   | 18     | 50.0     |
| gemini-2.0-flash-lite-preview-02-05 | 1.6       | 17   | 18     | 48.6     |
| gpt-4o-mini                         | 1.33      | 17   | 24     | 41.5     |
| gemini-2.0-flash                    | 1.32      | 15   | 19     | 44.1     |
| chatgpt-4o-latest                   | 1.28      | 13   | 21     | 38.2     |
| deepseek-chat                       | 1.2       | 11   | 21     | 34.4     |

Os resultados são rankeados pelo modelo [Bradley-Terry](https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model) que é bastante utilizado para avaliar LLMs, inclusive para fazer o pós-treino.

Pedi ao DeepSeek R1 que me ajudasse a analisar os dados das partidas, e ele me ajudou a ver padrões interessantes:
- O Qwen Plus foi o mais agressivo. Sempre apostando logo de primeira. Isso o ajudou a ficar em segundo lugar porque ele assustava a maioria dos modelos, que corriam das apostas.
- Modelos menores sofrem para seguir padrões: em vários momentos eles tentam apostar fora de hora ou jogar cartas que não têm na mão
- O modelo mais estratégico é o Claude-3.5-Sonnet. Ele teve uma taxa de agressividade moderada mas a segunda maior taxa de desistências e uma taxa baixa de aceitação de apostas iniciadas pelos oponentes. Isso, junto ao fato dele ser o número 1 em termos de vitórias, sugere traços de pensamento estratégico nas decisões.
- O segundo modelo mais estratégico foi o o3-mini (avaliado com reasoning-effort='medium'). Ele também demonstra o padrão estratégico de apostas e desistências próximos do Claude, mas não parece decidir tão bem quanto o Sonnet.
- O DeepSeek V3 (deepseek-chat) era extremamente passivo. Basicamente nunca apostava e desistia com muita frequência diante de apostas (imagine o abuso do Qwen Plus contra ele).

O custo total aproximado para rodar as partidas foi de R$ 262,43.

### Situações Interessantes

#### Claude Sonnet 3.5 respondendo a um truco do Qwen Plus

Analisando a situação:

1. Tenho uma Dama de Paus, 3 de Espadas e 4 de Ouros
2. O 5 é manilha em todos os naipes
3. Minhas cartas não são muito fortes (nenhuma manilha)
4. O adversário trucou logo no início
5. O placar está 0x0
6. O risco de perder 3 pontos é considerável com cartas fracas

Dado que minhas cartas são relativamente fracas e o adversário trucou, a decisão mais prudente é correr

#### Claude Sonnet 3.5 na mesma partida

Vou analisar a situação:
- Tenho um Ás de Copas, 7 de Paus e Dama de Paus
- A vira é 2 de Copas, então as manilhas são os 3s
- Tenho uma boa mão: 7 e Q de Paus são cartas altas, e o Ás de Copas também é forte
- O adversário pediu truco (aposta de 3 pontos)
- Estou perdendo por 1x0
- É a segunda rodada de apostas

Com uma mão relativamente forte e estando perdendo, vale a pena aumentar a aposta. A lógica é: tenho boas cartas e preciso pontuar para alcançar o adversário. O risco de aumentar para 6 se justifica pela força da minha mão e pela necessidade de pontos.

#### Qwen Plus perde do R1 porque não entende o jogo

Em uma partida com placar 9x10 entre o Deepseek R1 e o Qwen Plus, o Qwen levanta a aposta para "seis". O R1 raciocina e conclui que ele não pode correr, já que o adversário ganharia 3 pontos e ganharia a partida. Como tinha manilha, o R1 decide subir a aposta para "nove" para tentar fazer o adversário desistir, já que sua manilha era do naipe mais fraco. O Qwen Plus, não entendendo que se corresse perderia o jogo automaticamente, correu com a seguinte justificativa:

Justificativa: Estamos em uma situação de alta aposta (9 pontos) com cartas relativamente fracas (KOP e 5OU) e precisamos proteger nosso placar atual de 10 pontos, já que o adversário está muito próximo de vencer o jogo com 9 pontos. Correr é a melhor opção para evitar perder muitos pontos com um mão desvantajosa.

#### DeepSeek R1 pensa demais e se confunde

Apesar de ter as regras do jogo especificadas no prompt inicial, o DeepSeek fica repetidamente se questionando sobre esses aspectos: "That doesn't make sense," "Maybe there's a typo," "But according to the rules...".

Ele costuma se confundi ao ver duas cartas na mão em vez de três (mesmo tendo a informação que não é a primeira rodada da mão) e questiona a força de cada carta com relação ao ranking delas em outros tipos de jogos (como pôquer).

Já havia visto esse padrão em alguns posts no X, onde não apenas o R1, mas outros modelos sentem dificuldade quando vêem algo no prompt que vai contra o que viram durante o treinamento.

Neste caso, o R1 deve ter visto bem mais texto sobre outros jogos de cartas e precisa se esforçar para superar esses padrões. Isso pode explicar a baixa performance.

Existe um [paper que sugere que LLMs produzem mais tokens de raciocínio quando erram respostas](https://arxiv.org/abs/2501.18585).

Ele foi MUITO repetitivo nesses jogos, o que o fez ser o modelo mais caro para rodar (muitos tokens de raciocínio que são cobrados como "output tokens").


## Quão séria é essa benchmark?

> "Todas as benchmarks estão erradas, mas algumas são úteis."
> 
> ***Machado de Assis***

⚠️ Esta benchmark foi um exercício para eu aprender mais sobre avaliações de LLMs e sobre o comportamento deles com prompts em português numa atividade que exige planejamento e "raciocínio" (ou algo parecido). Certamente existem bugs que, por mais que eu tenha verificado e testado, ainda estão no código. Então não considere essa (ou qualque outra) benchmark uma medida perfeita das capacidades dos LLMs. Além disso, a qualidade dos resultados pode variar dependendo do modelo e do prompt. Aqui sigo a seguinte recomendação:

> "Por favor, tente garantir que os bugs afetem todos os modelos de forma igual."
> 
> ***[Ms. Casey, Lumon Industries](https://severance.wiki/half_loop_transcript)***

## Por Dentro do TrucoBench

Disponibilizei o código para te dar uma ideia de como fazer uma benchmark, mas você não conseguirá rodá-lo do jeito que está aqui.

O sistema é dividido em duas partes essenciais:
- **Engine do Jogo:** Responsável por implementar as regras e a lógica do truco (arquivo `engine.py`).
- **Integração com LLMs:** Gerencia as partidas e a tomada de decisões dos modelos (arquivo `llm_play.py`).

### Fluxo da Partida

1. **Inicialização:**  
   - Criação e embaralhamento do baralho  
   - Distribuição de 3 cartas por jogador  
   - Definição da **vira** e cálculo das **manilhas**

2. **Andamento da Mão:**  
   - Os LLMs analisam a situação e escolhem entre apostar, aceitar, aumentar ou desistir.  
   - São jogadas até três rodadas por mão, onde o vencedor da maioria das rodadas leva os pontos.

3. **Final da Partida:**  
   - A partida termina quando um dos LLMs atinge 12 pontos.
   
## Sistema de Seleção dos LLMs

Para cada partida sorteei um LLM para ser o jogador A e outro para ser o B, evitando que um LLM sempre fosse o primeiro ou último a jogar.

A ideia era ter, pelo menos, 30 partidas de cada LLM, então determinei o peso da amostra pela fórmula simples do UCB. Modelos com menos partidas totais tinham mais chances de participar.

## Aprendizados

### Verificação com LLMs

Para ver se as partidas estavam de acordo com as regras, usei "LLMs como juízes". 

Enviava o log da partida a um LLM e pedir para ele verificar vários fatores específicos e dizer se aquele log estava de acordo ou não.

Isso foi bastante útil para identificar problemas com a ordem de apostas e computação da pontuação das partidas.

Testei o o3-mini, o1, DeepSeek R1 e Gemini Flash Thinking para isso. Cada um exigiu um detalhe diferente no prompt, eles prestaram atenção a aspectos diferentes da checklist que eu passei. Fica a lição de sempre otimizar o prompt para o modelo que você vai usar. Um prompt não serve para todos os modelos igualmente.

### A formatação do prompt importa muito!

Os verificadores tiveram imensa dificuldade em entender o andamento do jogo quando eu passava o histórico de jogadas em JSON. Quando fiz o parsing para "texto livre", a performance mudou completamente. Não cheguei a medir um ou outro, mas parece que mesmo em modelos modernos a formatação do prompt (JSON, Markdown, etc) faz bastante diferença!

### Ler o raciocínio e respostas de modelos que não raciocinam para melhorar os prompts

Em modelos que mostram o raciocínio, ou em modelos que justificam suas jogadas, é importante ler e entender se há erros consistentes. Por exemplo, os modelos se mostraram confusos em relação às apostas que estavam valendo (achavam que tinham que aceitar apostas quando não tinha nada pendente).

Deve dar pra melhorar isso iterando sobre os prompts para deixar mais claro. Eu fiz um prompt bem básico, sem muitos truques ou iterações, para não dar vantagens aos modelos que estou acostumado a usar e, portanto, tenho um estilo de prompt mais favorável.

### Nunca acredite em apenas uma benchmark

Se você olhar o ranking dos modelos, terá a impressão que o Qwen Plus é um baita modelo bom comparado a outros como o o3-mini. Na realidade, ele ganha por puro bullying!

O Sonnet 3.5 parece ser o único modelo que consegue identificar e se aproveitar disso.

Por isso, nunca confie apenas em uma benchmark, veja várias benchmarks e preste atenção a modelos que vão bem em várias tarefas diferentes.

E, claro, crie seu próprio conjunto de dados para avaliar o modelo na tarefa específica que você quer resolver.