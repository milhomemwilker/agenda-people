
"""
ARQUIVO: google_tools.py

OBJETIVO:
Realizar a autenticação com os serviços Google e executar
as operações solicitadas pelo agente de recrutamento.

FUNCIONALIDADES:
1. Autenticar o usuário utilizando OAuth 2.0.
2. Criar entrevistas no Google Calendar.
3. Solicitar links do Google Meet.
4. Registrar candidatos no Google Sheets.

ARQUIVOS UTILIZADOS:
- credentials.json: configurações do cliente OAuth.
- token.json: credenciais autorizadas do usuário.

ATENÇÃO:
O arquivo token.json contém informações sensíveis.
Não publique esses arquivos no GitHub.
"""


# ============================================================
# ETAPA 1: IMPORTAÇÃO DAS BIBLIOTECAS
# ============================================================

# Biblioteca nativa do Python.
#
# Permite interagir com o sistema operacional, por exemplo:
# - Verificar se arquivos existem.
# - Trabalhar com caminhos de arquivos.
# - Ler variáveis de ambiente.
#
# Neste programa, será utilizada para verificar token.json.
import os


# Biblioteca nativa para manipulação de caracteres Unicode.
#
# É utilizada para remover acentos e normalizar
# os nomes das colunas da planilha.
#
# Exemplo:
# "Situação" -> "situacao"
# "Horário"  -> "horario"
import unicodedata


# Biblioteca nativa que gera identificadores UUID.
#
# UUID significa Universally Unique Identifier.
#
# Neste programa, será utilizada para gerar um
# identificador único para a solicitação de criação
# da videoconferência no Google Meet.
#
# IMPORTANTE:
# uuid não cria o link do Meet diretamente.
# O Google Calendar gera a conferência.
import uuid


# Importa a classe datetime.
#
# Permite:
# - Interpretar datas.
# - Trabalhar com horários.
# - Converter formatos de datas.
#
# Exemplo:
# 2026-11-10T14:00:00 -> 10/11/2026 14:00
from datetime import datetime


# Importa a exceção RefreshError.
#
# Essa exceção pode ocorrer quando o Google não consegue
# renovar um token de autenticação.
#
# Exemplo:
# Um token foi revogado ou deixou de ser válido.
from google.auth.exceptions import RefreshError


# Importa Request.
#
# É utilizada para enviar a requisição necessária
# à renovação das credenciais OAuth.
from google.auth.transport.requests import Request


# Importa Credentials.
#
# Representa as credenciais OAuth autorizadas.
#
# Permite:
# - Carregar credenciais salvas.
# - Verificar validade.
# - Renovar tokens quando possível.
from google.oauth2.credentials import Credentials


# Importa InstalledAppFlow.
#
# Responsável por iniciar o processo OAuth 2.0
# para aplicações instaladas.
#
# Pode abrir o navegador para o usuário
# autorizar o acesso à sua conta Google.
from google_auth_oauthlib.flow import InstalledAppFlow


# Importa build.
#
# Cria objetos de serviço para acessar APIs Google.
#
# Exemplos:
# build("calendar", "v3", credentials=...)
# build("sheets", "v4", credentials=...)
from googleapiclient.discovery import build


# ============================================================
# ETAPA 2: DEFINIÇÃO DOS ESCOPOS DE AUTENTICAÇÃO
# ============================================================

# SCOPES é uma lista de permissões solicitadas ao usuário.
#
# Em OAuth 2.0, um escopo determina quais recursos
# uma aplicação está autorizada a acessar.
#
# O Google apresenta essas permissões ao usuário
# durante o processo de autorização.
SCOPES = [

    # Permite gerenciar eventos do Google Calendar.
    #
    # Neste projeto, será utilizado para criar
    # entrevistas e solicitar videoconferências.
    'https://www.googleapis.com/auth/calendar.events',

    # Permite ler e modificar planilhas Google Sheets.
    #
    # ATENÇÃO:
    # Este escopo é amplo e deve ser protegido adequadamente.
    'https://www.googleapis.com/auth/spreadsheets',

]


# ============================================================
# ETAPA 2.1: MAPEAMENTO DAS COLUNAS DA PLANILHA
# ============================================================

# Dicionário que relaciona os campos utilizados no Python
# aos possíveis nomes das colunas no Google Sheets.
#
# Exemplo:
# O programa aceita tanto "Nome" quanto "Nome Candidato".
#
# A estrutura possui:
#
# CHAVE:
# Nome interno do campo utilizado pelo Python.
#
# VALOR:
# Conjunto (set) contendo os nomes aceitos.
#
# OBSERVAÇÃO:
# Esses valores não são IDs das colunas.
# São nomes alternativos dos cabeçalhos.
CAMPOS_DA_PLANILHA = {

    # Campo interno: nome.
    # Cabeçalhos reconhecidos:
    # "Nome" e "Nome Candidato".
    "nome": {"nome", "nomecandidato"},

    # Campo interno: vaga.
    # Cabeçalhos reconhecidos:
    # "Vaga" e "Cargo".
    "vaga": {"vaga", "cargo"},

    # Campo interno: data.
    # Cabeçalhos reconhecidos:
    # "Data" e "Data Entrevista".
    "data": {"data", "dataentrevista"},

    # Campo interno: hora.
    # Cabeçalhos reconhecidos:
    # "Hora", "Horário" e "Horário Entrevista".
    "hora": {"hora", "horario", "horarioentrevista"},

    # Campo interno: email.
    # Cabeçalhos reconhecidos:
    # "Email" e "Email Candidato".
    "email": {"email", "emailcandidato"},

    # Campo interno: status.
    # Cabeçalhos reconhecidos:
    # "Status" e "Situação".
    "status": {"status", "situacao"},
}


# ============================================================
# ETAPA 3: AUTENTICAÇÃO COM OS SERVIÇOS GOOGLE
# ============================================================

def autenticar_google():
    """
    Realiza a autenticação OAuth 2.0.

    FLUXO:
    1. Verifica se existe token.json.
    2. Carrega as credenciais existentes.
    3. Tenta renovar o token quando necessário.
    4. Solicita nova autorização, se necessário.
    5. Salva as credenciais em token.json.
    6. Retorna as credenciais autorizadas.
    """

    # Inicialmente, não existem credenciais carregadas.
    #
    # None representa ausência de valor.
    credentials = None

    # Verifica se token.json existe no diretório
    # de trabalho atual do programa.
    #
    # os.path.exists():
    # Retorna True quando o caminho existe.
    if os.path.exists('token.json'):

        # Carrega as credenciais previamente autorizadas.
        #
        # O arquivo contém dados utilizados para
        # autenticar o usuário sem repetir o login
        # em todas as execuções.
        credentials = Credentials.from_authorized_user_file(
            'token.json',
            SCOPES
        )

    # Verifica três condições:
    #
    # 1. credentials:
    #    Existem credenciais carregadas.
    #
    # 2. credentials.expired:
    #    O token de acesso está expirado.
    #
    # 3. credentials.refresh_token:
    #    Existe um token que permite tentar a renovação.
    #
    # O operador and exige que todas as condições sejam
    # verdadeiras para executar o bloco.
    if (
        credentials
        and credentials.expired
        and credentials.refresh_token
    ):

        # try:
        # Inicia um bloco de código que pode gerar exceções.
        try:

            # Solicita a renovação das credenciais.
            #
            # Request() fornece o transporte HTTP
            # utilizado durante a renovação.
            credentials.refresh(Request())

        # Captura erros específicos de renovação OAuth.
        #
        # A variável erro contém informações da exceção.
        except RefreshError as erro:

            # Verifica se a mensagem contém invalid_grant.
            #
            # Esse erro pode indicar um token inválido,
            # revogado ou expirado de forma irrecuperável.
            if "invalid_grant" not in str(erro):

                # Repassa a exceção para quem chamou
                # esta função.
                raise

            # Descarta as credenciais quando o erro
            # identificado é invalid_grant.
            #
            # Assim, o programa poderá solicitar
            # uma nova autorização.
            credentials = None

    # Verifica se:
    # - Não existem credenciais; OU
    # - As credenciais não estão válidas.
    #
    # O operador or exige apenas uma condição verdadeira.
    if not credentials or not credentials.valid:

        # Cria o fluxo OAuth utilizando credentials.json.
        #
        # Esse arquivo é obtido na configuração
        # de credenciais OAuth no Google Cloud.
        fluxo = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            SCOPES
        )

        # Inicia um servidor HTTP local temporário.
        #
        # O navegador permite ao usuário autorizar
        # as permissões solicitadas.
        #
        # port=0:
        # Solicita ao sistema operacional uma porta
        # disponível automaticamente.
        credentials = fluxo.run_local_server(port=0)

    # Abre token.json em modo de escrita.
    #
    # "w":
    # Cria ou sobrescreve o arquivo.
    #
    # with:
    # Garante o fechamento do arquivo ao sair do bloco.
    with open('token.json', 'w') as token:

        # Converte as credenciais para JSON e
        # grava o resultado no arquivo.
        token.write(credentials.to_json())

    # Retorna o objeto Credentials.
    #
    # Esse objeto será utilizado para criar
    # os clientes Google Calendar e Google Sheets.
    return credentials


# ============================================================
# ETAPA 4: AGENDAMENTO DE ENTREVISTAS COM GOOGLE MEET
# ============================================================

def agendar_entrevista_com_meet(
    nome_candidato,
    email_candidato,
    data_hora_inicio,
    data_hora_fim,
):
    """
    Cria um evento no Google Calendar e solicita
    uma videoconferência do Google Meet.

    PARÂMETROS:
    nome_candidato:
        Nome do candidato entrevistado.

    email_candidato:
        Endereço de e-mail do candidato.

    data_hora_inicio:
        Início da entrevista em ISO 8601.

    data_hora_fim:
        Término da entrevista em ISO 8601.

    RETORNO:
        Link do Google Meet, quando disponibilizado.
    """

    # Cria o cliente da API Google Calendar.
    #
    # calendar:
    # Nome da API.
    #
    # v3:
    # Versão da API utilizada.
    #
    # credentials:
    # Credenciais retornadas pela autenticação OAuth.
    servico = build(
        'calendar',
        'v3',
        credentials=autenticar_google()
    )

    # Cria um dicionário Python contendo os dados
    # do evento que será enviado ao Google Calendar.
    evento = {

        # summary:
        # Título que aparecerá no calendário.
        #
        # f-string:
        # Permite inserir variáveis dentro de uma string.
        'summary': f'Entrevista com {nome_candidato}',

        # description:
        # Descrição do evento.
        'description': (
            "Entrevista de alinhamento com o time da People."
        ),

        # start:
        # Define quando a entrevista começará.
        "start": {

            # Data e hora de início.
            "dateTime": data_hora_inicio,

            # Fuso horário utilizado no evento.
            "timeZone": "America/Sao_Paulo",
        },

        # end:
        # Define quando a entrevista terminará.
        "end": {

            # Data e hora de término.
            "dateTime": data_hora_fim,

            # Mesmo fuso horário do início.
            "timeZone": "America/Sao_Paulo",
        },

        # attendees:
        # Lista de convidados do evento.
        #
        # Cada convidado é representado por
        # um dicionário com o endereço de e-mail.
        "attendees": [

            # Candidato convidado para a entrevista.
            {"email": email_candidato},
        ],

        # conferenceData:
        # Configura a solicitação de videoconferência.
        "conferenceData": {

            # createRequest:
            # Solicita a criação de uma conferência.
            "createRequest": {

                # Gera um UUID para identificar
                # esta solicitação de criação.
                #
                # uuid.uuid4():
                # Gera um identificador aleatório.
                #
                # str():
                # Converte o UUID para texto.
                #
                # O Google utiliza o requestId para
                # identificar a solicitação e evitar
                # processamento duplicado da mesma requisição.
                "requestId": str(uuid.uuid4()),

                # Define o tipo de conferência desejado.
                #
                # hangoutsMeet:
                # Identifica o Google Meet.
                "conferenceSolutionKey": {
                    "type": "hangoutsMeet"
                },
            },
        },
    }

    # Envia uma requisição para criar o evento.
    #
    # servico.events():
    # Acessa o recurso de eventos do Calendar.
    #
    # insert():
    # Solicita a criação de um novo evento.
    #
    # execute():
    # Executa a requisição HTTP.
    evento_criado = servico.events().insert(

        # primary:
        # Utiliza o calendário principal da conta
        # autenticada.
        calendarId='primary',

        # Envia o dicionário com os dados do evento.
        body=evento,

        # Habilita o processamento dos dados
        # de conferência do evento.
        conferenceDataVersion=1,

        # Solicita o envio de notificações
        # aos participantes, quando aplicável.
        sendUpdates='all',

    ).execute()

    # Procura a propriedade hangoutLink no evento criado.
    #
    # get():
    # Retorna o valor da chave, se existir.
    #
    # Se a chave não existir, retorna None.
    #
    # OBSERVAÇÃO:
    # A criação da conferência pode ser assíncrona.
    # O link pode ainda não estar disponível
    # na resposta inicial da API.
    link_meet = evento_criado.get('hangoutLink')

    # Devolve o link do Google Meet.
    #
    # Exemplo de formato:
    # https://meet.google.com/xxx-yyyy-zzz
    #
    # Se o link não estiver disponível,
    # a função retornará None.
    return link_meet


# ============================================================
# ETAPA 5: REGISTRO DE CANDIDATOS NO GOOGLE SHEETS
# ============================================================

def registrar_candidato_na_planilha(
    id_planilha,
    nome,
    email,
    vaga,
    status,
    data_hora_inicio=None,
    data_hora_fim=None
):
    """
    Registra os dados de um candidato no Google Sheets.

    PARÂMETROS:
    id_planilha:
        Identificador da planilha Google.

    nome:
        Nome do candidato.

    email:
        E-mail do candidato.

    vaga:
        Vaga de interesse.

    status:
        Situação no processo seletivo.

    data_hora_inicio:
        Início da entrevista (opcional).

    data_hora_fim:
        Término da entrevista (opcional).

    FUNCIONAMENTO:
    1. Conecta ao Google Sheets.
    2. Identifica a aba desejada.
    3. Lê o cabeçalho.
    4. Identifica as colunas.
    5. Organiza os dados.
    6. Adiciona uma nova linha.
    """

    # Cria o cliente da API Google Sheets.
    #
    # sheets:
    # Nome da API.
    #
    # v4:
    # Versão utilizada.
    servico = build(
        'sheets',
        'v4',
        credentials=autenticar_google()
    )

    # Consulta os metadados da planilha.
    #
    # spreadsheets().get():
    # Obtém informações sobre a planilha.
    #
    # fields:
    # Limita os campos retornados pela API.
    #
    # Aqui, são solicitados:
    # - title: nome de cada aba.
    # - sheetId: identificador numérico da aba.
    planilha = servico.spreadsheets().get(

        spreadsheetId=id_planilha,

        fields="sheets(properties(title,sheetId))",

    ).execute()

    # Procura a aba cujo sheetId seja igual a zero.
    #
    # ATENÇÃO:
    # Nem toda planilha possui uma aba com sheetId=0.
    #
    # next():
    # Retorna o primeiro elemento encontrado.
    #
    # Expressão geradora:
    # Percorre as abas e filtra pelo identificador.
    #
    # None:
    # Valor utilizado caso nenhuma aba corresponda.
    aba = next(
        (
            item["properties"]
            for item in planilha.get("sheets", [])
            if item["properties"].get("sheetId") == 0
        ),
        None,
    )

    # Verifica se a aba foi encontrada.
    if not aba:

        # Interrompe a execução com uma exceção.
        #
        # ValueError:
        # Indica que um valor esperado não foi encontrado.
        raise ValueError(
            "Aba da planilha não encontrada na planilha."
        )

    # Recupera o nome da aba.
    #
    # replace("'", "''"):
    # Duplica aspas simples para permitir seu uso
    # no nome da aba dentro de uma referência A1.
    titulo_aba = aba["title"].replace("'", "''")

    # Define o intervalo de leitura.
    #
    # A1:Z1:
    # Primeira linha, da coluna A até a coluna Z.
    #
    # Esta linha deverá conter os nomes das colunas.
    intervalo = f"'{titulo_aba}'!A1:Z1"

    # Consulta os valores existentes no intervalo.
    resposta = servico.spreadsheets().values().get(

        spreadsheetId=id_planilha,

        range=intervalo,

    ).execute()

    # Recupera as linhas retornadas.
    #
    # Se a API não retornar "values",
    # utiliza uma lista vazia.
    linhas = resposta.get("values", [])

    # Obtém a primeira linha, correspondente ao cabeçalho.
    #
    # Se não houver linhas, utiliza uma lista vazia.
    cabecalho = linhas[0] if linhas else []

    # Dicionário que armazenará a posição
    # de cada coluna reconhecida.
    #
    # Exemplo:
    # {
    #     "nome": 0,
    #     "email": 1,
    #     "vaga": 2
    # }
    colunas = {}

    # Percorre os títulos das colunas.
    #
    # enumerate():
    # Retorna o índice e o valor de cada elemento.
    #
    # Exemplo:
    # 0, "Nome"
    # 1, "Email"
    # 2, "Vaga"
    for indice, titulo in enumerate(cabecalho):

        # Converte o título para string e
        # decompõe os caracteres Unicode.
        normalizado = unicodedata.normalize(
            "NFKD",
            str(titulo)
        )

        # Remove:
        # - Marcas de acentuação.
        # - Espaços.
        # - Caracteres que não sejam alfanuméricos.
        #
        # Depois converte o resultado para minúsculas.
        #
        # Exemplo:
        # "Nome Candidato" -> "nomecandidato"
        # "Situação"       -> "situacao"
        normalizado = "".join(

            caractere
            for caractere in normalizado

            if (
                not unicodedata.combining(caractere)
                and caractere.isalnum()
            )

        ).lower()

        # Percorre os campos e seus nomes alternativos.
        #
        # items():
        # Retorna pares chave/valor do dicionário.
        for campo, nomes in CAMPOS_DA_PLANILHA.items():

            # Verifica se o título normalizado
            # corresponde a um nome aceito.
            if normalizado in nomes:

                # Armazena o índice da coluna encontrada.
                #
                # Exemplo:
                # colunas["email"] = 1
                colunas[campo] = indice

    # Verifica se alguma coluna foi reconhecida.
    if not colunas:

        # Interrompe o cadastro caso o cabeçalho
        # não possua nenhuma coluna reconhecida.
        raise ValueError(
            "Nenhuma coluna reconhecida "
            "no cabeçalho da planilha."
        )

    # Organiza os dados do candidato em um dicionário.
    #
    # As chaves correspondem aos campos internos
    # definidos em CAMPOS_DA_PLANILHA.
    dados = {
        "nome": nome,
        "email": email,
        "vaga": vaga,
        "status": status,
    }

    # Verifica se uma data de início foi informada.
    if data_hora_inicio:

        # Inicia tratamento de possíveis erros
        # na conversão das datas.
        try:

            # Converte a string ISO 8601
            # para um objeto datetime.
            inicio = datetime.fromisoformat(
                data_hora_inicio
            )

            # Formata a data.
            #
            # %d: dia
            # %m: mês
            # %Y: ano com quatro dígitos
            # %H: hora no formato 24h
            # %M: minutos
            #
            # OBSERVAÇÃO:
            # Aqui a coluna "data" recebe
            # tanto a data quanto a hora.
            dados["data"] = inicio.strftime(
                "%d/%m/%Y %H:%M"
            )

            # Inicialmente, armazena apenas a hora de início.
            dados["hora"] = inicio.strftime("%H:%M")

            # Verifica se existe uma coluna de horário.
            if "hora" in colunas:

                # Formata a hora de início.
                hora = inicio.strftime("%H:%M")

                # Verifica se a hora de término foi informada.
                if data_hora_fim:

                    # Converte o término para datetime.
                    fim = datetime.fromisoformat(
                        data_hora_fim
                    )

                    # Concatena os horários.
                    #
                    # Exemplo:
                    # "14:00 - 15:00"
                    hora += f" - {fim.strftime('%H:%M')}"

                # Atualiza o campo hora.
                dados["hora"] = hora

        # Captura erros de conversão de data e hora.
        except ValueError:

            # Interrompe o registro com uma mensagem
            # explicando o formato esperado.
            raise ValueError(
                "Formato de data/hora inválido. "
                "Use o formato ISO 8601 "
                "(YYYY-MM-DDTHH:MM:SS)."
            )

    # --------------------------------------------------------
    # PREPARAÇÃO DOS VALORES PARA INSERÇÃO
    # --------------------------------------------------------

    # Cria uma lista com células inicialmente vazias.
    #
    # max(colunas.values()):
    # Identifica o maior índice de coluna encontrado.
    #
    # +1:
    # Ajusta a quantidade porque os índices começam em zero.
    #
    # [""] * quantidade:
    # Cria uma lista com a quantidade informada
    # de strings vazias.
    #
    # Exemplo:
    # ["", "", "", ""]
    valores = [""] * (max(colunas.values()) + 1)

    # Percorre os dados do candidato.
    #
    # items():
    # Retorna cada campo e seu respectivo valor.
    for campo, valor in dados.items():

        # Verifica se o campo possui uma coluna
        # correspondente no Google Sheets.
        if campo in colunas:

            # Insere o valor na posição correta.
            #
            # Exemplo:
            # valores[0] = "João Silva"
            # valores[1] = "joao@example.com"
            valores[colunas[campo]] = valor

    # --------------------------------------------------------
    # INSERÇÃO DOS DADOS NO GOOGLE SHEETS
    # --------------------------------------------------------

    # Adiciona uma linha à planilha.
    #
    # values().append():
    # Solicita a inserção de novos valores
    # após a tabela identificada pela API.
    resultado = servico.spreadsheets().values().append(

        # Identificador da planilha de destino.
        spreadsheetId=id_planilha,

        # Intervalo utilizado para localizar a tabela.
        range=f"'{titulo_aba}'!A1:Z1",

        # USER_ENTERED:
        # O Google Sheets interpreta os valores como
        # se fossem digitados por um usuário.
        #
        # Isso pode converter datas e números
        # e interpretar fórmulas.
        valueInputOption="USER_ENTERED",

        # INSERT_ROWS:
        # Solicita a inserção de linhas para
        # acomodar os novos valores.
        insertDataOption="INSERT_ROWS",

        # Corpo da requisição.
        #
        # "values" deve receber uma lista de linhas.
        #
        # Por isso utilizamos [valores]:
        # É uma lista contendo a linha preparada.
        body={
            "values": [valores]
        },

    ).execute()

    # Retorna a resposta da API Google Sheets.
    #
    # Ela pode conter:
    # - Intervalo atualizado.
    # - Número de linhas atualizadas.
    # - Número de células atualizadas.
    #
    # O resultado não contém necessariamente
    # todos os dados cadastrados.
    return resultado
