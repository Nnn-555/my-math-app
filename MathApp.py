import streamlit as st
from streamlit_drawable_canvas import st_canvas
import PyPDF2
from google import genai
from PIL import Image
import io

# 1. PAGE SETUP
st.set_page_config(
    layout="wide", 
    page_title="Math Mastery AI", 
    page_icon="📐"
)

# 2. LOAD AI BRAIN
if "GEMINI_API_KEY" in st.secrets:
    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"].strip())
    except Exception as e:
        st.error(f"AI Setup Error: {e}")
        st.stop()
else:
    st.error("API Key missing in Streamlit Cloud Secrets!")
    st.stop()

# 3. INITIALIZE MEMORY (The "Digital Notebook")
if "user_db" not in st.session_state:
    st.session_state.user_db = {
        "User 1": {"score": 0, "syllabus": "", "wrong_answers": []},
        "User 2": {"score": 0, "syllabus": "", "wrong_answers": []}
    }
if "current_q" not in st.session_state:
    st.session_state.current_q = None

# 4. SIDEBAR
st.sidebar.title("📐 Math Explorer")
current_user = st.sidebar.selectbox("Active Student:", ["User 1", "User 2"])
menu = st.sidebar.radio("Go to:", ["📁 File", "📝 Quiz", "🧠 Comprehension", "🔄 Revision"])

user_data = st.session_state.user_db[current_user]

# ---------------------------------------------------------
# MENU 1: FILE (Syllabus Upload)
# ---------------------------------------------------------
if menu == "📁 File":
    st.header(f"Syllabus Manager - {current_user}")
    
    if user_data["syllabus"]:
        st.success("✅ Syllabus is loaded! You can now start the Quiz.")
        if st.button("Delete and Upload New PDF"):
            st.session_state.user_db[current_user]["syllabus"] = ""
            st.rerun()
    else:
        st.info("💡 Please upload a Math PDF to help the AI learn your school topics.")
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        
        if uploaded_file:
            with st.spinner("Reading PDF..."):
                try:
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    text = "".join([page.extract_text() for page in pdf_reader.pages])
                    st.session_state.user_db[current_user]["syllabus"] = text
                    st.success("Syllabus Saved! Go to the Quiz tab now.")
                except Exception as e:
                    st.error("Error reading file. Try a different PDF.")

# ---------------------------------------------------------
# MENU 2: QUIZ
# ---------------------------------------------------------
elif menu == "📝 Quiz":
    st.subheader("Multiple Choice Quiz")
    
    if not user_data["syllabus"]:
        st.warning("⚠️ No syllabus found! Please upload a PDF in the 'File' tab first.")
    else:
        if st.button("Generate New Question"):
            context = user_data["syllabus"]
            # FIXED SYNTAX BELOW:
            prompt = f"Using this text: {context[:1500]}. Create ONE Form 2 Math MCQ with 5 options (A-E). End with 'Correct Answer: [Letter]'."
            
            with st.spinner("AI is thinking..."):
                try:
                    res = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
                    st.session_state.current_q = res.text
                except Exception as e:
                    st.error(f"AI Busy: {e}")

        if st.session_state.current_q:
            st.markdown(st.session_state.current_q)
            ans = st.text_input("Your Answer (A-E):").strip().upper()
            if st.button("Check"):
                if f"CORRECT ANSWER: {ans}" in st.session_state.current_q.upper():
                    st.balloons()
                    st.success("Correct! +1 Point")
                    st.session_state.user_db[current_user]["score"] += 1
                else:
                    st.error("Wrong. Adding to Revision.")
                    st.session_state.user_db[current_user]["wrong_answers"].append(st.session_state.current_q)

# ---------------------------------------------------------
# MENU 3: COMPREHENSION (Drawing)
# ---------------------------------------------------------
elif menu == "🧠 Comprehension":
    st.subheader("Handwriting Analysis")
    target_q = "Solve for x: 2x + 5 = 15"
    st.write(f"**Question:** {target_q}")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        canvas_result = st_canvas(
            fill_color="white", stroke_width=4, stroke_color="black",
            background_color="#ffffff", height=400, key="comp_canvas"
        )
    with col2:
        if st.button("Analyze My Work"):
            if canvas_result.image_data is not None:
                # Create a solid white background for the AI
                rgba_image = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                white_bg = Image.new("RGB", rgba_image.size, (255, 255, 255))
                white_bg.paste(rgba_image, mask=rgba_image.split()[3])
                
                try:
                    prompt = f"Question: {target_q}. Check these handwritten steps. Are they right?"
                    response = client.models.generate_content(model="gemini-1.5-flash", contents=[prompt, white_bg])
                    st.info(response.text)
                except Exception as e:
                    st.error(f"Error: {e}")
        if st.button("Clear Canvas"):
            st.rerun()

# ---------------------------------------------------------
# MENU 4: REVISION
# ---------------------------------------------------------
elif menu == "🔄 Revision":
    st.header(f"Mistakes Tracker - {current_user}")
    for mistake in user_data["wrong_answers"]:
        st.write("---")
        st.write(mistake)
