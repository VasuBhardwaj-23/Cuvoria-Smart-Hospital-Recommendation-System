import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import ast
from math import radians, sin, cos, sqrt, atan2
import base64
import random
from groq import Groq
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
   

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Cuvoria - Smart Hospital Finder",
    page_icon="🏥",
    layout="wide"
)

# ---------------- API ----------------
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

llm = ChatGroq(
    groq_api_key=st.secrets["GROQ_API_KEY"],
    model_name="llama-3.1-8b-instant",
    temperature=0.4
)
  
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

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ---------------- LOAD DATA ----------------
df = pd.read_csv("cleaned_hospitals.csv")
df['specialization'] = df['specialization'].apply(ast.literal_eval)

# ---------------- FAKE CONTACT ----------------
def get_fake_contact():
    return "9" + "".join([str(random.randint(0,9)) for _ in range(9)])

from fpdf import FPDF
from datetime import datetime

def generate_pdf(hospitals):

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ---------------- LOGO ----------------
    try:
        pdf.image("logo.png", x=80, w=50)
        pdf.ln(10)
    except:
        pass

    # ---------------- TITLE ----------------
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Medical Recommendation Report", ln=True, align="C")

    pdf.ln(3)

    # ---------------- SUBTITLE ----------------
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Top 5 Recommended Hospitals", ln=True, align="C")

    pdf.ln(5)

    # ---------------- TIMESTAMP ----------------
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}", ln=True)

    pdf.ln(5)

    # ---------------- DATA ----------------
    for idx, (_, row) in enumerate(hospitals.iterrows(), start=1):

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, f"{idx}. {row['hospital_name']}", ln=True)

        pdf.set_font("Arial", "", 10)

        pdf.cell(0, 6, f"Location: {row['city']}, {row['state']}", ln=True)
        pdf.cell(0, 6, f"Distance: {round(row['distance'],1)} km", ln=True)
        pdf.cell(0, 6, f"Rating: {row['rating']}", ln=True)
        pdf.cell(0, 6, f"Consultation Fee: Rs {row['consultation_fee']}", ln=True)

        reason = f"Recommended based on {round(row['distance'],1)} km proximity and rating {row['rating']}"
        pdf.cell(0, 6, f"Reason: {reason}", ln=True)

        pdf.cell(0, 6, f"Contact: {get_fake_contact()}", ln=True)

        pdf.ln(4)

    file_path = "hospital_report.pdf"
    pdf.output(file_path)

    return file_path

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

    # distance
    filtered['distance'] = filtered.apply(
        lambda row: calculate_distance(
            user_row['latitude'], user_row['longitude'],
            row['latitude'], row['longitude']
        ), axis=1
    )

    city_df = filtered[filtered['city'].str.lower() == city.lower()].copy()
    other_df = filtered[filtered['city'].str.lower() != city.lower()].copy()

    # --------- STEP 1: build candidate set (rule-based) ----------
    if len(city_df) >= 5:
        candidates = city_df
        level = "city"
    elif len(city_df) > 0:
        # fill from nearest others
        remaining = 5 - len(city_df)
        nearest_fill = other_df.sort_values(by='distance').head(remaining)
        candidates = pd.concat([city_df, nearest_fill])
        level = "city"
    else:
        candidates = filtered
        level = "nearest"

    # --------- STEP 2: KNN only for ranking on candidates ----------
    try:
        from sklearn.preprocessing import StandardScaler
        from sklearn.neighbors import NearestNeighbors

        features = candidates[['rating', 'consultation_fee', 'distance', 'beds_available']]

        scaler = StandardScaler()
        X = scaler.fit_transform(features)

        k = min(5, len(candidates))
        knn = NearestNeighbors(n_neighbors=k)
        knn.fit(X)

        # default preference (baad me UI se dynamic kar sakte ho)
        user_input = pd.DataFrame(
            [[4.5, 700, 5, 150]],
            columns=['rating', 'consultation_fee', 'distance', 'beds_available']
        )
        u = scaler.transform(user_input)

        _, idx = knn.kneighbors(u)
        ranked = candidates.iloc[idx[0]].copy()

        # ensure stable order (city first if mixed)
        if len(city_df) > 0 and len(city_df) < 5:
            ranked = pd.concat([
                ranked[ranked['city'].str.lower() == city.lower()],
                ranked[ranked['city'].str.lower() != city.lower()]
            ])

        return ranked, level

    except:
        # safe fallback
        candidates['score'] = candidates.apply(calculate_score, axis=1)
        return candidates.sort_values(by='score', ascending=False).head(5), level

 
# ---------------- HOSPITAL CONTEXT FUNCTION ----------------

def get_hospital_context(query):

    query = query.lower()

    # -------- FIND REQUESTED CITY --------

    requested_city = None

    for city in df['city'].unique():

        if city.lower() in query:
            requested_city = city.lower()
            break

    # -------- MEDICAL KEYWORDS --------

    medical_map = {
        "blood test": ["pathology", "diagnostic", "lab"],
        "heart": ["cardiology"],
        "cardiology": ["cardiology"],
        "brain": ["neurology"],
        "bone": ["orthopedics"],
        "cancer": ["oncology"],
        "skin": ["dermatology"],
        "child": ["pediatrics"],
        "eye": ["ophthalmology"],
        "diabetes": ["endocrinology", "general medicine"]
    }

    specialization_keywords = []

    for key, values in medical_map.items():

        if key in query:
            specialization_keywords.extend(values)

    # -------- CITY FILTER --------

    city_df = pd.DataFrame()

    if requested_city:

        city_df = df[
            df['city'].str.lower() == requested_city
        ].copy()

    # -------- SPECIALIZATION FILTER --------

    if not city_df.empty and specialization_keywords:

        filtered = city_df[
            city_df['specialization'].astype(str).str.lower().apply(
                lambda x: any(k in x for k in specialization_keywords)
            )
        ]

    elif not city_df.empty:

        filtered = city_df

    else:

        filtered = pd.DataFrame()

    # -------- IF CITY MATCH FOUND --------

    if not filtered.empty:

        filtered = filtered.sort_values(
            by='rating',
            ascending=False
        ).head(5)

        context = ""

        for idx, (_, row) in enumerate(filtered.iterrows(), start=1):

            context += (
                f"{idx}. {row['hospital_name']}\n"
                f"City: {row['city']}\n"
                f"State: {row['state']}\n"
                f"Specialization: {', '.join(row['specialization'])}\n"
                f"Rating: {row['rating']}\n"
                f"Beds: {row['beds_available']}\n"
                f"Review: {row['review']}\n\n"
            )

        return context

    # -------- SAME STATE FALLBACK --------

    if requested_city:

        state_match = df[
            df['city'].str.lower() == requested_city
        ]

        if not state_match.empty:

            user_state = state_match.iloc[0]['state']

            nearby = df[
                df['state'] == user_state
            ].sort_values(
                by='rating',
                ascending=False
            ).head(5)

            if not nearby.empty:

                context = ""

                for idx, (_, row) in enumerate(nearby.iterrows(), start=1):

                    context += (
                        f"{idx}. {row['hospital_name']}\n"
                        f"City: {row['city']}\n"
                        f"State: {row['state']}\n"
                        f"Specialization: {', '.join(row['specialization'])}\n"
                        f"Rating: {row['rating']}\n"
                        f"Beds: {row['beds_available']}\n"
                        f"Review: {row['review']}\n\n"
                    )

                return context

    # -------- INDIA FALLBACK --------

    india_best = df.sort_values(
        by='rating',
        ascending=False
    ).head(5)

    context = ""

    for idx, (_, row) in enumerate(india_best.iterrows(), start=1):

        context += (
            f"{idx}. {row['hospital_name']}\n"
            f"City: {row['city']}\n"
            f"State: {row['state']}\n"
            f"Specialization: {', '.join(row['specialization'])}\n"
            f"Rating: {row['rating']}\n"
            f"Beds: {row['beds_available']}\n"
            f"Review: {row['review']}\n\n"
        )

    return context
  
# ---------------- LUNA FUNCTION ----------------

def ask_luna(query):

    # ---------------- SMART DATASET CONTEXT ----------------
    hospital_context = get_hospital_context(query)

    # ---------------- SYSTEM PROMPT ----------------
    messages = [
        SystemMessage(content=f"""
You are Luna, the AI healthcare assistant of Cuvoria.

Rules:
- Recommend hospitals naturally and professionally.
- Use ONLY the hospital information provided below.
- Never create fake hospitals, ratings, reviews, or facilities.
- If hospitals exist for the requested city, recommend ONLY those hospitals.
- Suggest nearby cities ONLY when no hospitals exist for the requested city.
- Never mention datasets, databases, missing data, or internal limitations.
- Do NOT explain hospitals in your own words.
- ONLY display the exact hospital information provided.
- Format recommendations in bullet-point style.
- Mention ratings, beds, reviews, and specialization whenever available.
- For general medical questions, answer medically first.
- Do not recommend hospitals unless the user asks.

Hospital Information:
{hospital_context}
""")
    ]

    # ---------------- CHAT HISTORY ----------------
    for msg in st.session_state.chat_history[-6:]:

        if msg["role"] == "user":
            messages.append(
                HumanMessage(content=msg["content"])
            )

        else:
            messages.append(
                AIMessage(content=msg["content"])
            )

    # ---------------- CURRENT USER QUERY ----------------
    messages.append(
        HumanMessage(content=query)
    )

    # ---------------- MODEL RESPONSE ----------------
    response = llm.invoke(messages)

    # ---------------- SAVE MEMORY ----------------
    st.session_state.chat_history.append({
        "role": "user",
        "content": query
    })

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": response.content
    })

    return response.content


# ---------------- CLEAR FUNCTION ----------------

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

    col1, col2, col3 = st.columns([1, 6, 1])

with col2:
    st_folium(m, width=1000)

if st.session_state.search_done and not st.session_state.emergency_mode:

    st.markdown("---")

    col1, col2, col3 = st.columns([1,2,1])

    with col2:
        # Download Button
        pdf_file = generate_pdf(results)

        with open(pdf_file, "rb") as f:
            st.download_button(
                label="📄 Download Report",
                data=f,
                file_name="Cuvoria_Report.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # New Search
        if st.button("🔄 New Search", use_container_width=True):
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
