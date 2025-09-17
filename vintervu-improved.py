import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import json
import io
import PyPDF2
import speech_recognition as sr
import tempfile
import os
import time
import plotly.express as px
from datetime import datetime
import threading
import queue

# Database initialization
def init_database():
    conn = sqlite3.connect('vintervu.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            total_score INTEGER NOT NULL,
            max_score INTEGER NOT NULL,
            percentage REAL NOT NULL,
            feedback_data TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def register_user(username: str, email: str, password: str) -> bool:
    try:
        conn = sqlite3.connect('vintervu.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, hash_password(password))
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(email: str, password: str) -> bool:
    conn = sqlite3.connect('vintervu.db')
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE email = ?", (email,))
    result = cursor.fetchone()
    conn.close()
    if result and verify_password(password, result[0]):
        return True
    return False

def extract_text_from_pdf(file_content):
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return ""

def extract_text_from_docx(file_content):
    try:
        import docx2txt
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
            tmp_file.write(file_content)
            tmp_file.flush()
            text = docx2txt.process(tmp_file.name)
            os.unlink(tmp_file.name)
        return text
    except Exception as e:
        st.error(f"Error reading DOCX: {str(e)}")
        return ""

# Enhanced Voice Recognition Functions
def test_microphone():
    """Test if microphone is working"""
    try:
        r = sr.Recognizer()
        mic_list = sr.Microphone.list_microphone_names()
        st.info(f"Available microphones: {len(mic_list)}")
        for i, mic_name in enumerate(mic_list):
            st.write(f"{i}: {mic_name}")
        return True
    except Exception as e:
        st.error(f"Microphone test failed: {e}")
        return False

def speech_to_text_enhanced():
    """Enhanced speech to text with better error handling"""
    try:
        r = sr.Recognizer()
        
        # List available microphones
        mic_list = sr.Microphone.list_microphone_names()
        if not mic_list:
            st.error("❌ No microphones found! Please check your audio devices.")
            return ""
        
        # Use default microphone
        with sr.Microphone() as source:
            st.info("🎤 **Listening... Speak clearly now!**")
            st.write("📋 **Tips:**")
            st.write("• Speak clearly and at moderate pace")
            st.write("• Ensure you're in a quiet environment") 
            st.write("• Keep microphone close to your mouth")
            
            # Adjust for ambient noise
            with st.spinner("🔧 Adjusting for background noise..."):
                r.adjust_for_ambient_noise(source, duration=2)
            
            st.success("✅ Ready! Start speaking now...")
            
            # Listen for audio
            try:
                audio = r.listen(source, timeout=15, phrase_time_limit=45)
                st.info("🔄 Audio captured! Converting to text...")
            except sr.WaitTimeoutError:
                st.warning("⏰ No speech detected within 15 seconds. Please try again.")
                return ""
        
        # Convert to text using multiple services as fallback
        text = ""
        
        try:
            # Primary: Google Speech Recognition
            with st.spinner("🔄 Converting speech to text (Google)..."):
                text = r.recognize_google(audio)
                st.success("✅ Speech converted successfully!")
                return text
        except sr.UnknownValueError:
            st.warning("🤔 Google Speech Recognition couldn't understand the audio clearly.")
        except sr.RequestError as e:
            st.warning(f"⚠️ Google Speech Recognition service error: {e}")
        
        # Fallback: Try with different recognition services
        try:
            with st.spinner("🔄 Trying alternative speech recognition..."):
                # You can add other services here like Azure, IBM, etc.
                text = r.recognize_sphinx(audio)  # Offline recognition as fallback
                if text:
                    st.success("✅ Speech converted using offline recognition!")
                    return text
        except:
            pass
        
        st.error("❌ Could not convert speech to text. Please try typing your response.")
        return ""
        
    except Exception as e:
        st.error(f"❌ Speech recognition error: {str(e)}")
        st.info("💡 **Troubleshooting:**")
        st.write("1. Check microphone permissions in browser settings")
        st.write("2. Ensure microphone is not being used by other apps")
        st.write("3. Try refreshing the page and allowing microphone access")
        return ""

def test_voice_input():
    """Test voice input functionality without API key"""
    st.subheader("🎤 Voice Input Test")
    st.write("This is a simple test to check if your microphone and speech recognition is working.")
    
    if st.button("🎤 Test Voice Input", key="test_voice"):
        with st.spinner("Testing voice input..."):
            text = speech_to_text_enhanced()
            if text:
                st.success(f"✅ **Voice Input Successful!**")
                st.write(f"**You said:** *{text}*")
                st.balloons()
            else:
                st.error("❌ Voice input test failed. Please check your microphone setup.")

def text_to_speech_js(text):
    """Generate JavaScript code for text-to-speech"""
    # Clean text for JavaScript
    clean_text = text.replace('"', '\\"').replace('\n', ' ')
    
    js_code = f"""
    <script>
    function speakText() {{
        if ('speechSynthesis' in window) {{
            const utterance = new SpeechSynthesisUtterance("{clean_text}");
            utterance.rate = 0.8;
            utterance.pitch = 1;
            utterance.volume = 0.8;
            
            // Get available voices
            const voices = speechSynthesis.getVoices();
            
            // Try to use a good English voice
            const englishVoice = voices.find(voice => 
                voice.lang.includes('en') && voice.name.includes('Female')
            ) || voices.find(voice => voice.lang.includes('en'));
            
            if (englishVoice) {{
                utterance.voice = englishVoice;
            }}
            
            speechSynthesis.speak(utterance);
        }} else {{
            alert('Speech synthesis not supported in your browser');
        }}
    }}
    
    // Auto-call the function
    speakText();
    </script>
    """
    return js_code

def speak_question(question_text):
    """Add text-to-speech for questions"""
    if st.button("🔊 Read Question Aloud", key=f"speak_{hash(question_text)}"):
        # Use HTML/JS for text-to-speech
        st.components.v1.html(
            text_to_speech_js(question_text),
            height=0,
        )
        st.success("🔊 Question is being read aloud...")

def extract_skills_and_projects_with_gemini(text: str, api_key: str) -> dict:
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
Analyze this resume text and extract:
1. Technical skills (programming languages, frameworks, tools, technologies, software)
2. Project titles and their key technologies used
3. Domain expertise areas

Respond in JSON format:
{{
    "skills": ["Skill1", "Skill2", "Skill3", ...],
    "projects": [
        {{"title": "Project Name", "technologies": ["Tech1", "Tech2"]}},
        ...
    ],
    "domains": ["Domain1", "Domain2", ...]
}}

Resume Text:
{text[:4000]}
        """
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        json_string = response_text[json_start:json_end]
        result = json.loads(json_string)
        
        return {
            'skills': result.get('skills', []),
            'projects': result.get('projects', []),
            'domains': result.get('domains', [])
        }
    except Exception as e:
        st.error(f"Error extracting information with Gemini: {str(e)}")
        return {'skills': [], 'projects': [], 'domains': []}

def infer_branch(skills):
    skill_set = set([skill.lower() for skill in skills])
    
    if any(skill in skill_set for skill in ['python', 'java', 'c++', 'javascript', 'sql', 'machine learning', 'aws', 'react', 'nodejs']):
        return 'Computer Science'
    elif any(skill in skill_set for skill in ['matlab', 'vlsi', 'analog circuits', 'digital logic', 'embedded']):
        return 'Electronics'
    elif any(skill in skill_set for skill in ['plc', 'scada', 'power systems', 'control systems']):
        return 'Electrical'
    elif any(skill in skill_set for skill in ['autocad', 'staad', 'concrete', 'structural']):
        return 'Civil'
    elif any(skill in skill_set for skill in ['thermodynamics', 'fluid mechanics', 'mechanical design']):
        return 'Mechanical'
    else:
        return 'General Engineering'

def generate_technical_questions_enhanced(skills, projects, branch, api_key, asked_questions=[]):
    """Generate enhanced technical questions based on specific skills and projects"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        skill_list = ', '.join(skills[:10]) if skills else 'basic programming concepts'
        project_info = ""
        if projects:
            for project in projects[:3]:
                if isinstance(project, dict):
                    project_info += f"Project: {project.get('title', 'Unknown')} using {', '.join(project.get('technologies', []))}\n"
                else:
                    project_info += f"Project: {project}\n"
        
        core_topics = get_core_topics(branch)
        
        prompt = f"""
Generate 7 TECHNICAL interview questions for a {branch} candidate based on:

CANDIDATE'S SKILLS: {skill_list}
PROJECTS: 
{project_info}
CORE {branch.upper()} TOPICS: {', '.join(core_topics)}

REQUIREMENTS:
1. Focus 70% on candidate's actual skills and project technologies
2. Include 30% core {branch} fundamentals
3. Ask about specific implementations, not just definitions
4. Include scenario-based questions
5. Each question should be practical and implementation-focused
6. Avoid these already asked topics: {', '.join(asked_questions) if asked_questions else 'none'}

Format: Return only the questions, one per line, numbered 1-7.
Make questions specific to the skills mentioned above.
        """
        
        response = model.generate_content(prompt)
        questions = []
        for line in response.text.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering
                question = line.split('.', 1)[-1].strip() if '.' in line else line.strip('- ')
                questions.append(question)
        
        # Filter out similar questions
        def similarity(a, b):
            a_words = set(a.lower().split())
            b_words = set(b.lower().split())
            common = a_words.intersection(b_words)
            return len(common) / max(len(a_words), len(b_words), 1)
        
        filtered_questions = []
        for q in questions:
            if not any(similarity(q, aq) > 0.6 for aq in asked_questions):
                filtered_questions.append(q)
        
        return filtered_questions[:5]
        
    except Exception as e:
        st.error(f"Error generating technical questions: {str(e)}")
        return [
            "Explain the architecture of your most complex project.",
            "How would you optimize the performance of your application?",
            "Describe a challenging bug you encountered and how you solved it."
        ]

def generate_project_based_questions(projects, skills, api_key, asked_questions=[]):
    """Generate questions specifically about candidate's projects"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        project_details = ""
        for project in projects[:3]:
            if isinstance(project, dict):
                project_details += f"- {project.get('title', 'Project')}: {', '.join(project.get('technologies', []))}\n"
            else:
                project_details += f"- {project}\n"
        
        prompt = f"""
Based on these projects and skills, generate 3 specific project-based interview questions:

PROJECTS:
{project_details}

SKILLS: {', '.join(skills[:8])}

Generate questions that ask about:
1. Technical challenges in these specific projects
2. Implementation decisions and trade-offs
3. How they used specific technologies mentioned

Questions should be specific to these projects, not generic.
Return only the questions, one per line.
        """
        
        response = model.generate_content(prompt)
        questions = [line.strip() for line in response.text.split('\n') if line.strip()]
        return questions[:3]
        
    except Exception as e:
        st.error(f"Error generating project questions: {str(e)}")
        return ["Tell me about the biggest challenge in your recent project."]

def generate_dynamic_followup(response, skills, projects, api_key):
    """Generate follow-up questions based on the candidate's response"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
Based on this candidate response: "{response}"
And their skills: {', '.join(skills[:5])}
Generate ONE specific follow-up question that digs deeper into their technical knowledge.

The follow-up should:
1. Be more specific than the original answer
2. Test deeper technical understanding
3. Ask about implementation details or edge cases
4. Be directly related to their mentioned skills

Return only the question, nothing else.
        """
        
        followup = model.generate_content(prompt)
        return followup.text.strip()
        
    except Exception as e:
        st.error(f"Error generating follow-up: {str(e)}")
        return "Can you elaborate on the technical implementation details?"

def get_core_topics(branch):
    core_map = {
        'Computer Science': ['Data Structures', 'Algorithms', 'Operating Systems', 'DBMS', 'Computer Networks', 'OOP', 'System Design'],
        'Electronics': ['Analog Circuits', 'Digital Logic', 'Microprocessors', 'Embedded Systems', 'VLSI', 'Signal Processing'],
        'Electrical': ['Circuits', 'Control Systems', 'Signal Processing', 'Power Systems', 'Electromagnetics', 'Power Electronics'],
        'Mechanical': ['Thermodynamics', 'Fluid Mechanics', 'Heat Transfer', 'Strength of Materials', 'Machine Design', 'Manufacturing'],
        'Civil': ['Structural Analysis', 'Concrete Technology', 'Geotechnical Engineering', 'Transportation Engineering', 'Environmental Engineering'],
    }
    return core_map.get(branch, ['Engineering Fundamentals'])

def evaluate_response_enhanced(question, response, api_key):
    """Enhanced evaluation with detailed feedback"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Score evaluation
        score_prompt = f"""
Evaluate this technical interview response:
Question: "{question}"
Answer: "{response}"

Score from 0-10 considering:
- Technical accuracy (40%)
- Depth of explanation (30%)
- Clarity and structure (20%)
- Practical insight (10%)

Return only the numeric score (0-10).
        """
        
        score_response = model.generate_content(score_prompt)
        score_text = score_response.text.strip()
        score = int(score_text) if score_text.isdigit() and 0 <= int(score_text) <= 10 else 5
        
        # Enhanced detailed feedback
        feedback_prompt = f"""
Analyze this technical interview response in detail:
Question: "{question}"
Answer: "{response}"

Provide comprehensive feedback in the following format as JSON:
{{
    "technical_strengths": "Detailed analysis of what was technically correct and well-explained (3-4 sentences)",
    "communication_quality": "Assessment of clarity, structure, and communication skills shown (2-3 sentences)",
    "knowledge_gaps": "Specific areas where knowledge could be improved or was missing (3-4 sentences)",
    "implementation_insights": "Comments on practical understanding and real-world application (2-3 sentences)",
    "detailed_suggestions": "Specific, actionable recommendations for improvement (4-5 sentences)",
    "industry_relevance": "How well the answer reflects industry standards and best practices (2-3 sentences)",
    "next_learning_steps": "Concrete next steps for skill development (3-4 specific recommendations)"
}}

Make each section detailed and specific to this particular response.
        """
        
        feedback_response = model.generate_content(feedback_prompt)
        feedback_text = feedback_response.text
        
        try:
            json_start = feedback_text.find('{')
            json_end = feedback_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_string = feedback_text[json_start:json_end]
                feedback_data = json.loads(json_string)
            else:
                feedback_data = {
                    "technical_strengths": "You demonstrated a solid understanding of the basic concepts and showed good problem-solving approach. Your answer covered the key technical points adequately.",
                    "communication_quality": "Your explanation was clear and well-structured. You communicated your ideas in a logical sequence.",
                    "knowledge_gaps": "There are opportunities to dive deeper into the technical implementation details. Consider exploring edge cases and potential challenges that might arise in real-world scenarios.",
                    "implementation_insights": "Your answer shows practical awareness, but could benefit from more specific examples of how this would work in production environments.",
                    "detailed_suggestions": "To strengthen your answer, consider including specific examples, discussing performance implications, mentioning relevant tools or frameworks, and addressing potential scalability concerns. Practice explaining complex concepts with concrete scenarios.",
                    "industry_relevance": "Your response aligns with current industry practices. Consider staying updated with the latest trends and best practices in this area.",
                    "next_learning_steps": "1. Practice implementing similar solutions in code, 2. Study real-world case studies, 3. Explore advanced features and optimization techniques"
                }
        except:
            feedback_data = {
                "technical_strengths": "You demonstrated a solid understanding of the basic concepts and showed good problem-solving approach. Your answer covered the key technical points adequately and reflected good foundational knowledge.",
                "communication_quality": "Your explanation was clear and well-structured. You communicated your ideas in a logical sequence that was easy to follow.",
                "knowledge_gaps": "There are opportunities to dive deeper into the technical implementation details. Consider exploring edge cases, error handling scenarios, and potential challenges that might arise in real-world applications.",
                "implementation_insights": "Your answer shows practical awareness, but could benefit from more specific examples of how this would work in production environments with real constraints and requirements.",
                "detailed_suggestions": "To strengthen your answer, consider including specific code examples, discussing performance implications and optimization strategies, mentioning relevant tools or frameworks, and addressing potential scalability concerns. Practice explaining complex concepts with concrete scenarios and real-world applications.",
                "industry_relevance": "Your response aligns with current industry practices and shows good awareness of standard approaches. Consider staying updated with the latest trends and best practices.",
                "next_learning_steps": "1. Practice implementing similar solutions hands-on with code, 2. Study real-world case studies and architecture examples, 3. Explore advanced features and optimization techniques in this domain"
            }
        
        return {
            'score': score,
            'technical_strengths': feedback_data.get('technical_strengths', 'Good technical foundation shown'),
            'communication_quality': feedback_data.get('communication_quality', 'Clear communication style'),
            'knowledge_gaps': feedback_data.get('knowledge_gaps', 'Some areas for technical depth improvement'),
            'implementation_insights': feedback_data.get('implementation_insights', 'Shows practical understanding'),
            'detailed_suggestions': feedback_data.get('detailed_suggestions', 'Continue practicing and studying'),
            'industry_relevance': feedback_data.get('industry_relevance', 'Aligned with industry standards'),
            'next_learning_steps': feedback_data.get('next_learning_steps', 'Keep learning and practicing')
        }
        
    except Exception as e:
        st.error(f"Error evaluating response: {str(e)}")
        return {
            'score': 5,
            'technical_strengths': 'Unable to evaluate technical accuracy due to system error. Your response shows effort and engagement with the question.',
            'communication_quality': 'Communication style appears clear and structured based on visible content.',
            'knowledge_gaps': 'System unable to assess specific knowledge gaps. Consider reviewing fundamental concepts and implementation details.',
            'implementation_insights': 'Consider focusing on practical applications and real-world implementation scenarios.',
            'detailed_suggestions': 'Due to evaluation system error, recommend reviewing the question topic thoroughly, practicing with code examples, and studying best practices in this area.',
            'industry_relevance': 'Stay updated with current industry standards and practices in this technical area.',
            'next_learning_steps': '1. Review core concepts, 2. Practice hands-on implementation, 3. Study industry case studies'
        }

def analyze_resume_for_job(resume_text, job_role, api_key):
    role_skills = {
        'data scientist': ['python', 'machine learning', 'data analysis', 'pandas', 'numpy', 'tensorflow', 'statistics'],
        'machine learning engineer': ['python', 'machine learning', 'tensorflow', 'scikit-learn', 'deep learning', 'pytorch'],
        'ai engineer': ['python', 'neural networks', 'nlp', 'computer vision', 'tensorflow', 'keras', 'pytorch'],
        'web developer': ['html', 'css', 'javascript', 'react', 'nodejs', 'express', 'mongodb'],
        'frontend developer': ['html', 'css', 'javascript', 'react', 'redux', 'tailwind'],
        'backend developer': ['python', 'flask', 'django', 'rest api', 'postgresql', 'mysql'],
        'full stack developer': ['html', 'css', 'javascript', 'nodejs', 'react', 'mongodb', 'express', 'flask'],
        'software engineer': ['data structures', 'algorithms', 'oop', 'python', 'java', 'c++'],
        'data analyst': ['excel', 'sql', 'power bi', 'tableau', 'python', 'pandas'],
        'devops engineer': ['linux', 'docker', 'kubernetes', 'jenkins', 'aws', 'terraform', 'ci/cd'],
        'cloud engineer': ['aws', 'azure', 'gcp', 'devops', 'linux', 'cloudformation'],
        'mobile app developer': ['flutter', 'react native', 'android', 'ios', 'dart', 'kotlin', 'swift'],
    }
    
    skill_suggestions = {
        'python': 'Enhance Python by building small projects or solving problems on LeetCode.',
        'machine learning': 'Take an ML course on Coursera or Udemy and build projects.',
        'tensorflow': 'Practice TensorFlow by building a neural network model.',
        'docker': 'Learn Docker by containerizing a sample application.',
        'aws': 'Start with AWS Free Tier and deploy a basic application.',
        'html': 'Build a simple portfolio website to showcase your HTML/CSS skills.',
        'javascript': 'Make interactive web pages with JS, like a calculator or to-do list.',
        'react': 'Build a React-based UI project like a blog or resume site.',
        'sql': 'Practice SQL queries using online playgrounds like Mode Analytics or W3Schools.',
    }
    
    extracted_data = extract_skills_and_projects_with_gemini(resume_text, api_key)
    resume_skills = [skill.lower() for skill in extracted_data['skills']]
    required_skills = role_skills.get(job_role.lower(), [])
    
    found_skills = [skill for skill in required_skills if skill in resume_skills]
    missing_skills = [skill for skill in required_skills if skill not in resume_skills]
    
    score = (len(found_skills) / len(required_skills)) * 100 if required_skills else 0
    
    suggestions = [
        skill_suggestions.get(skill, f"Consider learning {skill} to improve your profile.")
        for skill in missing_skills[:5]
    ]
    
    return {
        'role': job_role,
        'score': round(score, 2),
        'found_keywords': found_skills,
        'missing_keywords': missing_skills,
        'suggestions': suggestions
    }

def save_feedback(email: str, total_score: int, max_score: int, percentage: float, feedback_data: dict):
    try:
        conn = sqlite3.connect('vintervu.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedback (email, total_score, max_score, percentage, feedback_data) VALUES (?, ?, ?, ?, ?)",
            (email, total_score, max_score, percentage, json.dumps(feedback_data))
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error saving feedback: {str(e)}")
        return False

def get_user_feedback(email: str):
    try:
        conn = sqlite3.connect('vintervu.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT total_score, max_score, percentage, feedback_data, timestamp FROM feedback WHERE email = ? ORDER BY timestamp DESC",
            (email,)
        )
        results = cursor.fetchall()
        conn.close()
        
        feedback_list = []
        for result in results:
            feedback_list.append({
                'total_score': result[0],
                'max_score': result[1],
                'percentage': result[2],
                'feedback_data': json.loads(result[3]) if result[3] else {},
                'timestamp': result[4]
            })
        return feedback_list
    except Exception as e:
        st.error(f"Error fetching feedback: {str(e)}")
        return []

# Initialize database
init_database()

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'current_page' not in st.session_state:
    st.session_state.current_page = "🏠 Home"
if 'interview_state' not in st.session_state:
    st.session_state.interview_state = {
        'active': False,
        'skills': [],
        'projects': [],
        'branch': '',
        'questions': [],
        'responses': [],
        'current_question_index': 0,
        'feedback': [],
        'scores': [],
        'question_type': 'technical'
    }

# Page configuration
st.set_page_config(
    page_title="VIntervu - AI Interview Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
body, .main {
    background-color: #181924 !important; /* keep background dark */
}

.main-header {
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
    border-radius: 10px;
    color: #fff;
    text-align: center;
    margin-bottom: 2rem;
}

/* Card styling for features */
.interview-card {
    background: #eaf0fa; /* very light blue for contrast */
    padding: 1.5rem;
    border-radius: 15px;
    border-left: 5px solid #667eea;
    margin: 1rem 0;
    /* Drop shadow for better separation */
    box-shadow: 0 2px 8px rgba(60,60,80,0.06);
}

.interview-card h3 {
    color: #24243d !important;    /* dark headings for readability */
    font-weight: 700;
    margin-bottom: 0.5rem;
    letter-spacing: 0.5px;
}

.interview-card p {
    color: #222440 !important;    /* dark regular text */
    font-weight: 500;
}

/* For section titles below cards */
.enhanced-features-title {
    color: #fff !important;
    font-size: 1.4rem;
    font-weight: 700;
    margin-top: 2.5rem;
    margin-bottom: 1rem;
    letter-spacing: 0.5px;
}

.features-text {
    color: #fff !important;
    font-size: 1.1rem;
}

</style>
""", unsafe_allow_html=True)


# Sidebar Navigation
st.sidebar.title("🤖 VIntervu Navigation")

if st.session_state.logged_in:
    st.sidebar.success(f"Welcome, {st.session_state.user_email}!")
    
    # Navigation with direct state management
    nav_options = ["🏠 Home", "📄 Resume Upload", "🎯 Resume Analyzer", "🎤 Voice Test", "💬 Interview", "📊 Dashboard", "🔓 Logout"]
    selected_page = st.sidebar.selectbox("Navigate to:", nav_options, index=nav_options.index(st.session_state.current_page) if st.session_state.current_page in nav_options else 0)
    
    if selected_page != st.session_state.current_page:
        st.session_state.current_page = selected_page
        if selected_page == "🔓 Logout":
            st.session_state.logged_in = False
            st.session_state.user_email = ""
            st.session_state.current_page = "🏠 Home"
            st.session_state.interview_state = {
                'active': False,
                'skills': [],
                'projects': [],
                'branch': '',
                'questions': [],
                'responses': [],
                'current_question_index': 0,
                'feedback': [],
                'scores': [],
                'question_type': 'technical'
            }
        st.rerun()
    
    page = selected_page
else:
    nav_options = ["🏠 Home", "🔐 Login", "📝 Signup", "🎯 Resume Analyzer", "🎤 Voice Test"]
    page = st.sidebar.selectbox("Navigate to:", nav_options)

# Main Application Logic
if page == "🏠 Home":
    st.markdown("""
    <div class="main-header">
        <h1>🤖 VIntervu - AI Interview Bot</h1>
        <p style="font-size: 1.2rem; margin-top: 1rem;">Practice to Perfection, Speak with Direction ✨</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="interview-card">
            <h3>🎯 AI-Powered Questions</h3>
            <p>Get personalized interview questions based on your resume skills and projects using advanced AI technology.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="interview-card">
            <h3>🎤 Voice Input & Audio</h3>
            <p>Answer questions using voice input and listen to questions being read aloud for natural conversation flow.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="interview-card">
            <h3>📊 Comprehensive Feedback</h3>
            <p>Receive detailed, multi-dimensional feedback on your technical responses with actionable improvement suggestions.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.subheader("🚀 Enhanced Features")
    st.markdown("""
    - 🎤 **Advanced Voice Input**: Enhanced speech recognition with better error handling
    - 🔊 **Text-to-Speech**: Questions are read aloud for natural interview experience
    - 🧠 **Detailed AI Feedback**: Comprehensive feedback across multiple dimensions
    - 🧪 **Voice Testing**: Test your microphone without needing API key
    - 🔧 **Technical Deep-Dive**: Questions tailored to your specific skills and projects
    - 💡 **Smart Follow-ups**: AI generates relevant follow-up questions based on your answers
    - 📈 **Enhanced Analytics**: Detailed performance tracking with technical insights
    """)
    
    if not st.session_state.logged_in:
        st.info("Please login or signup to access all features!")

elif page == "🎤 Voice Test":
    st.title("🎤 Voice Input Test")
    
    st.markdown("""
    <div class="interview-card">
        <h3>🧪 Test Your Voice Setup</h3>
        <p>Test your microphone and speech recognition without needing an API key. This helps ensure everything works before starting your interview.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Microphone test
    st.subheader("🔧 Microphone Setup")
    if st.button("📋 Check Available Microphones"):
        test_microphone()
    
    # Voice input test
    test_voice_input()
    
    # Text-to-speech test
    st.subheader("🔊 Text-to-Speech Test")
    test_text = st.text_area("Enter text to test speech synthesis:", 
                             value="Hello! This is a test of the text-to-speech functionality. How does this sound?",
                             height=100)
    
    if st.button("🔊 Test Speech Output"):
        st.components.v1.html(
            text_to_speech_js(test_text),
            height=0,
        )
        st.success("🔊 Text is being read aloud...")
    
    # Troubleshooting section
    st.subheader("🛠️ Troubleshooting")
    st.markdown("""
    **If voice input isn't working:**
    - ✅ Check browser microphone permissions
    - ✅ Ensure no other apps are using the microphone
    - ✅ Try refreshing the page
    - ✅ Use Chrome or Firefox for best compatibility
    - ✅ Check your system microphone settings
    
    **If text-to-speech isn't working:**
    - ✅ Ensure browser supports speech synthesis
    - ✅ Check system volume settings
    - ✅ Try a different browser if needed
    """)

elif page == "🔐 Login":
    st.title("Login to VIntervu")
    
    with st.form("login_form"):
        email = st.text_input("📧 Email", placeholder="Enter your email")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
        submit_button = st.form_submit_button("🚀 Login")
        
        if submit_button:
            if email and password:
                if authenticate_user(email, password):
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.current_page = "🏠 Home"
                    st.success("Login successful! 🎉")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid email or password! ❌")
            else:
                st.error("Please fill in all fields! ⚠️")

elif page == "📝 Signup":
    st.title("Create Your Account")
    
    with st.form("signup_form"):
        username = st.text_input("👤 Username", placeholder="Enter your username")
        email = st.text_input("📧 Email", placeholder="Enter your email")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
        confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Confirm your password")
        submit_button = st.form_submit_button("✨ Create Account")
        
        if submit_button:
            if username and email and password and confirm_password:
                if password == confirm_password:
                    if len(password) >= 6:
                        if register_user(username, email, password):
                            st.success("Account created successfully! Please login. 🎉")
                        else:
                            st.error("Email already exists! Please use a different email. ❌")
                    else:
                        st.error("Password must be at least 6 characters long!")
                else:
                    st.error("Passwords do not match! ❌")
            else:
                st.error("Please fill in all fields!")

elif page == "🎯 Resume Analyzer":
    st.title("Resume Analyzer")
    
    api_key = st.text_input("🔑 Enter Gemini API Key", type="password",
                           help="Get your API key from https://makersuite.google.com/app/apikey")
    
    if api_key:
        job_roles = [
            "data scientist", "machine learning engineer", "ai engineer", "web developer",
            "frontend developer", "backend developer", "full stack developer", "software engineer",
            "data analyst", "devops engineer", "cloud engineer", "mobile app developer",
            "android developer", "ios developer", "ui ux designer", "qa engineer",
            "security analyst", "network engineer", "blockchain developer", "game developer",
            "database administrator"
        ]
        
        selected_role = st.selectbox("🎯 Select Target Job Role", job_roles)
        uploaded_file = st.file_uploader("📄 Upload Your Resume", type=['pdf', 'docx'])
        
        if uploaded_file and selected_role:
            if st.button("🚀 Analyze Resume"):
                with st.spinner("Analyzing your resume..."):
                    file_content = uploaded_file.read()
                    
                    if uploaded_file.type == "application/pdf":
                        resume_text = extract_text_from_pdf(file_content)
                    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        resume_text = extract_text_from_docx(file_content)
                    else:
                        st.error("Unsupported file format!")
                        resume_text = ""
                    
                    if resume_text:
                        analysis = analyze_resume_for_job(resume_text, selected_role, api_key)
                        
                        st.subheader(f"Analysis Results for {analysis['role'].title()}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("📊 Match Score", f"{analysis['score']}%")
                        with col2:
                            st.metric("✅ Found Skills", len(analysis['found_keywords']))
                        with col3:
                            st.metric("❌ Missing Skills", len(analysis['missing_keywords']))
                        
                        if analysis['found_keywords']:
                            st.success(f"✅ Skills Found: {', '.join(analysis['found_keywords'])}")
                        
                        if analysis['missing_keywords']:
                            st.error(f"❌ Missing Skills: {', '.join(analysis['missing_keywords'])}")
                        
                        if analysis['suggestions']:
                            st.markdown("💡 **Improvement Suggestions:**")
                            for i, suggestion in enumerate(analysis['suggestions'], 1):
                                st.markdown(f"{i}. {suggestion}")
    else:
        st.info("Please enter your Gemini API key to use the Resume Analyzer feature.")

elif page == "📄 Resume Upload" and st.session_state.logged_in:
    st.title("Upload Your Resume")
    
    api_key = st.text_input("🔑 Enter Gemini API Key", type="password",
                           help="Get your API key from https://makersuite.google.com/app/apikey")
    
    if api_key:
        uploaded_file = st.file_uploader("📄 Choose a Resume File", type=['pdf', 'docx'])
        
        if uploaded_file:
            if st.button("🚀 Process Resume"):
                with st.spinner("Processing your resume..."):
                    file_content = uploaded_file.read()
                    
                    if uploaded_file.type == "application/pdf":
                        resume_text = extract_text_from_pdf(file_content)
                    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        resume_text = extract_text_from_docx(file_content)
                    else:
                        st.error("Unsupported file format!")
                        resume_text = ""
                    
                    if resume_text:
                        extracted_data = extract_skills_and_projects_with_gemini(resume_text, api_key)
                        skills = extracted_data['skills']
                        projects = extracted_data['projects']
                        domains = extracted_data['domains']
                        branch = infer_branch(skills)
                        
                        # Store in session state
                        st.session_state.interview_state['skills'] = skills
                        st.session_state.interview_state['projects'] = projects
                        st.session_state.interview_state['branch'] = branch
                        st.session_state.interview_state['api_key'] = api_key
                        
                        st.subheader("📊 Extracted Information")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**🛠️ Skills ({len(skills)}):**")
                            if skills:
                                for skill in skills[:10]:
                                    st.markdown(f"• {skill}")
                                if len(skills) > 10:
                                    st.markdown(f"• ... and {len(skills)-10} more")
                            else:
                                st.markdown("No skills found")
                        
                        with col2:
                            st.markdown(f"**🎓 Inferred Branch:** {branch}")
                            st.markdown(f"**🚀 Projects ({len(projects)}):**")
                            if projects:
                                for project in projects[:5]:
                                    if isinstance(project, dict):
                                        st.markdown(f"• {project.get('title', 'Unknown')}")
                                        if project.get('technologies'):
                                            st.markdown(f"  └── Technologies: {', '.join(project['technologies'][:3])}")
                                    else:
                                        st.markdown(f"• {project}")
                            else:
                                st.markdown("No projects found")
                        
                        if domains:
                            st.markdown(f"**🎯 Domain Expertise:** {', '.join(domains)}")
                        
                        st.success("✅ Resume processed successfully!")
                        
                        # Start Interview Button with proper navigation
                        if st.button("🎤 Start Technical Interview", type="primary"):
                            st.session_state.interview_state['active'] = True
                            st.session_state.current_page = "💬 Interview"
                            st.success("🎉 Redirecting to interview...")
                            time.sleep(1)
                            st.rerun()
    else:
        st.info("Please enter your Gemini API key to process your resume.")

elif page == "💬 Interview" and st.session_state.logged_in:
    st.title("🎤 AI Technical Interview Session")
    
    # Check if interview is set up
    if not st.session_state.interview_state.get('skills') or not st.session_state.interview_state.get('api_key'):
        st.warning("⚠️ Please upload your resume first to start the interview.")
        if st.button("📄 Go to Resume Upload"):
            st.session_state.current_page = "📄 Resume Upload"
            st.rerun()
        st.stop()
    
    api_key = st.session_state.interview_state['api_key']
    interview_state = st.session_state.interview_state
    
    # Initialize questions if not already done
    if not interview_state['questions']:
        with st.spinner("🤖 Preparing personalized technical questions..."):
            technical_questions = generate_technical_questions_enhanced(
                interview_state['skills'], 
                interview_state['projects'], 
                interview_state['branch'], 
                api_key
            )
            
            project_questions = generate_project_based_questions(
                interview_state['projects'], 
                interview_state['skills'], 
                api_key
            )
            
            all_questions = technical_questions + project_questions
            interview_state['questions'] = all_questions
            
    # Progress tracking
    total_questions = min(len(interview_state['questions']) + 3, 12)
    current_progress = interview_state['current_question_index'] / total_questions
    st.progress(current_progress)
    st.caption(f"Question {interview_state['current_question_index'] + 1} of {total_questions} (max)")
    
    # Display interview info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"🎓 **Branch:** {interview_state['branch']}")
    with col2:
        st.info(f"🛠️ **Skills:** {len(interview_state['skills'])} identified")
    with col3:
        st.info(f"🚀 **Projects:** {len(interview_state['projects'])} found")
    
    # Current question display
    if interview_state['current_question_index'] < len(interview_state['questions']):
        current_question = interview_state['questions'][interview_state['current_question_index']]
        
        st.markdown("""
        <div class="interview-card">
        <h3>🤖 Interviewer Question:</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"### {current_question}")
        
        # Text-to-speech for question
        speak_question(current_question)
        
        # Response input methods
        st.markdown("### 💬 Your Response:")
        
        # Voice input section
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("🎤 Voice Input", help="Click to answer using your microphone"):
                voice_text = speech_to_text_enhanced()
                if voice_text:
                    st.session_state.voice_response = voice_text
                    st.success(f"✅ Voice captured: *{voice_text[:100]}...*")
        
        # Text input with voice response pre-filled
        voice_response = getattr(st.session_state, 'voice_response', '')
        response = st.text_area(
            "Type your answer or use voice input above:", 
            value=voice_response,
            height=150, 
            key=f"response_{interview_state['current_question_index']}",
            placeholder="Click 'Voice Input' button above to speak your answer, or type here..."
        )
        
        # Clear voice response after using it
        if voice_response and response == voice_response:
            if 'voice_response' in st.session_state:
                del st.session_state.voice_response
        
        # Action buttons
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            if st.button("📝 Submit Response", type="primary"):
                if response.strip():
                    with st.spinner("🔄 Evaluating your technical response..."):
                        evaluation = evaluate_response_enhanced(current_question, response, api_key)
                        
                        interview_state['responses'].append(response)
                        interview_state['scores'].append(evaluation['score'])
                        interview_state['feedback'].append({
                            'question': current_question,
                            'response': response,
                            'score': evaluation['score'],
                            'technical_strengths': evaluation['technical_strengths'],
                            'communication_quality': evaluation['communication_quality'],
                            'knowledge_gaps': evaluation['knowledge_gaps'],
                            'implementation_insights': evaluation['implementation_insights'],
                            'detailed_suggestions': evaluation['detailed_suggestions'],
                            'industry_relevance': evaluation['industry_relevance'],
                            'next_learning_steps': evaluation['next_learning_steps']
                        })
                        
                        interview_state['current_question_index'] += 1
                        
                        # Generate follow-up if needed
                        if (interview_state['current_question_index'] >= len(interview_state['questions']) and 
                            interview_state['current_question_index'] < 12):
                            asked_questions = [item['question'] for item in interview_state['feedback']]
                            followup = generate_dynamic_followup(
                                response, interview_state['skills'], interview_state['projects'], api_key
                            )
                            interview_state['questions'].append(followup)
                        
                        st.success("✅ Response submitted successfully!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Please provide a response before submitting!")
        
        with col2:
            if st.button("⏭️ Skip Question"):
                interview_state['current_question_index'] += 1
                st.warning("Question skipped")
                time.sleep(1)
                st.rerun()
        
        with col3:
            if st.button("🏁 End Interview"):
                if interview_state['feedback']:
                    total_score = sum(interview_state['scores'])
                    max_score = len(interview_state['scores']) * 10
                    percentage = (total_score / max_score) * 100 if max_score > 0 else 0
                    
                    feedback_data = {
                        'feedback': interview_state['feedback'],
                        'skills': interview_state['skills'],
                        'projects': interview_state['projects'],
                        'branch': interview_state['branch']
                    }
                    
                    save_feedback(st.session_state.user_email, total_score, max_score, percentage, feedback_data)
                    
                    st.session_state.interview_state = {
                        'active': False,
                        'skills': [],
                        'projects': [],
                        'branch': '',
                        'questions': [],
                        'responses': [],
                        'current_question_index': 0,
                        'feedback': [],
                        'scores': [],
                        'question_type': 'technical'
                    }
                    
                    st.success("🎉 Interview completed! Check your dashboard for detailed feedback.")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Please answer at least one question before ending!")
    
    else:
        # Interview completed
        st.subheader("🎉 Technical Interview Completed!")
        
        if interview_state['feedback']:
            total_score = sum(interview_state['scores'])
            max_score = len(interview_state['scores']) * 10
            percentage = (total_score / max_score) * 100 if max_score > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📊 Total Score", f"{total_score}/{max_score}")
            with col2:
                st.metric("📈 Percentage", f"{percentage:.1f}%")
            with col3:
                st.metric("❓ Questions Answered", len(interview_state['feedback']))
            
            feedback_data = {
                'feedback': interview_state['feedback'],
                'skills': interview_state['skills'],
                'projects': interview_state['projects'],
                'branch': interview_state['branch']
            }
            
            save_feedback(st.session_state.user_email, total_score, max_score, percentage, feedback_data)
            
            # Show detailed results with enhanced feedback headings
            st.subheader("📝 Comprehensive Interview Analysis")
            for i, item in enumerate(interview_state['feedback']):
                with st.expander(f"Question {i+1} - Score: {item['score']}/10 ⭐"):
                    st.markdown(f"**❓ Interview Question:** {item['question']}")
                    st.markdown(f"**💬 Your Response:** {item['response']}")
                    
                    # Enhanced feedback sections with new headings
                    st.markdown("---")
                    
                    st.markdown(f"""
                    <div class="feedback-section feedback-positive">
                    <h4>🎯 Technical Strengths & Accuracy</h4>
                    <p>{item['technical_strengths']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="feedback-section feedback-positive">
                    <h4>🗣️ Communication & Clarity Assessment</h4>
                    <p>{item['communication_quality']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="feedback-section feedback-improvement">
                    <h4>📚 Knowledge Gaps & Missing Elements</h4>
                    <p>{item['knowledge_gaps']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="feedback-section feedback-neutral">
                    <h4>⚙️ Implementation & Practical Insights</h4>
                    <p>{item['implementation_insights']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="feedback-section feedback-improvement">
                    <h4>💡 Detailed Improvement Recommendations</h4>
                    <p>{item['detailed_suggestions']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="feedback-section feedback-neutral">
                    <h4>🏭 Industry Standards & Relevance</h4>
                    <p>{item['industry_relevance']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="feedback-section feedback-positive">
                    <h4>📈 Next Learning Steps & Action Plan</h4>
                    <p>{item['next_learning_steps']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            if st.button("🏠 Return to Home"):
                st.session_state.interview_state = {
                    'active': False,
                    'skills': [],
                    'projects': [],
                    'branch': '',
                    'questions': [],
                    'responses': [],
                    'current_question_index': 0,
                    'feedback': [],
                    'scores': [],
                    'question_type': 'technical'
                }
                st.session_state.current_page = "🏠 Home"
                st.rerun()

elif page == "📊 Dashboard" and st.session_state.logged_in:
    st.title("📊 Your Interview Dashboard")
    
    feedback_history = get_user_feedback(st.session_state.user_email)
    
    if feedback_history:
        latest_feedback = feedback_history[0]
        avg_score = sum(f['percentage'] for f in feedback_history) / len(feedback_history)
        total_interviews = len(feedback_history)
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🎯 Latest Score", f"{latest_feedback['percentage']:.1f}%")
        with col2:
            st.metric("📈 Average Score", f"{avg_score:.1f}%")
        with col3:
            st.metric("🎤 Total Interviews", total_interviews)
        with col4:
            improvement = 0
            if len(feedback_history) > 1:
                improvement = latest_feedback['percentage'] - feedback_history[1]['percentage']
            st.metric("📊 Improvement", f"{improvement:+.1f}%", delta=improvement)
        
        # Performance chart
        st.subheader("📈 Performance Over Time")
        chart_data = []
        for i, feedback in enumerate(reversed(feedback_history)):
            chart_data.append({
                'Interview': f'Interview {i+1}',
                'Score': feedback['percentage'],
                'Date': feedback['timestamp'][:10]
            })
        
        df = pd.DataFrame(chart_data)
        fig = px.line(df, x='Interview', y='Score', 
                     title='Technical Interview Performance Trend',
                     markers=True, line_shape='spline')
        fig.update_layout(yaxis_range=[0, 100])
        fig.update_traces(line_color='#667eea', marker_color='#764ba2')
        st.plotly_chart(fig, use_container_width=True)
        
        # Skills analysis from latest interview
        if 'feedback_data' in latest_feedback and latest_feedback['feedback_data']:
            feedback_data = latest_feedback['feedback_data']
            if 'skills' in feedback_data and feedback_data['skills']:
                st.subheader("🛠️ Skills Analysis from Latest Interview")
                skills = feedback_data['skills']
                st.markdown(f"**Evaluated Skills:** {', '.join(skills[:10])}")
                if len(skills) > 10:
                    st.markdown(f"*... and {len(skills)-10} more skills*")
        
        # Interview history table
        st.subheader("📋 Interview History")
        summary_data = []
        for i, feedback in enumerate(feedback_history):
            summary_data.append({
                'Interview #': len(feedback_history) - i,
                'Score': f"{feedback['total_score']}/{feedback['max_score']}",
                'Percentage': f"{feedback['percentage']:.1f}%",
                'Questions': feedback['max_score'] // 10,
                'Date': feedback['timestamp'][:19].replace('T', ' ')
            })
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
        
        # Enhanced detailed feedback section
        if st.checkbox("📝 Show Comprehensive Feedback Analysis for Latest Interview"):
            if 'feedback_data' in latest_feedback and latest_feedback['feedback_data']:
                feedback_data = latest_feedback['feedback_data']
                feedback_items = feedback_data.get('feedback', [])
                
                if feedback_items:
                    for i, item in enumerate(feedback_items):
                        with st.expander(f"Question {i+1} Analysis - Score: {item.get('score', 'N/A')}/10 ⭐"):
                            st.markdown(f"**❓ Question:** {item.get('question', 'N/A')}")
                            st.markdown(f"**💬 Your Response:** {item.get('response', 'N/A')}")
                            
                            # Enhanced feedback display with new headings
                            st.markdown("---")
                            
                            if 'technical_strengths' in item:
                                st.markdown(f"""
                                <div class="feedback-section feedback-positive">
                                <h4>🎯 Technical Strengths & Accuracy</h4>
                                <p>{item.get('technical_strengths', 'N/A')}</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            if 'communication_quality' in item:
                                st.markdown(f"""
                                <div class="feedback-section feedback-positive">
                                <h4>🗣️ Communication & Clarity Assessment</h4>
                                <p>{item.get('communication_quality', 'N/A')}</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            if 'knowledge_gaps' in item:
                                st.markdown(f"""
                                <div class="feedback-section feedback-improvement">
                                <h4>📚 Knowledge Gaps & Missing Elements</h4>
                                <p>{item.get('knowledge_gaps', 'N/A')}</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            if 'detailed_suggestions' in item:
                                st.markdown(f"""
                                <div class="feedback-section feedback-improvement">
                                <h4>💡 Detailed Improvement Recommendations</h4>
                                <p>{item.get('detailed_suggestions', 'N/A')}</p>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            if 'next_learning_steps' in item:
                                st.markdown(f"""
                                <div class="feedback-section feedback-positive">
                                <h4>📈 Next Learning Steps & Action Plan</h4>
                                <p>{item.get('next_learning_steps', 'N/A')}</p>
                                </div>
                                """, unsafe_allow_html=True)
    else:
        st.info("No interview history found. Complete a technical interview to see your dashboard!")
        st.markdown("""
        ### 🚀 Get Started with Enhanced Technical Interviews
        1. Test your voice setup in the **🎤 Voice Test** section
        2. Upload your resume in the **📄 Resume Upload** section
        3. Complete a technical interview in the **💬 Interview** section  
        4. Return here to view your comprehensive performance analytics
        
        ### ✨ Enhanced Features
        - 🎤 **Advanced Voice Input**: Enhanced speech recognition with detailed troubleshooting
        - 🔊 **Question Audio**: Questions are read aloud for natural interview experience
        - 🧠 **Multi-Dimensional Feedback**: Comprehensive analysis across 7 different aspects
        - 🛠️ **Skills-Based Questions**: Technical questions tailored to your specific resume
        - 🚀 **Project Deep-Dive**: Questions about your actual projects and implementations
        - 📊 **Enhanced Analytics**: Detailed performance insights and improvement tracking
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6B7280; padding: 2rem;">
    <p>🤖 VIntervu - Enhanced AI Interview Bot | Built with Streamlit & Gemini AI</p>
    <p>Enhanced Features: Advanced Voice Input 🎤 | Question Audio 🔊 | Comprehensive Feedback 🧠</p>
    <p>© 2024 VIntervu. All rights reserved.</p>
</div>
""", unsafe_allow_html=True)