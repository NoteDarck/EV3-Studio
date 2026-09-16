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

Os botões principais usam ícones e textos curtos: **📂 Abrir**, **💾 Salvar**, **⚙ Robô**, **🔌 EV3**, **🐍 Código**, **🧪 Simular**, **▶ Executar** e **■ Parar**. As categorias do Blockly também usam símbolos para facilitar a identificação visual.

O botão **⚙ Robô** agora é a central de conexão. Nele você escolhe Bluetooth/BLE ou USB, informa o nome do EV3, registra opcionalmente o endereço Bluetooth, detecta dispositivos com `pybricksdev devices` e escolhe um dispositivo encontrado. As informações ficam salvas junto da configuração do robô para serem reutilizadas na próxima execução.

Os atalhos globais são: `Ctrl+N` novo projeto, `Ctrl+O` abrir, `Ctrl+S` salvar, `F5` código, `F6` executar no EV3, `Shift+F6` parar, `F7` simular, `F8` detectar EV3, `Ctrl+R` configurar robô, `F1` tutorial inicial, `Esc` parar e `Ctrl+Q` sair.

O botão **🧪 Simular** abre um simulador físico visual baseado em **PyBullet**, dentro da própria janela do EV3 Studio. Ele mostra um robô 3D com chassis, quatro rodas, chão, gravidade, colisões, atrito e câmera. Comandos `run_time`, `run`, `run_angle` e `wait` são interpretados para movimentar o robô; não é aberto nenhum terminal separado. A simulação é uma prévia educacional e ainda não substitui o teste no EV3 real nem modela todos os sensores, engrenagens e cabos.

O simulador reconhece os motores A, B, C e D para o teste de movimento. No modelo simplificado, qualquer motor de tração selecionado pode movimentar o chassi, portanto o exemplo com `motor_a` também funciona; não é necessário trocar o bloco para B.

O editor carrega apenas o núcleo `blockly.min.js`; o antigo `blocks.min.js` não é carregado porque já registrava menus internos novamente e causava o erro `contextMenu_variableDynamicSetterGetter is already registered`.

Se a instalação do PyBullet precisar compilar o pacote, o Linux deve ter compilador instalado. No Ubuntu/Debian use `sudo apt install build-essential`; no Arch/CachyOS use `sudo pacman -S --needed base-devel`. O `install.sh` agora informa essa solução quando a instalação falha.

O menu **Ajuda** possui dois guias internos que funcionam sem internet: **Tutorial para iniciantes**, com o primeiro programa passo a passo, e **Conhecer o EV3 Studio**, que explica a interface, as categorias, a configuração do robô, o fluxo de geração Python e os atalhos.

Em **Ajuda → Verificar atualizações**, o aplicativo consulta os Releases públicos de [NoteDarck/EV3-Studio](https://github.com/NoteDarck/EV3-Studio), compara a versão instalada e oferece abrir a página de download quando existe uma versão mais nova. A verificação ocorre em segundo plano e não substitui arquivos automaticamente.

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
 tutorials.py         Tutoriais internos do menu Ajuda
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
