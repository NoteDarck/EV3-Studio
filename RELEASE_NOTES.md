# EV3 Studio v0.1.0 — MVP para Linux

Primeira versão pública do **EV3 Studio**, um ambiente de programação visual para o LEGO Mindstorms EV3 no Linux.

O projeto combina o editor de blocos Blockly com geração de código Python para Pybricks e envio de programas ao EV3 por meio do `pybricksdev`.

## Destaques

- Aplicativo desktop para Linux desenvolvido com Python e PySide6.
- Editor visual baseado em Blockly.
- Geração automática de código Python Pybricks.
- Painel de código Python atualizado em tempo real.
- Atalho `F5` para abrir e ocultar o código gerado.
- Botões de controle organizados no canto superior direito.
- Blockly e arquivos de mídia distribuídos localmente, sem dependência do CDN para carregar os blocos.
- Ícone próprio do aplicativo para janela, menu e barra de tarefas.
- Instalador e desinstalador para Linux.

## Categorias de blocos

### Motores

- Executar motor por tempo.
- Executar motor por ângulo.
- Iniciar motor sem tempo definido.
- Definir velocidade.
- Parar motor.
- Parar com freio, marcha lenta ou manter posição.
- Zerar o ângulo do motor.
- Obter graus contados.

### Movimento

- Mover o robô em linha reta.
- Girar o robô.
- Iniciar movimento.
- Parar movimento.
- Configurar motor esquerdo e direito.
- Configurar diâmetro das rodas e distância entre rodas.

### Monitor e display

- Escrever texto na tela do EV3.
- Desenhar linhas.
- Desenhar retângulos.
- Desenhar círculos.
- Limpar a tela.
- Controlar a luz de status do bloco EV3.

### Som

- Tocar beep ou nota.
- Definir frequência e duração.
- Tocar arquivo de som.
- Parar som.
- Falar texto pelo alto-falante do EV3.

### Eventos

- Quando o sensor de toque for acionado.
- Quando uma cor for detectada.
- Quando uma distância for atingida.
- Quando um ângulo do giroscópio for atingido.
- Quando uma mensagem for recebida.
- Quando um temporizador atingir determinado valor.

### Controle, sensores e operadores

- Esperar por segundos.
- Esperar até uma condição.
- Repetir uma quantidade de vezes.
- Repetir para sempre.
- Blocos `se/então` e `se/então/senão`.
- Parar o script.
- Sensor de toque: estado pressionado.
- Sensor de cor: cor atual, luz refletida e luz ambiente.
- Sensor ultrassônico: distância.
- Sensor giroscópio: ângulo e taxa de rotação.
- Temporizador.
- Operações matemáticas.
- Comparações.
- Operadores `E`, `OU` e `NÃO`.
- Valores booleanos.
- Números aleatórios.
- Arredondamento e funções matemáticas.
- Variáveis.
- Listas.
- Procedimentos reutilizáveis em **Meus Blocos**.

## Interface e ferramentas

- Abrir projetos `.ev3proj`.
- Salvar projetos com XML do Blockly, código gerado e configuração do robô.
- Criar novo projeto.
- Detectar dispositivos com `pybricksdev devices`.
- Selecionar conexão Bluetooth ou USB.
- Configurar o nome do EV3.
- Configurar motores esquerdo e direito.
- Configurar medidas do robô.
- Console integrado para acompanhar a execução.
- Botão para executar o programa no EV3.
- Botão para interromper a execução.
- Atalho `Esc` para parar o processo local.
- Menus Arquivo, Executar e Ajuda.

## Instalação rápida

Extraia o projeto e execute:

```bash
chmod +x install.sh uninstall.sh
./install.sh
```

Depois, abra pelo menu de aplicativos ou execute:

```bash
ev3-studio
```

Para remover:

```bash
./uninstall.sh
```

Os arquivos de projeto `.ev3proj` não são removidos pelo desinstalador.

## Requisitos

- Linux 64-bit.
- Python 3.10 ou superior.
- LEGO Mindstorms EV3.
- Firmware EV3 MicroPython/Pybricks instalado no EV3.
- `pybricksdev` instalado pelo instalador do projeto.
- Conexão Bluetooth ou USB compatível.

Antes de executar, teste a conexão com:

```bash
pybricksdev devices
```

## Testes realizados

- Sintaxe Python validada.
- Sintaxe JavaScript do editor validada.
- Sintaxe Bash dos scripts validada.
- Arquivos de mídia do Blockly verificados.
- Ícone SVG verificado.
- Testes automatizados de conversão de movimento executados.
- Validação de projetos e portas executada.
- Integridade do pacote ZIP verificada.

Executar os testes manualmente:

```bash
python3 -m unittest -v test_ev3studio.py
```

## Limitações conhecidas

Esta é uma versão MVP. Algumas funções ainda precisam ser testadas em um EV3 físico com a versão específica do firmware Pybricks utilizada pelo usuário.

- A comunicação Bluetooth e USB depende das permissões e bibliotecas do Linux.
- Os comandos Pybricks podem variar conforme a versão do firmware.
- Eventos visuais estão disponíveis no editor, mas a execução concorrente completa de vários eventos ainda precisa ser aprimorada.
- O movimento de alto nível precisa ser calibrado para cada robô, considerando rodas, engrenagens e distância entre os motores.
- O AppImage ainda não é distribuído nesta versão; a forma recomendada de instalação é o `install.sh`.
- Ainda não existe um instalador nativo `.deb`, `.rpm` ou pacote oficial para repositórios Linux.
- É recomendável testar cada sensor individualmente antes de montar um programa complexo.

## Próximos passos

- Testar todos os blocos em um EV3 físico.
- Melhorar a execução de eventos concorrentes.
- Criar AppImage oficial.
- Adicionar pacotes para Arch, Debian, Ubuntu e Fedora.
- Melhorar mensagens de erro e diagnóstico de conexão.
- Adicionar calibração visual do robô.
- Implementar atualização automática.
- Criar projetos de exemplo para motores, sensores e movimento.
- Adicionar testes de integração com um EV3 conectado.

## Agradecimentos

O projeto utiliza as seguintes tecnologias e projetos de código aberto:

- Python.
- PySide6.
- Blockly.
- Pybricks.
- pybricksdev.

## Licença

Adicione aqui a licença escolhida para o projeto, por exemplo MIT, GPL-3.0 ou outra licença compatível com seus objetivos.
