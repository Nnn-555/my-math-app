import streamlit as st
from google import generativeai as genai
import json, os, PyPDF2
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Math Mastery AI V4")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash-latest")

DB_FILE="student_db.json"

# ---------------- DATABASE ----------------
def load_db():
    if os.path.exists(DB_FILE):
        return json.load(open(DB_FILE))
    return {}

def save_db(db):
    json.dump(db, open(DB_FILE,"w"), indent=2)

if "db" not in st.session_state:
    st.session_state.db = load_db()

db = st.session_state.db

if "User 1" not in db:
    db["User 1"]={"score":0,"skills":{}, "syllabus_chunks":[]}
save_db(db)

# ---------------- HELPERS ----------------
def extract_pdf(file):
    reader=PyPDF2.PdfReader(file)
    return "".join(p.extract_text() or "" for p in reader.pages)

def chunk_text(text,size=600):
    return [text[i:i+size] for i in range(0,len(text),size)]

def weakest_topic(skills):
    if not skills:
        return "Mathematics"
    return sorted(skills,
        key=lambda k:skills[k]["wrong"]-skills[k]["correct"],
        reverse=True)[0]

def retrieve_context(chunks,topic):
    for c in chunks:
        if topic.lower() in c.lower():
            return c
    return chunks[0] if chunks else ""

# ---------------- SIDEBAR ----------------
user=st.sidebar.selectbox("Student", list(db.keys()))
menu=st.sidebar.radio("Menu",
["Upload","Quiz","Step Grading","Progress"])

user_data=db[user]

# ---------------- UPLOAD ----------------
if menu=="Upload":
    file=st.file_uploader("Upload syllabus PDF")
    if file:
        text=extract_pdf(file)
        user_data["syllabus_chunks"]=chunk_text(text)
        save_db(db)
        st.success("Syllabus stored permanently!")

# ---------------- QUIZ ----------------
elif menu=="Quiz":

    if not user_data["syllabus_chunks"]:
        st.warning("Upload syllabus first")
        st.stop()

    if st.button("Generate Question"):

        topic=weakest_topic(user_data["skills"])
        context=retrieve_context(
            user_data["syllabus_chunks"],topic)

        prompt=f"""
Create ONE Form 2 math MCQ.
Topic:{topic}

Return JSON:
{{"topic":"","question":"",
"options":{{"A":"","B":"","C":"","D":"","E":""}},
"answer":"A","explanation":""}}

Reference:
{context}
"""

     try:
    response = model.generate_content(prompt)
    q = json.loads(response.text)

except Exception as e:
    st.error("AI temporarily unavailable. Please try again.")
    st.stop()
    
        st.session_state.q=q

    if "q" in st.session_state:
        q=st.session_state.q
        st.write(q["question"])

        for k,v in q["options"].items():
            st.write(f"{k}. {v}")

        ans=st.text_input("Answer").upper()

        if st.button("Check"):
            topic=q["topic"]
            skills=user_data["skills"]

            if topic not in skills:
                skills[topic]={"correct":0,"wrong":0}

            if ans==q["answer"]:
                skills[topic]["correct"]+=1
                st.success("Correct!")
                user_data["score"]+=1
            else:
                skills[topic]["wrong"]+=1
                st.error("Wrong")
                st.write(q["explanation"])

            save_db(db)
            del st.session_state.q

# ---------------- STEP GRADING ----------------
elif menu=="Step Grading":

    question="Solve 2x+10=30"
    st.write(question)

    canvas=st_canvas(height=400)

    if st.button("Analyze"):
        img=Image.fromarray(canvas.image_data.astype("uint8"))

        prompt=f"""
Check student's solution steps for:
{question}

Explain mistake and guide.
"""

        res=model.generate_content([prompt,img])
        st.write(res.text)

# ---------------- PROGRESS ----------------
elif menu=="Progress":
    st.metric("Score",user_data["score"])

    if user_data["skills"]:
        st.bar_chart(
            {k:v["correct"]
             for k,v in user_data["skills"].items()}
        )
