#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
import datetime
import os
import time
import requests
import threading
import queue
import warnings

warnings.filterwarnings("ignore")

# ================= CONFIG ================= #

this_year = int(datetime.datetime.today().strftime('%Y'))
today = datetime.datetime.today().strftime('%Y-%m-%d')

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

BASE_PATH = "raw_data_B3"
BACKUP_PATH = "BACKUPS"

# ========================================== #
# 🔧 UTILS
# ========================================== #

def safe_request(url, retries=3, sleep=2):
    for _ in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                return response.text
        except:
            pass
        time.sleep(sleep)
    return None


def safe_read_html(url):
    html = safe_request(url)
    if html is None:
        return None
    try:
        return pd.read_html(html, decimal=',', thousands='.')
    except:
        return None


# ========================================== #
# 📊 CAPITAL SOCIAL
# ========================================== #

print("Baixando capital social...")

url = "http://bvmf.bmfbovespa.com.br/CapitalSocial/"
tables = safe_read_html(url)

if tables:
    capital_social = tables[0]

    capital_social.drop_duplicates('Código', inplace=True)
    capital_social.set_index('Código', inplace=True)

    os.makedirs(f"{BASE_PATH}/capital_social", exist_ok=True)
    os.makedirs(f"{BACKUP_PATH}/capital_social", exist_ok=True)

    capital_social.to_pickle(f"{BASE_PATH}/capital_social/capitalsocial.pkl")
    capital_social.to_pickle(f"{BACKUP_PATH}/capital_social/capitalsocial{today}.pkl")

    print("Capital social OK")
else:
    print("Falha ao baixar capital social")


# ========================================== #
# 📥 CARREGANDO EMPRESAS
# ========================================== #

print("Carregando empresas...")

info = pd.read_pickle('clean_data/info_companies/info_companies_geral_comSetor.pkl')
codigo = info['Codigo_CVM'].unique()


# ========================================== #
# 💰 DIVIDENDOS HISTÓRICOS
# ========================================== #

print("Baixando dividendos históricos...")

os.makedirs(f"{BASE_PATH}/proventos/historico", exist_ok=True)

def fetch_hist(url, cvm):
    tables = safe_read_html(url)
    if tables:
        tables[0].to_pickle(f"{BASE_PATH}/proventos/historico/{cvm}.pkl")


batch_size = 20

for i in range(0, len(codigo), batch_size):
    threads = []

    for cvm in codigo[i:i+batch_size]:
        url = f"http://bvmf.bmfbovespa.com.br/cias-listadas/empresas-listadas/ResumoProventosDinheiro.aspx?codigoCvm={cvm}&tab=3.1&idioma=pt-br"

        t = threading.Thread(target=fetch_hist, args=(url, cvm))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    time.sleep(3)


# ========================================== #
# 📊 CONSOLIDANDO HISTÓRICO
# ========================================== #

print("Consolidando histórico...")

all_divd = pd.DataFrame()

for cvm in codigo:
    path = f"{BASE_PATH}/proventos/historico/{cvm}.pkl"
    if os.path.exists(path):
        df = pd.read_pickle(path)
        df['Codigo_CVM'] = cvm
        all_divd = pd.concat([all_divd, df])

if not all_divd.empty:
    all_divd["Últ. Dia 'Com'"] = pd.to_datetime(all_divd["Últ. Dia 'Com'"], format='%d/%m/%Y', errors='coerce')
    all_divd = all_divd[all_divd["Últ. Dia 'Com'"].dt.year > 2006]

    all_divd.rename({
        "Últ. Dia 'Com'": "Data COM",
        'Valor do Provento (R$)': 'Valor',
        'Tipo de Ativo': 'CLASSE'
    }, axis=1, inplace=True)

    all_divd.to_pickle(f"{BASE_PATH}/proventos/historico/all_proventos_hist.pkl")
    all_divd.to_pickle(f"{BACKUP_PATH}/proventos/all_proventos_hist{today}.pkl")

    print("Histórico OK")


# ========================================== #
# 📊 EVENTOS CORPORATIVOS
# ========================================== #

print("Baixando eventos corporativos...")

os.makedirs(f"{BASE_PATH}/proventos/eventos_corporativos", exist_ok=True)

def fetch_events(url, cvm):
    tables = safe_read_html(url)
    if tables:
        df = pd.concat(tables[2:], ignore_index=True)
        df.to_pickle(f"{BASE_PATH}/proventos/eventos_corporativos/{cvm}.pkl")


for i in range(0, len(codigo), batch_size):
    threads = []

    for cvm in codigo[i:i+batch_size]:
        url = f"http://bvmf.bmfbovespa.com.br/cias-listadas/empresas-listadas/ResumoEventosCorporativos.aspx?codigoCvm={cvm}&idioma=pt-br"

        t = threading.Thread(target=fetch_events, args=(url, cvm))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    time.sleep(3)


# ========================================== #
# 📊 CONSOLIDANDO EVENTOS
# ========================================== #

print("Consolidando eventos...")

all_event = pd.DataFrame()

for cvm in codigo:
    path = f"{BASE_PATH}/proventos/eventos_corporativos/{cvm}.pkl"
    if os.path.exists(path):
        df = pd.read_pickle(path)
        df['Codigo_CVM'] = cvm
        all_event = pd.concat([all_event, df])

if not all_event.empty:
    all_event['Data COM'] = pd.to_datetime(all_event['Data COM'], errors='coerce')

    all_event.to_pickle(f"{BASE_PATH}/proventos/eventos_corporativos/proventos_atuais_b3.pkl")
    all_event.to_pickle(f"{BACKUP_PATH}/proventos/proventos_atuais_b3{today}.pkl")

    print("Eventos OK")


# ========================================== #
# 🔚 FINAL
# ========================================== #

print("Script finalizado com sucesso.")
