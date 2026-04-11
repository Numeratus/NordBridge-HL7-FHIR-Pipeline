import streamlit as st
import requests

# --- Page Config ---
st.set_page_config(page_title="Nordpeak EHR", page_icon="🏥", layout="wide")

FHIR_BASE_URL = "https://hapi.fhir.org/baseR4"
TARGET_MRN = "NP-2026-004"

# --- FHIR API Functions ---
def get_patient(mrn):
    """Fetch Patient by MRN"""
    url = f"{FHIR_BASE_URL}/Patient?identifier=http://nordpeak.de/fhir/patients|{mrn}"
    res = requests.get(url).json()
    if res.get("total", 0) > 0:
        return res["entry"][0]["resource"]
    return None

def get_encounter(mrn):
    """Fetch Encounter by MRN"""
    url = f"{FHIR_BASE_URL}/Encounter?identifier=http://nordpeak.de/fhir/encounters|{mrn}-ENC"
    res = requests.get(url).json()
    if res.get("total", 0) > 0:
        return res["entry"][0]["resource"]
    return None

def get_vitals(mrn):
    """Fetch Vital Signs using the project tag and filter by MRN in Python"""
    # We use the 'nordbridge' tag we added in Mirth to find our data
    url = f"{FHIR_BASE_URL}/Observation?_tag=nordbridge&_count=100"
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return []
            
        bundle = response.json()
        vitals = []
        
        # Loop through all NordBridge vitals and find the ones for Max
        for entry in bundle.get("entry", []):
            resource = entry.get("resource", {})
            # Look inside the Logical Reference we built in Mirth
            subject_mrn = resource.get("subject", {}).get("identifier", {}).get("value")
            
            if subject_mrn == mrn:
                vitals.append(resource)
        
        return vitals
    except:
        return []

# --- UI Header ---
st.title("🏥 Nordpeak Medical Center - Patient Chart")
st.markdown("---")

st.subheader(f"Searching FHIR Server for MRN: `{TARGET_MRN}`")

with st.spinner("Connecting to HAPI FHIR..."):
    patient = get_patient(TARGET_MRN)
    encounter = get_encounter(TARGET_MRN)

# --- Display Data ---
if patient:
    internal_id = patient.get("id", "")
    vitals = get_vitals(TARGET_MRN)
    
    # Parse Patient Data
    name_dict = patient.get("name", [{}])[0]
    full_name = f"{name_dict.get('family', '')}, {name_dict.get('given', [''])[0]}"
    gender = patient.get("gender", "Unknown").capitalize()
    dob = patient.get("birthDate", "Unknown")
    
    st.success(f"✅ Patient Found! (HAPI Internal ID: {internal_id})")
    
    # Demographics Grid
    st.markdown("### 👤 Demographics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Patient Name", full_name)
    col2.metric("Date of Birth", dob)
    col3.metric("Gender", gender)
    
    st.markdown("---")
    
    # Encounter Data
    if encounter:
        st.markdown("### 🛏️ Current Encounter")
        status = encounter.get("status", "Unknown").upper()
        
        # Color code the status
        if status == "IN-PROGRESS":
            st.info(f"Status: **{status}** (Admitted)")
        elif status == "FINISHED":
            st.warning(f"Status: **{status}** (Discharged)")
            
        period = encounter.get("period", {})
        admit_time = period.get("start", "N/A")
        discharge_time = period.get("end", "N/A")
        location = encounter.get("location", [{}])[0].get("location", {}).get("display", "N/A")
        doctor = encounter.get("participant", [{}])[0].get("individual", {}).get("display", "N/A")
        
        col_e1, col_e2, col_e3 = st.columns(3)
        col_e1.write(f"**Location:** {location}")
        col_e2.write(f"**Attending:** {doctor}")
        col_e3.write(f"**Admitted:** {admit_time}")
        
        if status == "FINISHED":
            st.write(f"**Discharged:** {discharge_time}")
    else:
        st.error("No encounter found for this patient.")

    st.markdown("---")

    # Vitals Data
    st.markdown("### ❤️ Vital Signs")
    if vitals:
        v_col1, v_col2 = st.columns(2)
        for obs in vitals:
            code_display = obs.get("code", {}).get("coding", [{}])[0].get("display", "Unknown")
            value = obs.get("valueQuantity", {}).get("value", "--")
            unit = obs.get("valueQuantity", {}).get("unit", "")
            
            # Format display nicely
            if "Heart rate" in code_display:
                v_col1.metric(label="💓 Heart Rate", value=f"{value} {unit}")
            elif "temperature" in code_display.lower():
                v_col2.metric(label="🌡️ Body Temperature", value=f"{value} {unit}")
    else:
        st.info("No vital signs recorded for this patient.")

else:
    st.error("Patient not found on server. Did you run the Mirth channels?")
