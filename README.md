# EV3 Studio — MVP para Linux

O EV3 Studio é um aplicativo desktop em Python para programar o LEGO Mindstorms EV3 com blocos e enviar o programa para o robô usando Pybricks.

## Instalação

```bash
cd ~/Projetos/ev3-studio
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

O EV3 precisa estar com firmware EV3 MicroPython/Pybricks. Teste a conexão com `pybricksdev devices`.

## Blocos disponíveis

A biblioteca visual agora inclui:

| Categoria | Funções |
|---|---|
| Motores | Rodar por tempo, rodar por ângulo, rodar continuamente, parar com freio/inércia/segurar e zerar ângulo |
| Controle | Esperar, repetir quantidade de vezes e repetir para sempre |
| Sensores | Esperar toque, esperar cor, esperar distância e esperar ângulo do giroscópio |
| Bloco EV3 | Esperar botão, luz do bloco e escrever texto na tela |
| Som | Bipe configurável e fala de texto |

Motores usam portas `A` a `D`. Sensores usam portas `S1` a `S4`.

## Layout e F5

Os botões ficam no alto, alinhados à direita. O painel do código fica oculto para deixar mais espaço para os blocos. Pressione **F5** ou clique em **Código Python (F5)** para abrir e fechar o código gerado.

## Mídia local

O Blockly e as texturas do lixo são distribuídos localmente em `web/lib` e `web/media`. Mantenha essas pastas junto de `main.py`.

## Observação sobre os sensores

Os blocos geram código Pybricks para os dispositivos selecionados. Antes de executar, conecte o sensor correto à porta escolhida. O programa pode ficar aguardando indefinidamente nos blocos de espera até que a condição seja atendida.
