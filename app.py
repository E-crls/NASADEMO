import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import date, datetime
import requests
import matplotlib.pyplot as plt
import openai
import os
from openai import OpenAI

os.environ['OPENAI_API_KEY'] = "sk--"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

openai.api_key = os.getenv("OPENAI_API_KEY")

plt.style.use('classic')

def format_date_to_api(date_input):
    return date_input.strftime('%Y%m%d')

def display_card(parameter_name, value):
    st.metric(label=parameter_name, value=value)

def plot_graph(values, parameter_name):
    plt.figure(figsize=(10, 4))
    plt.plot(values, marker='o', linestyle='-', color='black')
    plt.title(f"{parameter_name}", fontsize=16, weight='bold')
    plt.xlabel("")
    plt.ylabel(parameter_name, fontsize=12)
    plt.xticks([])
    plt.yticks(fontsize=10)
    plt.box(False)
    st.pyplot(plt)

parameter_names = {
    "PRECTOTCORR": "Precipitação Corrigida (mm/hora)",
    "GWETROOT": "Umidade na Camada Superior das Raízes",
    "GWETPROF": "Umidade no Perfil do Solo",
    "GWETTOP": "Umidade na Superfície do Solo",
    "EVPTRNS": "Evapotranspiração (mm/hora)",
    "T2M": "Temperatura a 2m (°C)",
    "WS10M": "Velocidade do Vento a 10m (m/s)",
    "WD10M": "Direção do Vento a 10m (graus)",
    "ALLSKY_SFC_UV_INDEX": "Índice UV na Superfície",
    "ALLSKY_SRF_ALB": "Albedo da Superfície",
    "RH2M": "Umidade Relativa a 2m",
    "ALLSKY_SFC_SW_DWN": "Irradiação Solar na Superfície",
    "ALLSKY_KT": "Transmissividade da Atmosfera"
}

def generate_suggestions(data):
    suggestions = []

    precip_data = data.get('PRECTOTCORR', {})
    if precip_data:
        precip_value = list(precip_data.values())[0]
        if precip_value < 5:
            suggestions.append(f"Precipitação baixa ({precip_value} mm). Sugerido iniciar irrigação.")
        else:
            suggestions.append(f"Precipitação suficiente ({precip_value} mm). Irrigação não necessária.")

    uv_data = data.get('ALLSKY_SFC_UV_INDEX', {})
    if uv_data:
        uv_value = list(uv_data.values())[0]
        if uv_value >= 8:
            suggestions.append(f"Índice UV elevado ({uv_value}). Proteja as plantas.")
        else:
            suggestions.append(f"Índice UV seguro ({uv_value}). Nenhuma ação necessária.")

    wind_speed_data = data.get('WS10M', {})
    if wind_speed_data:
        wind_speed_value = list(wind_speed_data.values())[0]
        if wind_speed_value > 5:
            suggestions.append(f"Vento forte ({wind_speed_value} m/s). Pulverização não recomendada.")
        else:
            suggestions.append(f"Condições adequadas para pulverização ({wind_speed_value} m/s).")

    return suggestions

def generate_chatgpt_insights(culturas, tamanho, data, insights):
    prompt = f"""
    O agricultor selecionou as seguintes opções:
    - Culturas: {', '.join(culturas)}
    - Tamanho da cultura: {tamanho}
    - Dados meteorológicos: {data}

    Com base nas informações acima, forneça insights úteis para o agricultor e estratégias recomendadas. Aqui estão algumas sugestões iniciais:
    {insights}

    Gere mais sugestões e insights personalizados. Seja objetivo e resumido.
    O output não pode ser em formato md. Escreva em texto normal
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Você é um engenheiro agrônomo especializado em fitopatologia e otimização de produção agrícola."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content

st.header("Selecione os seus tipos de culturas")
milho = st.checkbox("Milho")
soja = st.checkbox("Soja")
algodao = st.checkbox("Algodão")

culturas_selecionadas = []
if milho:
    culturas_selecionadas.append("Milho")
if soja:
    culturas_selecionadas.append("Soja")
if algodao:
    culturas_selecionadas.append("Algodão")

if not culturas_selecionadas:
    st.warning("Você deve selecionar pelo menos um tipo de cultura.")
else:
    st.success(f"Culturas selecionadas: {', '.join(culturas_selecionadas)}")

st.header("Selecione o tamanho da sua cultura")
tamanho_cultura = None
if st.checkbox("Até 1 hectare"):
    tamanho_cultura = "Até 1 hectare"
elif st.checkbox("1 a 3 hectares"):
    tamanho_cultura = "1 a 3 hectares"
elif st.checkbox("Mais de 3 hectares"):
    tamanho_cultura = "Mais de 3 hectares"

if not tamanho_cultura:
    st.warning("Você deve selecionar o tamanho da sua cultura.")
else:
    st.success(f"Tamanho selecionado: {tamanho_cultura}")

if culturas_selecionadas and tamanho_cultura:

    min_date_allowed = date(2001, 1, 1)
    max_date_allowed = date(2024, 10, 10)

    st.title("Selecione sua área no mapa e o intervalo de tempo")
    st.write("Use o mapa abaixo para clicar e selecionar a área desejada, e depois escolha o intervalo de tempo.")

    m = folium.Map(location=[-16.71, -49.26], zoom_start=10)

    m.add_child(folium.LatLngPopup())

    st_data = st_folium(m, width=700, height=500)

    st.write(f"Selecione o intervalo de datas (entre {min_date_allowed} e {max_date_allowed}):")
    start_date = st.date_input("Data de início", value=min_date_allowed, key="start_date", min_value=min_date_allowed, max_value=max_date_allowed)
    end_date = st.date_input("Data de fim", value=max_date_allowed, key="end_date", min_value=min_date_allowed, max_value=max_date_allowed)

    st.write(f"Data de início selecionada: {start_date}")
    st.write(f"Data de fim selecionada: {end_date}")

    if st_data and 'last_clicked' in st_data and st_data['last_clicked'] is not None:
        latitude = st_data['last_clicked']['lat']
        longitude = st_data['last_clicked']['lng']

        st.write("Coordenadas Selecionadas:")
        st.success(f"Latitude: {latitude}, Longitude: {longitude}")

        with st.form("Enviar Coordenadas e Intervalo de Tempo"):
            st.write("Pronto para enviar os dados?")
            st.text_input("Latitude", value=f"{latitude}", key="lat_input")
            st.text_input("Longitude", value=f"{longitude}", key="lon_input")
            st.text_input("Data de Início", value=f"{start_date}", key="start_date_input")
            st.text_input("Data de Fim", value=f"{end_date}", key="end_date_input")
            submitted = st.form_submit_button("Enviar")

            if submitted:
                start_date_str = format_date_to_api(start_date)
                end_date_str = format_date_to_api(end_date)

                parameters = "PRECTOTCORR,GWETROOT,GWETPROF,GWETTOP,EVPTRNS,T2M,WS10M,WD10M,ALLSKY_SFC_UV_INDEX,ALLSKY_SRF_ALB,RH2M,ALLSKY_SFC_SW_DWN,ALLSKY_KT"
                format_type = "JSON"
                api_power_url = f"https://power.larc.nasa.gov/api/temporal/daily/point?latitude={latitude}&longitude={longitude}&parameters={parameters}&format={format_type}&start={start_date_str}&end={end_date_str}&community=AG"

                response_power = requests.get(api_power_url)

                if response_power.status_code == 200:
                    st.success("Dados da API POWER NASA recebidos com sucesso!")
                    data = response_power.json()['properties']['parameter']

                    suggestions = generate_suggestions(data)
                    for suggestion in suggestions:
                        st.info(suggestion)

                    for parameter, values in data.items():
                        parameter_label = parameter_names.get(parameter, parameter)
                        value_list = list(values.values())

                        if value_list:
                            first_value = value_list[0]
                            display_card(parameter_label, first_value)
                            plot_graph(value_list, parameter_label)

                    insights = "\n".join(suggestions)
                    chatgpt_insights = generate_chatgpt_insights(culturas_selecionadas, tamanho_cultura, data, insights)
                    st.text_area("Insights:", value=chatgpt_insights, height=200)
                else:
                    st.error(f"Erro ao fazer a requisição para API POWER NASA: {response_power.status_code}")
                    st.write(f"Mensagem de erro: {response_power.text}")
