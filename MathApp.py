import streamlit as st
from streamlit_drawable_canvas import st_canvas
import PyPDF2
from google import genai
from PIL import Image
import io

# 1. PAGE SETUP
st.set_page_config(layout="wide", page_title="Math Mastery AI")

# 2. LOAD AI BRAIN
if "GEMINI_API_KEY" in st.secrets:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("API Key missing in secrets.toml! Please check your folder.")
    st.stop()

# 3. INITIALIZE MULTI-USER MEMORY
if "db" not in st.session_state:
    st.session_state.db = {
        "User 1": {"score": 0, "syllabus": "", "wrong_answers": []},
        "User 2": {"score": 0, "syllabus": "", "wrong_answers": []}
    }
if "current_q" not in st.session_state:
    st.session_state.current_q = None

# 4. SIDEBAR NAVIGATION
st.sidebar.title("🎮 Math Explorer")
current_user = st.sidebar.selectbox("Active Student:", ["User 1", "User 2"])
menu = st.sidebar.radio("Go to:", ["File", "Quiz", "Comprehension", "Revision"])

user_data = st.session_state.db[current_user]
st.sidebar.markdown("---")
st.sidebar.write(f"📊 **{current_user} Progress**")
st.sidebar.write(f"Points: {user_data['score']}")
st.sidebar.write(f"Mistakes tracked: {len(user_data['wrong_answers'])}")

# ---------------------------------------------------------
# MENU 1: FILE (Syllabus Upload)
# ---------------------------------------------------------
if menu == "File":
    st.header(f"📂 Syllabus Manager - {current_user}")
    uploaded_file = st.file_uploader("Upload School Syllabus or Worksheet (PDF)", type=["pdf"])
    
    if uploaded_file:
        with st.spinner("Learning syllabus..."):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = "".join([page.extract_text() for page in pdf_reader.pages])
            st.session_state.db[current_user]["syllabus"] = text
            st.success("Syllabus Updated! AI now knows your specific math level.")
            st.text_area("Preview of Syllabus Text:", text[:500] + "...", height=150)

# ---------------------------------------------------------
# MENU 2: QUIZ (Multiple Choice)
# ---------------------------------------------------------
elif menu == "Quiz":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("📝 Multiple Choice Quiz")
        if st.button("Generate Question"):
            context = user_data["syllabus"] if user_data["syllabus"] else "General Form 2 Malaysia Math"
            prompt = f"Based on: {context[:1000]}, generate 1 math MCQ with 5 options (A-E). Clearly state the correct answer at the end."
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt])
            st.session_state.current_q = res.text
            
        if st.session_state.current_q:
            st.info(st.session_state.current_q)
            ans = st.text_input("Your Answer (A-E):").upper()
            if st.button("Submit Answer"):
                if ans in st.session_state.current_q: # Simple check for demo
                    st.balloons()
                    st.success("Congratulations, you are correct! Bravo! 🎉")
                    st.session_state.db[current_user]["score"] += 1
                else:
                    st.error("Please try again. 💡")
                    st.session_state.db[current_user]["wrong_answers"].append(st.session_state.current_q)

    with col2:
        st_canvas(fill_color="white", stroke_width=2, height=500, key="quiz_canvas")

# ---------------------------------------------------------
# MENU 3: COMPREHENSION (Whiteboard Analysis)
# ---------------------------------------------------------
elif menu == "Comprehension":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("🧠 Comprehension Mode")
        q = "Solve: If a book costs RM 15 and a pen costs RM 4, how much for 2 books and 3 pens?"
        st.write(f"**Question:** {q}")
        submit = st.button("Submit Workings")

    with col2:
        canvas_result = st_canvas(fill_color="white", stroke_width=3, height=500, key="comp_canvas")

    if submit and canvas_result.image_data is not None:
        with st.spinner("Analyzing your steps..."):
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert('RGB')
            prompt = f"Question: {q}. Analyze the handwritten steps in this image. Is the logic correct? Explain why."
            response = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, img])
            st.write(response.text)

# ---------------------------------------------------------
# MENU 4: REVISION (Review Mistakes)
# ---------------------------------------------------------
elif menu == "Revision":
    st.header(f"🔄 Revision - {current_user}")
    if not user_data["wrong_answers"]:
        st.write("No mistakes yet! Keep practicing. ✅")
    else:
        for idx, mistake in enumerate(user_data["wrong_answers"]):
            with st.expander(f"Mistake #{idx+1}"):
                st.write(mistake)
                st.write("---")
                st.write("Try solving this again on your whiteboard!")