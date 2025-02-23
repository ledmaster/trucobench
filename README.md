# 🏆 TrucoBench: O Campo de Batalha Definitivo para a AGI

Enquanto grandes laboratórios perdem tempo ensinando LLMs a jogar xadrez ou resolver equações diferenciais, eu descobri *o verdadeiro caminho para a SuperInteligência Artificial*:  

**DOMINAR O TRUCO!** 🤯🎉

Mas sério, eu queria encontrar uma tarefa em português que exigisse:
✅ Conhecimento cultural que esteja majoritariamente em português em textos na internet (Têm mais materiais sobre pôquer do que truco em inglês)
✅ Não possa ser respondido apenas com conhecimentos gerais (por exemplo, "Quem descobriu o Brasil?")
✅ Exija "raciocínio" estratégico, planejamento. Quero saber se o modelo consegue entender as regras ao ponto de planejar maneiras de vencer o jogo

Algumas inspirações:
- [Tweet do Karpathy](https://x.com/karpathy/status/1885740680804504010) sugerindo a superioridade de testar LLMs usando jogos
- [SnakeBench](https://snakebench.com/): LLMs jogando o jogo da cobrinha entre eles
- [Minecraft](https://x.com/hamptonism/status/1849537031568781424): você encontra vários tweets de usuários comparando quais modelos constróem estruturas melhores no Minecraft

## Resultados

| Modelo                              | Pontuação | Vit | Der | % Vit |
|-------------------------------------|-----------|------|--------|----------|
| claude-3.5-sonnet                   | 2.87      | 24   | 11     | 68.6     |
| qwen-plus                           | 2.75      | 19   | 11     | 63.3     |
| o3-mini                             | 2.34      | 17   | 14     | 54.8     |
| gpt-4o                              | 2.33      | 17   | 15     | 53.1     |
| claude-3.5-haiku                    | 2.24      | 17   | 18     | 48.6     |
| qwen-turbo                          | 2.22      | 14   | 16     | 46.7     |
| qwen-max                            | 2.2       | 17   | 15     | 53.1     |
| deepseek-r1                         | 2.14      | 17   | 18     | 48.6     |
| gemini-2.0-flash-lite-preview-02-05 | 2.09      | 16   | 15     | 51.6     |
| gemini-1.5-pro                      | 2.03      | 15   | 17     | 46.9     |
| gemini-2.0-flash                    | 1.88      | 15   | 16     | 48.4     |
| gpt-4o-mini                         | 1.69      | 14   | 21     | 40.0     |
| deepseek-chat                       | 1.63      | 11   | 20     | 35.5     |

Os resultados são rankeados pelo modelo [Bradley-Terry](https://en.wikipedia.org/wiki/Bradley%E2%80%93Terry_model) que é bastante utilizado para avaliar LLMs, inclusive para fazer o pós-treino.

Pedi ao DeepSeek R1 que me ajudasse a analisar os dados das partidas, e ele me ajudou a ver padrões interessantes:
- O Qwen Plus foi o mais agressivo. Sempre apostando logo de primeira. Isso o ajudou a ficar em segundo lugar porque ele assustava a maioria dos modelos, que corriam das apostas.
- Modelos menores sofrem para seguir padrões: em vários momentos eles tentam apostar fora de hora ou jogar cartas que não têm na mão
- O modelo mais estratégico é o Claude-3.5-Sonnet. Ele teve uma taxa de agressividade moderada mas a segunda maior taxa de desistências e uma taxa baixa de aceitação de apostas iniciadas pelos oponentes. Isso, junto ao fato dele ser o número 1 em termos de vitórias, sugere traços de pensamento estratégico nas decisões.
- O segundo modelo mais estratégico foi o o3-mini (avaliado com reasoning-effort='medium'). Ele também demonstra o padrão estratégico de apostas e desistências próximos do Claude, mas não parece decidir tão bem quanto o Sonnet.
- O DeepSeek V3 (deepseek-chat) era extremamente passivo. Basicamente nunca apostava e desistia com muita frequência diante de apostas (imagine o abuso do Qwen Plus contra ele).

### Respostas Interessantes dos LLMs

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

## Quão séria é essa benchmark?

> "Todas as benchmarks estão erradas, mas algumas são úteis."
> ***Machado de Assis***

⚠️ Esta benchmark foi um exercício para eu aprender mais sobre avaliações de LLMs e sobre o comportamento deles com prompts em português numa atividade que exige planejamento e "raciocínio" (ou algo parecido). Certamente existem bugs que, por mais que eu tenha verificado e testado, ainda estão no código. Então não considere essa (ou qualque outra) benchmark uma medida perfeita das capacidades dos LLMs. Além disso, a qualidade dos resultados pode variar dependendo do modelo e do prompt. Aqui sigo a seguinte recomendação:

> "Por favor, tente garantir que os bugs afetem todos os modelos de forma igual."
> ***[Ms. Casey, Lumon Industries](https://severance.wiki/half_loop_transcript)***

## Visão Geral do Código

O sistema é composto por dois módulos principais que trabalham em conjunto para simular partidas de Truco:

1. **Motor do Jogo (engine.py)**: Implementa toda a lógica do Truco paulista
2. **Partidas entre LLMs (llm_play.py)**: Responsável pela integração com modelos de linguagem para tomada de decisões

## Funcionamento do Código (recomendo conhecer as regras do Truco antes de ler)

### 1. **Fase de Inicialização**

- Cria um baralho de 40 cartas e embaralha
- Distribui 3 cartas por jogador
- Revela a **vira** e calcula as **manilhas**

Manilhas são as cartas mais fortes do jogo

---

### 2. **Andamento da Mão**

O truco é jogado em "mãos" e até 3 rodadas dentro dessas mãos. Cada vez que a inicialização acima acontece consideramos uma mão.

Em cada rodada os LLMs: 
   - Analisam o estado do jogo e suas cartas   
   - Decidem entre apostar, aceitar uma aposta, aumentar a aposta ou desistir da mão
   - Decidem quais cartas jogar, caso ninguém tenha desistido

Caso um LLM ganhe duas rodadas, ele ganha a mão e os pontos correspondentes.

---

### 3. **Partida**

A partida termina quando algum LLM atinge 12 pontos ou mais.

Isso às vezes acontece rápido (pode acontecer em uma mão só, se os LLMs ficarem aumentando a aposta), mas às vezes os LLMs são super passivos e ninguém aposta, jogando várias mãos dentro da mesma partida.

## Sistema de Seleção dos LLMs

Para cada partida sorteei um LLM para ser o jogador A e outro para ser o B, evitando que um LLM sempre fosse o primeiro ou último a jogar.

A ideia era ter, pelo menos, 30 partidas de cada LLM, então determinei o peso da amostra pela fórmula simples do UCB. Modelos com menos partidas totais tinham mais chances de participar.

## Aprendizados

### Verificação com LLMs

Para ver se as partidas estavam de acordo com as regras, usei "LLMs como juízes". 

Enviava o log da partida a um LLM e pedir para ele verificar vários fatores específicos e dizer se aquele log estava de acordo ou não.

Isso foi bastante útil para identificar problemas com a ordem de apostas e computação da pontuação das partidas.

Testei o o3-mini, o1, DeepSeek R1 e Gemini Flash Thinking para isso. Cada um exigiu um detalhe diferente no prompt, eles prestaram atenção a aspectos diferentes da checklist que eu passei. Fica a lição de sempre otimizar o prompt para o modelo que você vai usar. Um prompt não serve para todos os modelos igualmente.