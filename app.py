import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import date, datetime
import requests
import matplotlib.pyplot as plt
import os
import requests

token = st.secrets.TOKEN
url = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"
plt.style.use('classic')

def format_date_to_api(date_input):
    return date_input.strftime('%Y%m%d')

def display_card(parameter_name, value):
    if value == -999.0:  
        return
    st.metric(label=parameter_name, value=value)

def plot_graph(values, parameter_name):
    valid_values = [v for v in values if v != -999.0]  
    if not valid_values:  
        st.warning(f"No valid data available for {parameter_name}.")
        return
    plt.figure(figsize=(10, 4))
    plt.plot(valid_values, marker='o', linestyle='-', color='black')
    plt.title(f"{parameter_name}", fontsize=16, weight='bold')
    plt.xlabel("")
    plt.ylabel(parameter_name, fontsize=12)
    plt.xticks([])
    plt.yticks(fontsize=10)
    plt.box(False)
    st.pyplot(plt)


parameter_names = {
    "PRECTOTCORR": "Corrected Precipitation (mm/hour)",
    "GWETROOT": "Root Zone Soil Wetness",
    "GWETPROF": "Profile Soil Moisture",
    "GWETTOP": "Surface Soil Wetness",
    "EVPTRNS": "Evapotranspiration (mm/hour)",
    "T2M": "Temperature at 2m (°C)",
    "WS10M": "Wind Speed at 10m (m/s)",
    "WD10M": "Wind Direction at 10m (degrees)",
    "ALLSKY_SFC_UV_INDEX": "Surface UV Index",
    "ALLSKY_SRF_ALB": "Surface Albedo",
    "RH2M": "Relative Humidity at 2m",
    "ALLSKY_SFC_SW_DWN": "Surface Shortwave Downward Irradiance",
    "ALLSKY_KT": "Atmospheric Transmissivity"
}

def generate_suggestions(data):
    suggestions = []

    precip_data = data.get('PRECTOTCORR', {})
    if precip_data:
        precip_value = list(precip_data.values())[0]
        if precip_value != -999.0: 
            if precip_value < 5:
                suggestions.append(f"Low precipitation ({precip_value} mm). Suggested to start irrigation.")
            else:
                suggestions.append(f"Sufficient precipitation ({precip_value} mm). Irrigation not necessary.")

    uv_data = data.get('ALLSKY_SFC_UV_INDEX', {})
    if uv_data:
        uv_value = list(uv_data.values())[0]
        if uv_value != -999.0:  
            if uv_value >= 8:  
                suggestions.append(f"High UV Index ({uv_value}). Protect the plants.")
            else:
                suggestions.append(f"Safe UV Index ({uv_value}). No action needed.")

    wind_speed_data = data.get('WS10M', {})
    if wind_speed_data:
        wind_speed_value = list(wind_speed_data.values())[0]
        if wind_speed_value != -999.0:  
            if wind_speed_value > 5:
                suggestions.append(f"Strong wind ({wind_speed_value} m/s). Spraying not recommended.")
            else:
                suggestions.append(f"Suitable conditions for spraying ({wind_speed_value} m/s).")

    return suggestions


def generate_hf_insights(culturas, tamanho, data, insights):
    # Define parameters for Hugging Face model
    parameters = {
        "max_new_tokens": 5000,
        "temperature": 0.01,
        "top_k": 50,
        "top_p": 0.95,
        "return_full_text": False
    }

    # Create prompt based on inputs (culturas, tamanho, data, insights)
    prompt = f"""
    The farmer selected the following options:
- Crops: {', '.join(culturas)}
    -Crop size: {tamanho}
    - Weather data: {data}

Based on the information above, provide useful insights for the farmer and recommended strategies. Here are some initial suggestions:
{insights}

   Generate more personalized suggestions and insights. Be objective and concise.
The output cannot be in md format. Write in plain text
    """

    headers = {
        'Authorization': f'Bearer {token}',  
        'Content-Type': 'application/json'
    }

    payload = {
        "inputs": prompt,
        "parameters": parameters
    }


    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        st.error(f"API request failed with status code {response.status_code}: {response.text}")
        return "Failed to generate insights due to an API error."

    response_json = response.json()

    if isinstance(response_json, list) and len(response_json) > 0 and 'generated_text' in response_json[0]:
        response_text = response_json[0]['generated_text'].strip()
    else:
        st.error("Unexpected response format from Hugging Face API. Please check the API response.")
        st.write("API Response:", response_json)
        response_text = "No insights generated due to an error in processing."

    return response_text

st.header("Select your crop types")
milho = st.checkbox("Corn")
soja = st.checkbox("Soybean")
algodao = st.checkbox("Cotton")

culturas_selecionadas = []
if milho:
    culturas_selecionadas.append("Corn")
if soja:
    culturas_selecionadas.append("Soybean")
if algodao:
    culturas_selecionadas.append("Cotton")

if not culturas_selecionadas:
    st.warning("You must select at least one crop type.")
else:
    st.success(f"Selected crops: {', '.join(culturas_selecionadas)}")

st.header("Select your crop size")
tamanho_cultura = None
if st.checkbox("Up to 1 hectare"):
    tamanho_cultura = "Up to 1 hectare"
elif st.checkbox("1 to 3 hectares"):
    tamanho_cultura = "1 to 3 hectares"
elif st.checkbox("More than 3 hectares"):
    tamanho_cultura = "More than 3 hectares"

if not tamanho_cultura:
    st.warning("You must select the size of your crop.")
else:
    st.success(f"Selected size: {tamanho_cultura}")

if culturas_selecionadas and tamanho_cultura:

    min_date_allowed = date(2024, 10, 1)
    max_date_allowed = date(2024, 10, 6)

    st.title("Select your area on the map and the time range")
    st.write("Use the map below to click and select the desired area, then choose the time range.")

    m = folium.Map(location=[-16.71, -49.26], zoom_start=10)

    m.add_child(folium.LatLngPopup())

    st_data = st_folium(m, width=700, height=500)

    st.write(f"Select the date range (between {min_date_allowed} and {max_date_allowed}). Do not exceed 5 days:")
    start_date = st.date_input("Start date", value=min_date_allowed, key="start_date", min_value=min_date_allowed, max_value=max_date_allowed)
    end_date = st.date_input("End date", value=max_date_allowed, key="end_date", min_value=min_date_allowed, max_value=max_date_allowed)

    if st_data and 'last_clicked' in st_data and st_data['last_clicked'] is not None:
        latitude = st_data['last_clicked']['lat']
        longitude = st_data['last_clicked']['lng']

        st.write("Selected Coordinates:")
        st.success(f"Latitude: {latitude}, Longitude: {longitude}")

        with st.form("Send Coordinates and Time Interval"):
            st.write("Ready to submit data?")
            submitted = st.form_submit_button("Submit")

            if submitted:
                start_date_str = format_date_to_api(start_date)
                end_date_str = format_date_to_api(end_date)

                parameters = "PRECTOTCORR,GWETROOT,GWETPROF,GWETTOP,EVPTRNS,T2M,WS10M,WD10M,ALLSKY_SFC_UV_INDEX,ALLSKY_SRF_ALB,RH2M,ALLSKY_SFC_SW_DWN,ALLSKY_KT"
                format_type = "JSON"
                api_power_url = f"https://power.larc.nasa.gov/api/temporal/daily/point?latitude={latitude}&longitude={longitude}&parameters={parameters}&format={format_type}&start={start_date_str}&end={end_date_str}&community=AG"

                response_power = requests.get(api_power_url)

                if response_power.status_code == 200:
                    st.success("NASA API data received successfully!")
                    data = response_power.json()['properties']['parameter']

                    suggestions = generate_suggestions(data)
                    for suggestion in suggestions:
                        st.info(suggestion)

                    for parameter, values in data.items():
                        parameter_label = parameter_names.get(parameter, parameter)
                        value_list = list(values.values())
                        
                        valid_values = [v for v in value_list if v != -999.0]
                        
                        if valid_values:  
                            first_value = valid_values[0]
                            display_card(parameter_label, first_value)
                            plot_graph(valid_values, parameter_label)

                    insights = "\n".join(suggestions)
                    chatgpt_insights = generate_hf_insights(culturas_selecionadas, tamanho_cultura, data, insights)
                    st.text_area("Insights:", value=chatgpt_insights, height=200)
                else:
                    st.error(f"Error making request to NASA API: {response_power.status_code}")
                    st.write(f"Error message: {response_power.text}")
