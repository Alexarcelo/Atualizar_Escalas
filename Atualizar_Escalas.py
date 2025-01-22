import streamlit as st
import mysql.connector
import decimal
import pandas as pd
import requests
import gspread 
from google.oauth2 import service_account

def gerar_df_phoenix(vw_name, base_luck):

    config = {
        'user': 'user_automation_jpa',
        'password': 'luck_jpa_2024',
        'host': 'comeia.cixat7j68g0n.us-east-1.rds.amazonaws.com',
        'database': base_luck
        }

    conexao = mysql.connector.connect(**config)
    cursor = conexao.cursor()
    request_name = f'SELECT * FROM {vw_name}'
    cursor.execute(request_name)
    resultado = cursor.fetchall()
    cabecalho = [desc[0] for desc in cursor.description]
    cursor.close()
    conexao.close()
    df = pd.DataFrame(resultado, columns=cabecalho)
    df = df.applymap(lambda x: float(x) if isinstance(x, decimal.Decimal) else x)

    return df

def puxar_aba_simples(id_gsheet, nome_aba, nome_df):

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(id_gsheet)
    
    sheet = spreadsheet.worksheet(nome_aba)

    sheet_data = sheet.get_all_values()

    st.session_state[nome_df] = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

def gerar_listas_de_nao_cadastrados(df, coluna):

    if coluna=='Guia':

        lista_a_atualizar = st.session_state.df_escalas_atualizar[st.session_state.df_escalas_atualizar[coluna]!=''][coluna].unique().tolist()

    else:

        lista_a_atualizar = st.session_state.df_escalas_atualizar[coluna].unique().tolist()

    lista_phoenix = st.session_state[df][coluna].unique().tolist()

    lista_nao_cadastrados = list(set(lista_a_atualizar) - set(lista_phoenix))

    return lista_nao_cadastrados

def gerar_mensagens_de_nao_cadastrados(lista_escalas_nao_cadastrados, lista_veiculos_nao_cadastrados, lista_motoristas_nao_cadastrados, lista_guias_nao_cadastrados):

    if len(lista_escalas_nao_cadastrados)>0:

        st.error(f'As escalas {", ".join(lista_escalas_nao_cadastrados)} não existem no Phoenix. Precisa ajustar a nomenclatura na planilha e tentar novamente')

    if len(lista_veiculos_nao_cadastrados)>0:

        st.error(f'Os veículos {", ".join(lista_veiculos_nao_cadastrados)} não existem no Phoenix. Precisa ajustar a nomenclatura na planilha e tentar novamente')

    if len(lista_motoristas_nao_cadastrados)>0:

        st.error(f'Os motoristas {", ".join(lista_motoristas_nao_cadastrados)} não existem no Phoenix. Precisa ajustar a nomenclatura na planilha e tentar novamente')

    if len(lista_guias_nao_cadastrados)>0:

        st.error(f'Os guias {", ".join(lista_guias_nao_cadastrados)} não existem no Phoenix. Precisa ajustar a nomenclatura na planilha e tentar novamente')

    if len(lista_escalas_nao_cadastrados)>0 or len(lista_veiculos_nao_cadastrados)>0 or len(lista_motoristas_nao_cadastrados)>0 or len(lista_guias_nao_cadastrados)>0:

        st.stop()

def verificar_cadastros_veic_mot_guias():

    lista_escalas_nao_cadastrados = gerar_listas_de_nao_cadastrados('df_escalas', 'Escala')

    lista_veiculos_nao_cadastrados = gerar_listas_de_nao_cadastrados('df_veiculos', 'Veiculo')

    lista_motoristas_nao_cadastrados = gerar_listas_de_nao_cadastrados('df_motoristas', 'Motorista')

    lista_guias_nao_cadastrados = gerar_listas_de_nao_cadastrados('df_guias', 'Guia')

    gerar_mensagens_de_nao_cadastrados(lista_escalas_nao_cadastrados, lista_veiculos_nao_cadastrados, lista_motoristas_nao_cadastrados, lista_guias_nao_cadastrados)

def update_scale(payload):

    try:
        response = requests.post(st.session_state.base_url_post, json=payload, verify=False)
        response.raise_for_status()
        return 'Escala atualizada com sucesso!'
    except requests.RequestException as e:
        st.error(f"Ocorreu um erro: {e}")
        return 'Erro ao atualizar a escala'

def get_novo_codigo(reserve_service_id):
    novo_codigo = st.session_state.df_escalas[
        (st.session_state.df_escalas['ID Servico'] == reserve_service_id) 
    ]
    if novo_codigo.empty:
        return 'Escala não encontrada'
    return novo_codigo['Escala'].values[0]

def inserir_novas_escalas_drive(df_itens_faltantes, id_gsheet, nome_aba):

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)
    
    spreadsheet = client.open_by_key(id_gsheet)

    sheet = spreadsheet.worksheet(nome_aba)

    sheet.batch_clear(["A2:Z100000"])

    data = df_itens_faltantes.values.tolist()
    sheet.update('A2', data)

def puxar_dados_phoenix():

    st.session_state.df_escalas = gerar_df_phoenix('vw_scales', st.session_state.base_luck)

    st.session_state.df_motoristas = gerar_df_phoenix('vw_motoristas', 'test_phoenix_joao_pessoa')

    st.session_state.df_motoristas = st.session_state.df_motoristas.rename(columns={'nickname': 'Motorista'})

    st.session_state.df_guias = gerar_df_phoenix('vw_guias', 'test_phoenix_joao_pessoa')

    st.session_state.df_guias = st.session_state.df_guias.rename(columns={'nickname': 'Guia'})

    st.session_state.df_veiculos = gerar_df_phoenix('vw_veiculos', st.session_state.base_luck)

    st.session_state.df_veiculos = st.session_state.df_veiculos.rename(columns={'name': 'Veiculo'})

st.set_page_config(layout='wide')

if not 'base_luck' in st.session_state:
    
    base_fonte = st.query_params["base_luck"]

    if base_fonte=='mcz':

        st.session_state.base_luck = 'test_phoenix_maceio'

        st.session_state.base_url_post = 'https://drivermaceio.phoenix.comeialabs.com/scale/roadmap/allocate'

        st.session_state.id_gsheet = '1CYBP8I51Y0fvICG0bDEkZp7uSkM7aKPBT2FTD352pdk'

    elif base_fonte=='rec':

        st.session_state.base_luck = 'test_phoenix_recife'
        
        st.session_state.base_url_post = 'https://driverrecife.phoenix.comeialabs.com/scale/roadmap/allocate'
        
        st.session_state.id_gsheet = '1tK_tUWk5gDFcv0vKHviWYax0r3njkLldwAXx6AFxUhs'

    elif base_fonte=='ssa':

        st.session_state.base_luck = 'test_phoenix_salvador'
        
        st.session_state.base_url_post = 'https://driversalvador.phoenix.comeialabs.com/scale/roadmap/allocate'
        
        st.session_state.id_gsheet = '1C-3dkL0ysXn8P1jEaCwhhHHJ0HCiNDgLUJf9q4hlm7I'

    elif base_fonte=='aju':

        st.session_state.base_luck = 'test_phoenix_aracaju'
        
        st.session_state.base_url_post = 'https://driveraracaju.phoenix.comeialabs.com/scale/roadmap/allocate'
        
        st.session_state.id_gsheet = '1v_-017SkNT3nGMLYcJukLhhSUla4jJdPvb6afn1onzI'

    elif base_fonte=='fen':

        st.session_state.base_luck = 'test_phoenix_noronha'
        
        st.session_state.base_url_post = 'https://drivernoronha.phoenix.comeialabs.com/scale/roadmap/allocate'
        
        st.session_state.id_gsheet = '1xqeRTQP1kkByMxyEpaq_YqMmwxAEABbJQF06y9u4QI0'

    elif base_fonte=='nat':

        st.session_state.base_luck = 'test_phoenix_natal'
        
        st.session_state.base_url_post = 'https://drivernatal.phoenix.comeialabs.com/scale/roadmap/allocate'
        
        st.session_state.id_gsheet = '1_WXMT5cxessNWmvBc1mpoRIfNMNIvnqwuXyHSScdEZY'

    elif base_fonte=='jpa':

        st.session_state.base_luck = 'test_phoenix_joao_pessoa'
        
        st.session_state.base_url_post = 'https://driverjoao_pessoa.phoenix.comeialabs.com/scale/roadmap/allocate'
        
        st.session_state.id_gsheet = '1gBUAuQHuA1bmLD9F_TAt3ya6V4w3SuXRNyGZN3eGwrA'

if not 'df_escalas' in st.session_state:

    with st.spinner('Puxando dados do Phoenix...'):

        puxar_dados_phoenix()

row0 = st.columns(1)

st.title('Atualizar Escalas')

st.divider()

row1 = st.columns(3)

with row1[1]:

    atualizar_phoenix = st.button('Atualizar Dados Phoenix')

if atualizar_phoenix:

    with st.spinner('Puxando dados do Phoenix...'):

        puxar_dados_phoenix()

with row1[0]:

    atualizar_escalas = st.button('Atualizar Escalas')

if atualizar_escalas:

    with st.spinner('Puxando dados do Google Drive...'):

        puxar_aba_simples(st.session_state.id_gsheet, 'Atualizar Escalas', 'df_escalas_atualizar')

        st.session_state.df_escalas_atualizar = st.session_state.df_escalas_atualizar[st.session_state.df_escalas_atualizar['Escala Nova']==''].reset_index(drop=True)

        if len(st.session_state.df_escalas_atualizar)==0:

            st.error('Não existem escalas pra atualizar')

            st.stop()

        verificar_cadastros_veic_mot_guias()

    df_escalas_a_atualizar = st.session_state.df_escalas[st.session_state.df_escalas['Escala'].isin(st.session_state.df_escalas_atualizar['Escala'].unique())].reset_index(drop=True)

    escalas_para_atualizar = []

    for index in range(len(st.session_state.df_escalas_atualizar)):

        escala = st.session_state.df_escalas_atualizar.at[index, 'Escala']

        veiculo = st.session_state.df_escalas_atualizar.at[index, 'Veiculo']

        motorista = st.session_state.df_escalas_atualizar.at[index, 'Motorista']

        guia = st.session_state.df_escalas_atualizar.at[index, 'Guia']

        df_ref = df_escalas_a_atualizar[df_escalas_a_atualizar['Escala']==escala]

        id_servicos = [int(item) for item in df_ref['ID Servico'].tolist()]

        date_str = df_ref['Data da Escala'].values[0].strftime('%Y-%m-%d')

        id_veiculo = int(st.session_state.df_veiculos[st.session_state.df_veiculos['Veiculo']==veiculo]['id'].iloc[0])

        id_motorista = int(st.session_state.df_motoristas[st.session_state.df_motoristas['Motorista']==motorista]['id'].iloc[0])

        if guia!='':

            id_guia = int(st.session_state.df_guias[st.session_state.df_guias['Guia']==guia]['id'].iloc[0])

            payload = {
                    "date": date_str,
                    "vehicle_id": id_veiculo,
                    "driver_id": id_motorista,
                    "guide_id": id_guia,
                    "reserve_service_ids": id_servicos,
                }
            
        else:

            payload = {
                    "date": date_str,
                    "vehicle_id": id_veiculo,
                    "driver_id": id_motorista,
                    "reserve_service_ids": id_servicos,
                }
        
        escalas_para_atualizar.append(payload)

    placeholder = st.empty()
    placeholder.dataframe(escalas_para_atualizar)
    for escala in escalas_para_atualizar:
        escala_atual = escala.copy()
        if escala_atual['guide_id'] == None:
            escala_atual.pop('guide_id')
        if escala_atual['driver_id'] == None:
            escala_atual.pop('driver_id')
        if escala_atual['vehicle_id'] == None:
            escala_atual.pop('vehicle_id')
        status = update_scale(escala_atual)
        escala['status'] = status
        placeholder.dataframe(escalas_para_atualizar)

    with st.spinner('Buscando novos códigos de escalas...'):

        st.session_state.df_escalas = gerar_df_phoenix('vw_scales', st.session_state.base_luck)

    contador=0

    for escala in escalas_para_atualizar:
        novo_codigo = get_novo_codigo(escala['reserve_service_ids'][0])
        escala['novo_codigo'] = novo_codigo
        placeholder.dataframe(escalas_para_atualizar)
        st.session_state.df_escalas_atualizar.at[contador, 'Escala Nova'] = novo_codigo
        contador+=1

    with st.spinner('Inserindo novos códigos de escala no Google Drive...'):

        inserir_novas_escalas_drive(st.session_state.df_escalas_atualizar, st.session_state.id_gsheet, 'Atualizar Escalas')
