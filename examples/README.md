# Exemplos do EV3 Studio

## Teste motor e tela

Abra o arquivo `teste_motor_tela.ev3proj` no EV3 Studio.

O programa faz o seguinte:

1. Usa o motor conectado à porta A;
2. Gira o motor a 50% por 2 segundos;
3. Limpa a tela do EV3;
4. Escreve `Teste OK` na tela;
5. Aguarda 1 segundo.

## Teste recomendado antes do envio

1. Conecte o motor à porta A.
2. Deixe o robô suspenso ou retire as rodas do chão.
3. Abra o projeto em **Arquivo → Abrir**.
4. Confira o Python usando `F5`.
5. Clique em **F7** para simular.
6. Se a simulação estiver correta, conecte o EV3 por USB.
7. Abra **⚙ Robô**, selecione USB e clique em **Detectar EV3**.
8. Clique em **F6** para executar no EV3.
9. Pressione **Esc** ou **Shift+F6** para interromper.

O código gerado deve começar com `motor_a.run_time(...)` sem espaços antes da linha. Se houver uma indentação inesperada no início do programa, gere novamente o código abrindo o projeto no editor atualizado.
