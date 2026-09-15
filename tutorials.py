BEGINNER_TUTORIAL = '''<h1>EV3 Studio — Tutorial para iniciantes</h1>
<p>Este tutorial mostra como criar seu primeiro programa e executá-lo no LEGO Mindstorms EV3.</p>
<h2>1. Prepare o EV3</h2>
<p>Instale o firmware EV3 MicroPython/Pybricks no cartão microSD, coloque-o no EV3 e ligue o bloco. Conecte o motor à porta A e confirme a conexão no computador.</p>
<h2>2. Detecte o robô</h2>
<p>No EV3 Studio, clique em <b>Detectar EV3</b>. Se o robô aparecer, a comunicação está pronta. Se não aparecer, verifique Bluetooth/USB, se o EV3 está ligado e execute <code>pybricksdev devices</code> no terminal.</p>
<h2>3. Monte o programa</h2>
<p>Abra a categoria <b>EV3 - Início</b> e arraste o bloco INÍCIO. Em <b>Motores</b>, arraste MOTOR POR TEMPO, escolha a porta A, velocidade 50% e tempo 2 segundos. Conecte PARAR MOTOR depois dele.</p>
<h2>4. Veja o Python</h2>
<p>Pressione <b>F5</b> para mostrar o código Python Pybricks. O código muda automaticamente quando os blocos são alterados.</p>
<h2>5. Execute</h2>
<p>Clique em <b>Executar</b>. O motor deve funcionar por dois segundos. Para interromper o envio local, clique em <b>Parar</b> ou pressione <b>Esc</b>.</p>
<h2>6. Salve seu projeto</h2>
<p>Clique em <b>Salvar projeto</b> e escolha um nome com a extensão <code>.ev3proj</code>. Para continuar depois, use <b>Abrir projeto</b>.</p>
<h2>Cuidados</h2>
<p>Mantenha o robô apoiado e longe das bordas da mesa. Confira a porta do motor antes de executar. Comece com velocidades baixas.</p>'''

ABOUT_TUTORIAL = '''<h1>Conhecendo o EV3 Studio</h1>
<p>O EV3 Studio é um ambiente visual para criar programas para o LEGO Mindstorms EV3. Os blocos são convertidos para Python e enviados ao robô pelo Pybricks.</p>
<h2>Área de blocos</h2>
<p>À esquerda fica o editor Blockly. As categorias agrupam comandos: Motores, Movimento, Monitor/Display, Som, Eventos, Controle, Sensores, Operadores, Variáveis, Listas e Meus Blocos.</p>
<h2>Barra superior</h2>
<p><b>Abrir projeto</b> carrega um arquivo; <b>Salvar projeto</b> guarda o programa; <b>Configurar robô</b> define motores e medidas; <b>Detectar EV3</b> procura dispositivos; <b>Código Python (F5)</b> abre o código; <b>Executar</b> envia ao EV3; <b>Parar</b> interrompe o processo.</p>
<h2>Código Python</h2>
<p>O painel mostra o código gerado. Ele é uma ferramenta de aprendizagem: cada bloco visual corresponde a uma ou mais instruções Python Pybricks.</p>
<h2>Configuração do robô</h2>
<p>Defina o motor esquerdo, o motor direito, o diâmetro das rodas, a distância entre as rodas, o tipo de conexão e o nome do EV3. A calibração é necessária para o movimento em linha reta e os giros.</p>
<h2>Arquivos de projeto</h2>
<p>Um projeto <code>.ev3proj</code> guarda o XML dos blocos, o código gerado e a configuração do robô. Ele pode ser versionado no GitHub.</p>
<h2>Fluxo de execução</h2>
<p>O fluxo é: <b>blocos → XML → Python Pybricks → arquivo temporário → pybricksdev → EV3</b>. O EV3 precisa estar com firmware compatível.</p>
<h2>Atalhos</h2>
<p><b>F5</b> mostra ou oculta o Python. <b>Esc</b> tenta interromper a execução local.</p>'''
