# EV3 Studio

Ambiente visual para programar o LEGO Mindstorms EV3 no Linux com Blockly, Python e Pybricks.

## Instalação

```bash
chmod +x install.sh uninstall.sh
./install.sh
```

O instalador cria o ambiente virtual, instala as dependências, copia o aplicativo para `~/.local/share/ev3-studio`, cria o comando `~/.local/bin/ev3-studio`, o ícone e o atalho do menu. Para remover:

```bash
./uninstall.sh
```

Seus arquivos `.ev3proj` não são removidos.

## Recursos implementados

O aplicativo possui categorias de Motores, Movimento, Monitor/Display, Som, Eventos, Controle, Sensores, Operadores, Variáveis, Listas e Meus Blocos. O código é atualizado em tempo real e abre com **F5**. Os botões ficam no alto à direita.

A configuração do robô permite escolher motores esquerdo/direito, diâmetro da roda, distância entre rodas, Bluetooth/USB e nome do EV3. Esses dados ficam em `~/.config/ev3-studio/robot.json`.

O menu Executar possui detecção de dispositivos, execução e parada. O atalho `Esc` interrompe o processo local do `pybricksdev`. O console mostra a saída do envio. Antes de executar ou salvar, o validador verifica programa vazio e portas inválidas.

Projetos guardam Blockly, código gerado e configuração do robô no arquivo `.ev3proj`.

## Testes

Execute:

```bash
python3 -m unittest -v test_ev3studio.py
```

Também é possível validar a sintaxe:

```bash
python3 -m py_compile main.py ev3studio_config.py validator.py
```

## Firmware e conexão

O EV3 precisa usar EV3 MicroPython/Pybricks. Teste a conexão com:

```bash
pybricksdev devices
```

A aplicação chama `pybricksdev run ble` ou `pybricksdev run usb` conforme a configuração. Sensores devem estar conectados às portas selecionadas. Eventos visuais e blocos de procedimentos são representados no Blockly; a execução concorrente completa de múltiplos eventos requer uma futura camada de tarefas no programa Pybricks.

## Estrutura

```text
main.py              Aplicativo PySide6
web/blockly.html     Blocos e gerador Python
web/lib              Blockly local
web/media            Mídias e textura do lixo
assets               Ícone SVG
ev3studio_config.py  Configuração e calibração
validator.py         Validação antes do envio
test_ev3studio.py    Testes automatizados
install.sh           Instalação
uninstall.sh         Desinstalação
```
