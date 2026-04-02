🏥 CUVORIA - Smart Hospital Recommendation System

<p align="center">
  <b>Right Care, Right Place, Right Time</b>
</p>---

📸 Application Preview

🏠 Home Interface

"Home" (assets/home.png)

🔍 Hospital Recommendations

"Results" (assets/results.png)

📊 Insights & Analytics

"Insights" (assets/insights.png)

🗺️ Interactive Map View

"Map" (assets/map.png)

🤖 Luna AI Assistant

"Assistant" (assets/assistant.png)

---

🧠 Overview

Cuvoria is a smart hospital recommendation system designed to help users find the most suitable healthcare options based on location, specialization, availability, and quality metrics.

It combines data-driven scoring, geolocation logic, and AI assistance to deliver reliable and efficient hospital recommendations.

---

✨ Key Features

- 🔍 Smart recommendations based on city and specialization
- 📍 Distance-based ranking using geolocation calculations
- ⭐ Intelligent scoring system (rating, distance, availability)
- 🚑 Emergency mode for instant nearest hospitals
- 📊 Interactive insights (ratings, fees, availability comparison)
- 🗺️ Map visualization using Folium
- 🤖 Luna AI Assistant for basic medical queries
- 💾 Bookmark system for saving hospitals
- 🎨 Clean and responsive UI with Streamlit

---

🛠️ Tech Stack

- Frontend: Streamlit
- Backend: Python
- Data Processing: Pandas
- Mapping: Folium
- AI Integration: Groq (LLaMA 3)
- Visualization: Streamlit Charts

---

⚙️ Installation & Setup

1. Clone Repository

git clone https://github.com/your-username/Cuvoria-Smart-Hospital-Recommendation-System.git
cd Cuvoria-Smart-Hospital-Recommendation-System

2. Install Dependencies

pip install -r requirements.txt

3. Configure API Key

Create a file: ".streamlit/secrets.toml"

GROQ_API_KEY = "your_api_key_here"

4. Run Application

streamlit run app.py

---

🚀 How It Works

1. Select your city
2. Choose required treatment/specialization
3. Click Find Hospitals
4. View:
   - Recommended hospitals
   - Analytical insights
   - Interactive map
   - AI assistance via Luna

---

📂 Project Structure

Cuvoria/
 ├── app.py
 ├── cleaned_hospitals.csv
 ├── logo.png
 ├── requirements.txt
 ├── assets/
 │    ├── home.png
 │    ├── results.png
 │    ├── insights.png
 │    ├── map.png
 │    └── assistant.png
 └── README.md

---

👨‍💻 Author

Vasu Bhardwaj
BTech CSE | Data Analytics | AI & Cloud Enthusiast

---

📌 Note

This project demonstrates the integration of data analytics, geospatial logic, and AI to solve real-world healthcare discovery problems.

---

© 2026 Cuvoria • Built by Vasu Bhardwaj
