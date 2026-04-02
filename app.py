import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import ast
from math import radians, sin, cos, sqrt, atan2
import base64
import random
from groq import Groq   

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Cuvoria - Smart Hospital Finder",
    page_icon="🏥",
    layout="wide"
)

# ---------------- API ----------------
client = Groq(api_key=st.secrets["GROQ_API_KEY"])  

# ---------------- SESSION ----------------
if "search_done" not in st.session_state:
    st.session_state.search_done = False

if "bookmarks" not in st.session_state:
    st.session_state.bookmarks = []

if "emergency_mode" not in st.session_state:
    st.session_state.emergency_mode = False

# ✅ LUNA STATE (ADDED ONLY)
if "luna_response" not in st.session_state:
    st.session_state.luna_response = ""

if "luna_query" not in st.session_state:
    st.session_state.luna_query = ""

# ---------------- LOAD DATA ----------------
df = pd.read_csv("cleaned_hospitals.csv")
df['specialization'] = df['specialization'].apply(ast.literal_eval)

# ---------------- FAKE CONTACT ----------------
def get_fake_contact():
    return "9" + "".join([str(random.randint(0,9)) for _ in range(9)])

# ---------------- DISTANCE ----------------
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

# ---------------- SCORE ----------------
def calculate_score(row):
    return (
        row['rating'] * 0.5 +
        (1 / (row['distance'] + 1)) * 0.4 +
        (row['available_slots'] * 0.1)
    )

# ---------------- FILTER ----------------
def filter_specialization(df, specialization):
    keywords_map = {
        "Emergency": ["Emergency", "General Medicine", "Cardiology"],
        "Basic Care": ["General Medicine", "Pediatrics", "ENT"],
    }

    if specialization in keywords_map:
        keywords = keywords_map[specialization]
        return df[df['specialization'].apply(lambda x: any(k in x for k in keywords))].copy()

    return df[df['specialization'].apply(lambda x: specialization in x)].copy()

# ---------------- MAIN ----------------
def get_recommendations(city, specialization):

    user_row = df[df['city'].str.lower() == city.lower()]
    if len(user_row) == 0:
        return pd.DataFrame(), "none"

    user_row = user_row.iloc[0]

    filtered = filter_specialization(df, specialization)

    filtered['distance'] = filtered.apply(
        lambda row: calculate_distance(
            user_row['latitude'], user_row['longitude'],
            row['latitude'], row['longitude']
        ), axis=1
    )

    city_result = filtered[filtered['city'].str.lower() == city.lower()]
    if len(city_result) >= 3:
        city_result['score'] = city_result.apply(calculate_score, axis=1)
        return city_result.sort_values(by='score', ascending=False).head(5), "city"

    state_result = filtered[filtered['state'] == user_row['state']]
    if len(state_result) >= 3:
        state_result['score'] = state_result.apply(calculate_score, axis=1)
        return state_result.sort_values(by='score', ascending=False).head(5), "state"

    filtered['score'] = filtered.apply(calculate_score, axis=1)
    return filtered.sort_values(by=['distance', 'rating'], ascending=[True, False]).head(5), "nearest"

# ---------------- LUNA FUNCTION (ADDED ONLY) ----------------
def ask_luna(query):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are Luna, a health assistant. Give short clear answers."},
            {"role": "user", "content": query}
        ]
    )
    return response.choices[0].message.content

def clear_luna():
    st.session_state.luna_query = ""
    st.session_state.luna_response = ""

# ---------------- CSS ----------------
st.markdown("""
<style>
div.stButton > button {
    border-radius: 10px;
    padding: 10px 25px;
    border: 1px solid #00ff9f;
    background-color: transparent;
    color: #00ff9f;
    transition: all 0.3s ease;
}
div.stButton > button:hover {
    background-color: #00ff9f;
    color: black;
    box-shadow: 0 0 20px #00ff9f;
}
.card {
    background-color: #0f172a;
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 15px;
    border: 1px solid #1e293b;
    transition: 0.3s;
}
.card:hover {
    border: 1px solid #00ff9f;
    box-shadow: 0 0 15px #00ff9f;
}
section[data-testid="stSidebar"] {
    background-color: #020617;
}
section[data-testid="stSidebar"] h3 {
    color: #00ff9f !important;
    font-weight: 600;
}
.sidebar-divider {
    height: 1px;
    background: linear-gradient(to right, transparent, #00ff9f, transparent);
    margin: 10px 0 20px 0;
}
</style>
""", unsafe_allow_html=True)

# ---------------- LOGO ----------------
def get_base64_image(image_path):
    with open(image_path, "rb") as img:
        return base64.b64encode(img.read()).decode()

logo_base64 = get_base64_image("logo.png")

st.markdown(f"""
<div style="display:flex; justify-content:center; align-items:center; margin-top:10px;">
    <img src="data:image/png;base64,{logo_base64}" width="320">
</div>
""", unsafe_allow_html=True)

# ---------------- TITLE ----------------
st.markdown("""
<h1 style="text-align:center; margin-top:-10px;">
Smart Hospital Recommendation System
</h1>
<p style="text-align:center; color:#9CA3AF; margin-top:-6px;">
Right Care, Right Place, Right Time
</p>
""", unsafe_allow_html=True)

st.markdown("---")

# ---------------- SIDEBAR ----------------
st.sidebar.markdown("### 🚑 Emergency")
st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

if st.sidebar.button("Emergency Help"):
    st.session_state.emergency_mode = True

# ---------------- LUNA SIDEBAR ----------------
st.sidebar.markdown("### ✨ Luna")

luna_query = st.sidebar.text_input("Ask Luna...", key="luna_query")

if st.sidebar.button("Ask Luna"):
    if luna_query:
        st.session_state.luna_response = ask_luna(luna_query)

st.sidebar.button("💬 New Chat", on_click=clear_luna)

# ---------------- INPUT ----------------
col1, col2 = st.columns(2)

with col1:
    specialization = st.selectbox(
        "Select Treatment",
        sorted(list(set([i for sub in df['specialization'] for i in sub])))
    )

with col2:
    city = st.selectbox(
        "Select City",
        sorted(df['city'].unique())
    )

if st.button("🔍 Find Hospitals"):
    st.session_state.search_done = True
    st.session_state.emergency_mode = False

# ---------------- EMERGENCY MODE ----------------
if st.session_state.emergency_mode:

    st.error("🚑 Showing nearest hospitals immediately")

    user_row = df[df['city'].str.lower() == city.lower()].iloc[0]

    df['distance'] = df.apply(
        lambda row: calculate_distance(
            user_row['latitude'], user_row['longitude'],
            row['latitude'], row['longitude']
        ), axis=1
    )

    emergency_df = df.sort_values(by='distance').head(5)

    for _, row in emergency_df.iterrows():
        st.markdown(f"""
        <div style="background:#7f1d1d;padding:15px;border-radius:10px;margin:10px 0;">
            <h4 style="color:#fca5a5;">{row['hospital_name']}</h4>
            📍 {row['city']}, {row['state']} <br>
            📏 Distance: {round(row['distance'],1)} km <br>
            ⭐ {row['rating']} | 💰 ₹{row['consultation_fee']} <br>
            📞 Contact: {get_fake_contact()}
        </div>
        """, unsafe_allow_html=True)

    st.warning("📞 Emergency Number: 112 (India)")

# ---------------- NORMAL RESULTS ----------------
elif st.session_state.search_done:

    results, level = get_recommendations(city, specialization)

    if level == "city":
        st.success(f"Showing hospitals in {city}")
    elif level == "state":
        st.info("Showing nearby hospitals in your state")
    else:
        st.warning("Showing nearest hospitals")

    st.markdown("---")
    st.subheader("🏥 Recommended Hospitals")

    for _, row in results.iterrows():

        st.markdown(f"""
        <div class="card">
            <h4 style="color:#00ff9f;">{row['hospital_name']}</h4>
            📍 {row['city']}, {row['state']} <br>
            ⭐ Rating: {row['rating']} <br>
            💰 Fee: ₹{row['consultation_fee']} <br>
            🛏 Beds: {row['beds_available']} | ⏱ Slots: {row['available_slots']} <br>
            📏 Distance: {round(row['distance'],1)} km<br>
            📞 Contact: {get_fake_contact()} <br>
            📝 {row['review']}
        </div>
        """, unsafe_allow_html=True)

        if st.button("Save", key=f"save_{row['hospital_name']}"):
            if row['hospital_name'] not in st.session_state.bookmarks:
                st.session_state.bookmarks.append(row['hospital_name'])
                st.success("Saved!")
            else:
                st.warning("Already saved!")

    # Sidebar Bookmark
    st.sidebar.markdown("### ⭐ Saved Hospitals")
    st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    if len(st.session_state.bookmarks) > 0:
        for h in st.session_state.bookmarks:
            st.sidebar.write(f"• {h}")
    else:
        st.sidebar.write("No saved hospitals yet")

    # ---------------- INSIGHTS ----------------
    st.markdown("---")
    st.subheader("📊 Insights")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("⭐ Ratings Comparison")
        st.bar_chart(results.set_index('hospital_name')['rating'], color="#00ff9f")

    with col2:
        st.markdown("💰 Consultation Fees")
        st.bar_chart(results.set_index('hospital_name')['consultation_fee'], color="#00ff9f")

    st.markdown("🛏 Beds Availability")
    st.bar_chart(results.set_index('hospital_name')['beds_available'], color="#00ff9f")

    # ---------------- MAP ----------------
    st.markdown("---")
    st.subheader("📍 Hospital Locations")

    m = folium.Map(
        location=[results.iloc[0]['latitude'], results.iloc[0]['longitude']],
        zoom_start=10
    )

    for _, row in results.iterrows():
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(
                f"<b>{row['hospital_name']}</b><br>⭐ {row['rating']}<br>₹ {row['consultation_fee']}",
                max_width=250
            ),
            icon=folium.Icon(color="green", icon="plus-sign")
        ).add_to(m)

    st_folium(m, width=1000)

    if st.button("🔄 New Search"):
        st.session_state.search_done = False
        st.rerun()

# ---------------- LUNA OUTPUT (ADDED ONLY) ----------------
if st.session_state.luna_response:
    st.markdown("---")
    st.subheader("✨ Luna Assistant")
    st.write(st.session_state.luna_response)

# ---------------- FOOTER ----------------
st.markdown("""
<div style="text-align:center; margin-top:50px; color:#9CA3AF;">
© Cuvoria 2026 • Built by Vasu Bhardwaj
</div>
""", unsafe_allow_html=True)