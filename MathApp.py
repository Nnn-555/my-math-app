import streamlit as st
from streamlit_drawable_canvas import st_canvas
import PyPDF2
from google import genai
from PIL import Image
import io

# 1. PAGE SETUP - This controls the name and icon on the Android Home Screen
st.set_page_config(
    layout="wide", 
    page_title="Math Mastery AI", 
    page_icon="📐"
)

# 2. LOAD AI BRAIN - Using the modern google-genai library
if "GEMINI_API_KEY" in st.secrets:
    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as e:
        st.error(f"AI Setup Error: {e}")
        st.stop()
else:
    st.error("API Key missing in Streamlit Cloud Secrets!")
    st.stop()

# 3. INITIALIZE MULTI-USER MEMORY
if "user_db" not in st.session_state:
    st.session_state.user_db = {
        "User 1": {"score": 0, "syllabus": "", "wrong_answers": []},
        "User 2": {"score": 0, "syllabus": "", "wrong_answers": []}
    }
if "current_q" not in st.session_state:
    st.session_state.current_q = None

# 4. SIDEBAR NAVIGATION
st.sidebar.title("📐 Math Explorer")
current_user = st.sidebar.selectbox("Active Student:", ["User 1", "User 2"])
menu = st.sidebar.radio("Go to:", ["📁 File", "📝 Quiz", "🧠 Comprehension", "🔄 Revision"])

user_data = st.session_state.user_db[current_user]
st.sidebar.markdown("---")
st.sidebar.write(f"📊 **{current_user} Progress**")
st.sidebar.write(f"Points: {user_data['score']}")
st.sidebar.write(f"Mistakes tracked: {len(user_data['wrong_answers'])}")

# ---------------------------------------------------------
# MENU 1: FILE (Syllabus Upload)
# ---------------------------------------------------------
if menu == "📁 File":
    st.header(f"Syllabus Manager - {current_user}")
    st.info("💡 Tip: Download your PDF from Google Drive to this tablet first, then click below to upload.")
    
    uploaded_file = st.file_uploader("Upload School Syllabus (PDF)", type=["pdf"])
    
    if uploaded_file:
        with st.spinner("AI is reading the syllabus..."):
            try:
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                text = "".join([page.extract_text() for page in pdf_reader.pages])
                st.session_state.user_db[current_user]["syllabus"] = text
                st.success("Syllabus Updated! AI now knows your specific math level.")
            except Exception as e:
                st.error("Could not read PDF. Please try a different file.")

# ---------------------------------------------------------
# MENU 2: QUIZ (Multiple Choice)
# ---------------------------------------------------------
elif menu == "📝 Quiz":
    col1, col2 = st.columns([1, 1.5])
    with col1:
        st.subheader("Multiple Choice Quiz")
        if st.button("Generate New Question"):
            context = user_data["syllabus"] if user_data["syllabus"] else "General Form 2 Malaysia Math"
            # Structured prompt for consistency
            prompt = (
                f"Based on this syllabus: {context[:1500]}\n\n"
                "Task: Create ONE math multiple choice question (MCQ) for a 13-year-old student. "
                "Include 5 options (A to E). At the very end of your response, write 'Correct Answer: [Letter]'."
            )
            
            with st.spinner("Creating question..."):
                try:
                    res = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
                    st.session_state.current_q = res.text
                except Exception as e:
                    st.error("AI is busy. Please tap 'Generate' again.")

        if st.session_state.current_q:
            st.markdown(st.session_state.current_q)
            ans = st.text_input("Type your answer (A, B, C, D, or E):").strip().upper()
            
            if st.button("Check Answer"):
                # Simple logic to find the answer in the text
                if f"CORRECT ANSWER: {ans}" in st.session_state.current_q.upper():
                    st.balloons()
                    st.success("Correct! Well done! 🎉")
                    st.session_state.user_db[current_user]["score"] += 1
                else:
                    st.error("Not quite right. I've added this to your Revision list.")
                    st.session_state.user_db[current_user]["wrong_answers"].append(st.session_state.current_q)

    with col2:
        st.write("Scratchpad (Draw your workings here):")
        st_canvas(fill_color="white", stroke_width=2, stroke_color="black", height=450, key="quiz_canvas")

# ---------------------------------------------------------
# MENU 3: COMPREHENSION (Handwriting Analysis)
# ---------------------------------------------------------
elif menu == "🧠 Comprehension":
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Step-by-Step Analysis")
        # You can change this question manually if needed
        target_q = "Solve for x: 5x + 10 = 35" 
        st.write(f"**Question:** {target_q}")
        
        if st.button("Check My Logic"):
            st.session_state.analyze = True
        if st.button("🗑️ Clear Whiteboard"):
            st.rerun()

    with col2:
        canvas_result = st_canvas(
            fill_color="white", stroke_width=4, stroke_color="black",
            background_color="#ffffff", height=500, drawing_mode="freedraw", key="comp_canvas"
        )

    if st.session_state.get("analyze") and canvas_result.image_data is not None:
        with st.spinner("AI is examining your handwriting..."):
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert('RGB')
            prompt = f"The math question is: {target_q}. Look at the handwritten steps in this image. Explain if the steps are logically correct. Be very encouraging like a kind teacher."
            
            try:
                response = client.models.generate_content(model="gemini-1.5-flash", contents=[prompt, img])
                st.info(response.text)
                st.session_state.analyze = False
            except Exception as e:
                st.error("AI couldn't see the image clearly. Try drawing thicker lines.")

# ---------------------------------------------------------
# MENU 4: REVISION (Mistakes Tracker)
# ---------------------------------------------------------
elif menu == "🔄 Revision":
    st.header(f"Revision List for {current_user}")
    if not user_data["wrong_answers"]:
        st.success("No mistakes found! You're a math master. ✅")
    else:
        st.write("Review the questions you missed earlier:")
        for i, mistake in enumerate(user_data["wrong_answers"]):
            with st.expander(f"Mistake #{i+1}"):
                st.write(mistake)
