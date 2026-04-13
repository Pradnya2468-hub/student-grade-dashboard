import streamlit as st
import pandas as pd
import plotly.express as px
from database import Database
from datetime import datetime
import hashlib

st.set_page_config(page_title="Teacher Dashboard - Grade Analysis", layout="wide")

# Initialize database
@st.cache_resource
def init_db():
    return Database()

db = init_db()

# ------------------ Initialize session_state ------------------
if "page" not in st.session_state:
    st.session_state["page"] = "teacher_login"
if "teacher" not in st.session_state:
    st.session_state["teacher"] = None
if "selected_batch" not in st.session_state:
    st.session_state["selected_batch"] = "2024-25"
if "selected_department" not in st.session_state:
    st.session_state["selected_department"] = None
if "selected_year" not in st.session_state:
    st.session_state["selected_year"] = None
if "selected_student" not in st.session_state:
    st.session_state["selected_student"] = None

# Grade points mapping
GRADE_POINTS = {
    "O": 10,
    "A+": 9,
    "A": 8,
    "B+": 7,
    "B": 6,
    "C": 5,
    "D": 4,
    "P": 4,
    "F": 0
}

# Year mapping
YEAR_SEMESTERS = {
    "FE": [1, 2],
    "SE": [3, 4],
    "TE": [5, 6],
    "BE": [7, 8]
}

ALL_DEPARTMENTS = ["Computer Engineering", "Data Science", "IT", "AIML", "Civil", "Mechanical", "Automobile"]

def get_grade(percentage):
    if percentage >= 90:
        return "O"
    elif percentage >= 80:
        return "A+"
    elif percentage >= 70:
        return "A"
    elif percentage >= 60:
        return "B+"
    elif percentage >= 50:
        return "C"
    elif percentage >= 45:
        return "D"
    elif percentage >= 40:
        return "P"
    else:
        return "F"

def get_max_marks(row):
    subject_type = row.get("Subject Type", "")
    if subject_type == "Theory":
        paper_format = row.get("Paper Format", "")
        if paper_format == "40+60":
            return 100
        elif paper_format == "30+45":
            return 75
        else:
            return 100
    elif subject_type == "Lab":
        if row.get("Oral", 0) > 0 or row.get("Practical", 0) > 0:
            return 50
        else:
            return 25
    elif subject_type == "Additional":
        return row.get("Termwork_Max", 50)
    elif subject_type == "Always Pass":
        return 0
    return 0

def calculate_student_grades(student_gr):
    """Calculate SGPA and CGPA for a student"""
    all_marks = db.get_all_student_marks(student_gr)
    if not all_marks:
        return None
    
    all_records = []
    for sem, subjects in all_marks.items():
        if subjects:
            for subject in subjects:
                if "Grade" not in subject:
                    continue
                all_records.append(subject)
    
    if not all_records:
        return None
    
    df = pd.DataFrame(all_records)
    
    # Calculate grade points if not present
    if "Grade Point" not in df.columns:
        df["Grade Point"] = df["Grade"].map(GRADE_POINTS)
    
    # Calculate credit points - ONLY FOR PASSED SUBJECTS
    df["Credit Points"] = df.apply(
        lambda row: row["Credits"] * row["Grade Point"] if row.get("Final Result") == "Pass" else 0, 
        axis=1
    )
    
    # Semester wise data
    sem_data = []
    total_passed_credits = 0
    total_credit_points = 0
    
    semesters = sorted(df["Semester"].unique())
    
    for sem in semesters:
        sem_df = df[df["Semester"] == sem]
        passed_df = sem_df[sem_df.get("Final Result") == "Pass"]
        
        if not passed_df.empty:
            credits = passed_df["Credits"].sum()
            credit_points = passed_df["Credit Points"].sum()
            sgpa = round(credit_points / credits, 2) if credits > 0 else 0
            
            total_passed_credits += credits
            total_credit_points += credit_points
        else:
            credits = 0
            credit_points = 0
            sgpa = 0
        
        sem_data.append({
            "semester": sem,
            "credits": credits,
            "points": credit_points,
            "sgpa": sgpa,
            "total_subjects": len(sem_df),
            "passed_subjects": len(passed_df),
            "failed_subjects": len(sem_df) - len(passed_df)
        })
    
    cgpa = round(total_credit_points / total_passed_credits, 2) if total_passed_credits > 0 else 0
    
    return {
        "sem_data": sem_data,
        "total_passed_credits": total_passed_credits,
        "total_credit_points": total_credit_points,
        "cgpa": cgpa,
        "df": df
    }

def generate_batch_years():
    current_year = datetime.now().year
    batches = []
    for year in range(2004, current_year + 1):
        batch = f"{year}-{str(year+1)[-2:]}"
        batches.append(batch)
    return batches

def check_subject_exists(batch, department, semester, subject_code, subject_name):
    existing_subjects = db.get_batch_subjects(batch, department, semester)
    for subject in existing_subjects:
        if subject['subject_code'].lower() == subject_code.lower():
            return True, f"Subject with code '{subject_code}' already exists for {department}!"
        if subject['subject_name'].lower() == subject_name.lower():
            return True, f"Subject with name '{subject_name}' already exists for {department}!"
    return False, ""

def logout():
    st.session_state["page"] = "teacher_login"
    st.session_state["teacher"] = None
    st.session_state["selected_student"] = None
    st.rerun()

# Page Navigation
if st.session_state.get("page") != "teacher_login" and st.session_state.get("teacher"):
    col1, col2 = st.columns([6,1])
    with col2:
        if st.button("Logout"):
            logout()

# ------------------ TEACHER LOGIN ------------------
if st.session_state["page"] == "teacher_login":
    st.title("Teacher Grade Analysis System")
    st.subheader("Teacher Login")
    
    with st.form("teacher_login_form"):
        email = st.text_input("Enter Email Address")
        password = st.text_input("Enter Password", type="password")
        department = st.selectbox("Select Your Department", ALL_DEPARTMENTS)
        
        col1, col2 = st.columns(2)
        with col1:
            login = st.form_submit_button("Login")
        with col2:
            register = st.form_submit_button("Register")
        
        if login:
            if not email or not password:
                st.error("Please fill all fields!")
            else:
                teacher = db.verify_teacher(email, password)
                if teacher:
                    st.session_state["teacher"] = teacher
                    st.session_state["selected_department"] = teacher['department']
                    st.session_state["page"] = "teacher_dashboard"
                    st.rerun()
                else:
                    st.error("Invalid credentials!")
        
        if register:
            if not email or not password:
                st.error("Please fill all fields!")
            else:
                name = email.split('@')[0]
                teacher = db.save_teacher(name, email, password, department)
                if teacher:
                    st.success("Registration successful! Please login.")
                else:
                    st.error("Email already exists!")

# ------------------ TEACHER DASHBOARD ------------------
elif st.session_state["page"] == "teacher_dashboard":
    st.title(f"Welcome, {st.session_state['teacher']['name']}!")
    st.subheader(f"Your Department: {st.session_state['teacher']['department']}")
    st.markdown("---")
    
    # Batch Selection
    batch_years = generate_batch_years()
    if st.session_state["selected_batch"] not in batch_years:
        st.session_state["selected_batch"] = batch_years[-1]
    
    col1, col2 = st.columns(2)
    with col1:
        selected_batch = st.selectbox("Select Batch Year", batch_years, 
                                      index=batch_years.index(st.session_state["selected_batch"]))
        st.session_state["selected_batch"] = selected_batch
    
    with col2:
        selected_dept = st.selectbox("Select Department to Configure/Analyze", ALL_DEPARTMENTS,
                                    index=ALL_DEPARTMENTS.index(st.session_state['teacher']['department']))
        st.session_state["selected_department"] = selected_dept
    
    st.info(f"Working with Batch: {selected_batch} | Department: {selected_dept}")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📝 Enter Subjects & Credits**")
        if st.button("Go to Subject Configuration", use_container_width=True):
            st.session_state["page"] = "subject_config"
            st.rerun()
    with col2:
        st.markdown("**📊 Analysis & Reports**")
        if st.button("Go to Analysis", use_container_width=True):
            st.session_state["page"] = "teacher_analysis"
            st.rerun()

# ------------------ SUBJECT CONFIGURATION ------------------
elif st.session_state["page"] == "subject_config":
    st.title("Configure Subjects and Credits")
    
    batch = st.session_state.get("selected_batch", "2024-25")
    dept = st.session_state.get("selected_department", st.session_state['teacher']['department'])
    
    st.info(f"Configuring for Batch: {batch} | Department: {dept}")
    
    col1, col2 = st.columns([5,1])
    with col2:
        if st.button("← Back"):
            st.session_state["page"] = "teacher_dashboard"
            st.rerun()
    
    years = ["FE", "SE", "TE", "BE"]
    selected_year = st.radio("Select Year", years, horizontal=True)
    st.session_state["selected_year"] = selected_year
    
    semesters = YEAR_SEMESTERS[selected_year]
    st.subheader(f"{selected_year} - Semesters {semesters[0]} & {semesters[1]}")
    
    sem_tabs = st.tabs([f"Semester {semesters[0]}", f"Semester {semesters[1]}"])
    
    for idx, semester in enumerate(semesters):
        with sem_tabs[idx]:
            st.subheader(f"Semester {semester} Subjects for {dept}")
            
            existing_subjects = db.get_batch_subjects(batch, dept, semester)
            
            type_tabs = st.tabs(["Theory", "Lab", "Additional", "Always Pass (Sem 1 Only)"])
            
            with type_tabs[0]:
                st.markdown("**Add Theory Subject**")
                with st.form(f"theory_form_sem{semester}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        subject_code = st.text_input("Subject Code", key=f"theory_code_{semester}")
                        subject_name = st.text_input("Subject Name", key=f"theory_name_{semester}")
                    with col2:
                        paper_format = st.selectbox("Paper Format", 
                            ["40+60 (IA:40, ESE:60)", "30+45 (IA:30, ESE:45)", "20+20+60 (IA:20, FA:20, ESE:60)"],
                            key=f"theory_format_{semester}")
                        credits = st.number_input("Credits", min_value=0.5, max_value=5.0, value=3.0, step=0.5, key=f"theory_credits_{semester}")
                    
                    if st.form_submit_button(f"Add Theory Subject"):
                        if subject_code and subject_name:
                            exists, msg = check_subject_exists(batch, dept, semester, subject_code, subject_name)
                            if exists:
                                st.error(msg)
                            else:
                                format_code = "40+60" if "40+60" in paper_format else "30+45" if "30+45" in paper_format else "20+20+60"
                                if db.add_batch_subject(batch, dept, semester, subject_code, subject_name,
                                                       "Theory", paper_format=format_code, credits=credits):
                                    st.success(f"Added {subject_name} to {dept}")
                                    st.rerun()
                        else:
                            st.error("Please fill all fields!")
                
                theory_subjects = [s for s in existing_subjects if s['subject_type'] == "Theory"]
                if theory_subjects:
                    st.markdown(f"**Existing Theory Subjects for {dept}**")
                    for subj in theory_subjects:
                        col1, col2, col3 = st.columns([3,1,1])
                        with col1:
                            st.text(f"{subj['subject_code']} - {subj['subject_name']}")
                        with col2:
                            st.text(f"Credits: {subj['credits']}")
                        with col3:
                            if st.button(f"Delete", key=f"del_theory_{subj['subject_code']}_{semester}"):
                                db.delete_batch_subject(batch, dept, semester, subj['subject_code'])
                                st.rerun()
            
            with type_tabs[1]:
                st.markdown("**Add Lab Subject**")
                with st.form(f"lab_form_sem{semester}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        subject_code = st.text_input("Lab Subject Code", key=f"lab_code_{semester}")
                        subject_name = st.text_input("Lab Subject Name", key=f"lab_name_{semester}")
                    with col2:
                        lab_type = st.selectbox("Lab Type", 
                            ["Only Termwork", "Termwork + Oral", "C Programming"],
                            key=f"lab_type_{semester}")
                        credits = st.number_input("Credits", min_value=0.5, max_value=5.0, value=1.0, step=0.5, key=f"lab_credits_{semester}")
                    
                    if st.form_submit_button(f"Add Lab Subject"):
                        if subject_code and subject_name:
                            exists, msg = check_subject_exists(batch, dept, semester, subject_code, subject_name)
                            if exists:
                                st.error(msg)
                            else:
                                lab_code = "Only_TW" if lab_type == "Only Termwork" else "C_Prog" if lab_type == "C Programming" else "TW_OR"
                                if db.add_batch_subject(batch, dept, semester, subject_code, subject_name,
                                                       "Lab", lab_type=lab_code, credits=credits):
                                    st.success(f"Added {subject_name} to {dept}")
                                    st.rerun()
                        else:
                            st.error("Please fill all fields!")
                
                lab_subjects = [s for s in existing_subjects if s['subject_type'] == "Lab"]
                if lab_subjects:
                    st.markdown(f"**Existing Lab Subjects for {dept}**")
                    for subj in lab_subjects:
                        col1, col2, col3 = st.columns([3,1,1])
                        with col1:
                            st.text(f"{subj['subject_code']} - {subj['subject_name']}")
                        with col2:
                            st.text(f"Credits: {subj['credits']}")
                        with col3:
                            if st.button(f"Delete", key=f"del_lab_{subj['subject_code']}_{semester}"):
                                db.delete_batch_subject(batch, dept, semester, subj['subject_code'])
                                st.rerun()
            
            with type_tabs[2]:
                st.markdown("**Add Additional Subject**")
                with st.form(f"add_form_sem{semester}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        subject_code = st.text_input("Subject Code", key=f"add_code_{semester}")
                        subject_name = st.text_input("Subject Name", key=f"add_name_{semester}")
                    with col2:
                        termwork_max = st.selectbox("Max Marks", [25, 50], key=f"add_max_{semester}")
                        credits = st.number_input("Credits", min_value=0.5, max_value=5.0, value=2.0, step=0.5, key=f"add_credits_{semester}")
                    
                    if st.form_submit_button(f"Add Additional Subject"):
                        if subject_code and subject_name:
                            exists, msg = check_subject_exists(batch, dept, semester, subject_code, subject_name)
                            if exists:
                                st.error(msg)
                            else:
                                if db.add_batch_subject(batch, dept, semester, subject_code, subject_name,
                                                       "Additional", termwork_max=termwork_max, credits=credits):
                                    st.success(f"Added {subject_name} to {dept}")
                                    st.rerun()
                        else:
                            st.error("Please fill all fields!")
                
                add_subjects = [s for s in existing_subjects if s['subject_type'] == "Additional"]
                if add_subjects:
                    st.markdown(f"**Existing Additional Subjects for {dept}**")
                    for subj in add_subjects:
                        col1, col2, col3 = st.columns([3,1,1])
                        with col1:
                            st.text(f"{subj['subject_code']} - {subj['subject_name']}")
                        with col2:
                            st.text(f"Credits: {subj['credits']}")
                        with col3:
                            if st.button(f"Delete", key=f"del_add_{subj['subject_code']}_{semester}"):
                                db.delete_batch_subject(batch, dept, semester, subj['subject_code'])
                                st.rerun()
            
            with type_tabs[3]:
                if semester == 1:
                    st.markdown("**Add Always Pass Subject**")
                    st.caption("Students get O grade (10 grade points)")
                    
                    with st.form(f"always_pass_form_sem{semester}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            subject_code = st.text_input("Subject Code", key=f"always_code_{semester}")
                            subject_name = st.text_input("Subject Name", key=f"always_name_{semester}")
                        with col2:
                            credits = st.number_input("Credits", min_value=0.5, max_value=5.0, value=2.0, step=0.5, key=f"always_credits_{semester}")
                            st.info(f"O grade (10 points) × {credits} credits = {credits*10} credit points")
                        
                        if st.form_submit_button(f"Add Always Pass Subject"):
                            if subject_code and subject_name:
                                exists, msg = check_subject_exists(batch, dept, semester, subject_code, subject_name)
                                if exists:
                                    st.error(msg)
                                else:
                                    if db.add_batch_subject(batch, dept, semester, subject_code, subject_name,
                                                           "Always Pass", credits=credits):
                                        st.success(f"Added Always Pass subject to {dept}")
                                        st.rerun()
                            else:
                                st.error("Please fill all fields!")
                    
                    always_subjects = [s for s in existing_subjects if s['subject_type'] == "Always Pass"]
                    if always_subjects:
                        st.markdown(f"**Existing Always Pass Subjects for {dept}**")
                        for subj in always_subjects:
                            col1, col2, col3 = st.columns([3,1,1])
                            with col1:
                                st.text(f"{subj['subject_code']} - {subj['subject_name']}")
                            with col2:
                                st.text(f"Credits: {subj['credits']}")
                            with col3:
                                if st.button(f"Delete", key=f"del_always_{subj['subject_code']}_{semester}"):
                                    db.delete_batch_subject(batch, dept, semester, subj['subject_code'])
                                    st.rerun()

# ------------------ TEACHER ANALYSIS ------------------
elif st.session_state["page"] == "teacher_analysis":
    st.title("Student Performance Analysis")
    
    batch = st.session_state.get("selected_batch", "2024-25")
    analysis_dept = st.session_state.get("selected_department", st.session_state['teacher']['department'])
    
    st.info(f"Analyzing Batch: {batch} | Department: {analysis_dept}")
    
    col1, col2 = st.columns([5,1])
    with col2:
        if st.button("← Back"):
            st.session_state["page"] = "teacher_dashboard"
            st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        view_dept = st.selectbox("Select Department to View", ALL_DEPARTMENTS,
                                index=ALL_DEPARTMENTS.index(analysis_dept),
                                key="view_dept")
    with col2:
        st.write("")
    
    if view_dept != analysis_dept:
        analysis_dept = view_dept
        st.session_state["selected_department"] = view_dept
    
    students = db.get_students_by_batch_and_dept(batch, analysis_dept)
    
    if not students:
        st.warning(f"No students found in {analysis_dept} for batch {batch}")
    else:
        student_performance = []
        students_with_data_count = 0
        total_subjects_dept = 0
        
        for student in students:
            grades = calculate_student_grades(student['gr_number'])
            if grades and grades['total_passed_credits'] > 0:
                students_with_data_count += 1
                # Calculate total subjects for this student
                student_total_subjects = 0
                if grades['sem_data']:
                    for sem in grades['sem_data']:
                        student_total_subjects += sem['total_subjects']
                total_subjects_dept += student_total_subjects
                
                student_performance.append({
                    "name": student['name'],
                    "gr": student['gr_number'],
                    "department": student['department'],
                    "batch": student['batch'],
                    "cgpa": grades['cgpa'],
                    "total_passed_credits": grades['total_passed_credits'],
                    "total_credit_points": grades['total_credit_points'],
                    "total_subjects": student_total_subjects,
                    "has_data": True,
                    "sem_data": grades['sem_data']
                })
            else:
                student_performance.append({
                    "name": student['name'],
                    "gr": student['gr_number'],
                    "department": student['department'],
                    "batch": student['batch'],
                    "cgpa": 0,
                    "total_passed_credits": 0,
                    "total_credit_points": 0,
                    "total_subjects": 0,
                    "has_data": False,
                    "sem_data": []
                })
        
        students_with_data = [s for s in student_performance if s['has_data']]
        students_with_data.sort(key=lambda x: x['cgpa'], reverse=True)
        
        st.subheader("🏆 Top 3 Students")
        if students_with_data:
            top_cols = st.columns(3)
            for i in range(min(3, len(students_with_data))):
                with top_cols[i]:
                    st.metric(
                        f"{i+1}. {students_with_data[i]['name']}",
                        f"CGPA: {students_with_data[i]['cgpa']:.2f}",
                        f"GR: {students_with_data[i]['gr']}"
                    )
        else:
            st.info("No students with grade data found")
        
        st.markdown("---")
        
        # Statistics with Total Subjects
        st.subheader(f"📊 {analysis_dept} Department Statistics")
        
        total_students = len(student_performance)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Students", total_students)
        with col2:
            st.metric("Students with Data", students_with_data_count)
        with col3:
            st.metric("Total Subjects", total_subjects_dept)
        
        if students_with_data:
            pass_students = [s for s in students_with_data if s['cgpa'] >= 4.0]
            fail_students = [s for s in students_with_data if s['cgpa'] < 4.0]
            
            pass_rate = (len(pass_students)/len(students_with_data))*100 if students_with_data else 0
            avg_cgpa = sum(s['cgpa'] for s in students_with_data)/len(students_with_data)
            
            with col4:
                st.metric("Pass Rate", f"{pass_rate:.1f}%")
            with col5:
                st.metric("Dept Avg CGPA", f"{avg_cgpa:.2f}")
            
            st.subheader("📈 Pass vs Fail Distribution")
            pass_fail_df = pd.DataFrame({
                "Status": ["Pass", "Fail"],
                "Count": [len(pass_students), len(fail_students)]
            })
            fig_pie = px.pie(pass_fail_df, values='Count', names='Status',
                            color='Status', color_discrete_map={'Pass': '#2ecc71', 'Fail': '#e74c3c'})
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.subheader("📊 CGPA Distribution")
            cgpa_values = [s['cgpa'] for s in students_with_data]
            fig_hist = px.histogram(cgpa_values, nbins=20, 
                                   title=f"CGPA Distribution - {analysis_dept}",
                                   labels={'value': 'CGPA', 'count': 'Number of Students'})
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            with col4:
                st.metric("Pass Rate", "0%")
            with col5:
                st.metric("Dept Avg CGPA", "0.00")
            st.info("No grade data available for statistics")
        
        st.markdown("---")
        
        # Student List
        st.subheader("📋 Student List")
        
        filter_option = st.radio("Filter Students", ["All", "Pass", "Fail", "No Data"], horizontal=True)
        
        if filter_option == "Pass":
            filtered = [s for s in student_performance if s['has_data'] and s['cgpa'] >= 4.0]
        elif filter_option == "Fail":
            filtered = [s for s in student_performance if s['has_data'] and s['cgpa'] < 4.0]
        elif filter_option == "No Data":
            filtered = [s for s in student_performance if not s['has_data']]
        else:
            filtered = student_performance
        
        search = st.text_input("🔍 Search by name or GR number")
        if search:
            filtered = [s for s in filtered if search.lower() in s['name'].lower() or search in s['gr']]
        
        if filtered:
            for student in filtered:
                with st.expander(f"{student['name']} ({student['gr']}) - CGPA: {student['cgpa']:.2f}"):
                    if student['has_data']:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Department:** {student['department']}")
                            st.write(f"**Batch:** {student['batch']}")
                        with col2:
                            st.write(f"**Passed Credits:** {student['total_passed_credits']:.2f}")
                            st.write(f"**Total Subjects:** {student['total_subjects']}")
                        with col3:
                            st.write(f"**Credit Points:** {student['total_credit_points']:.2f}")
                        
                        col1, col2 = st.columns([3,1])
                        with col2:
                            if st.button("📊 View Full Analysis", key=f"view_{student['gr']}"):
                                student_details = db.get_student_details(student['gr'])
                                st.session_state["selected_student"] = student_details
                                st.session_state["page"] = "student_detail_view"
                                st.rerun()
                        
                        if student['sem_data']:
                            sem_df = pd.DataFrame(student['sem_data'])
                            st.dataframe(sem_df[['semester', 'total_subjects', 'passed_subjects', 'failed_subjects', 'credits', 'sgpa']],
                                       use_container_width=True, hide_index=True)
                    else:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Department:** {student['department']}")
                            st.write(f"**Batch:** {student['batch']}")
                        with col2:
                            st.warning("⚠️ No marks data available for this student")
        else:
            st.info("No students match the filter")

# ------------------ STUDENT DETAIL VIEW ------------------
elif st.session_state["page"] == "student_detail_view":
    student = st.session_state.get("selected_student", {})
    
    if not student:
        st.error("No student selected")
        if st.button("← Back to Analysis"):
            st.session_state["page"] = "teacher_analysis"
            st.rerun()
    else:
        st.title(f"📊 Student Analysis: {student['name']}")
        st.subheader(f"GR: {student['gr_number']} | Batch: {student['batch']} | Dept: {student['department']}")
        
        col1, col2 = st.columns([5,1])
        with col2:
            if st.button("← Back"):
                st.session_state["page"] = "teacher_analysis"
                st.rerun()
        
        grades = calculate_student_grades(student['gr_number'])
        
        if not grades or grades['df'].empty:
            st.warning("No marks data available for this student")
        else:
            df = grades['df']
            
            st.subheader("📝 Subject-wise Detailed Report")
            display_cols = ["Semester", "Subject", "Total", "Percentage", "Grade", "Credits", "Grade Point", "Credit Points", "Final Result"]
            available = [col for col in display_cols if col in df.columns]
            st.dataframe(df[available], use_container_width=True)
            
            st.subheader("📈 Semester-wise Performance")
            if grades['sem_data']:
                sem_data = []
                for sem in grades['sem_data']:
                    sem_data.append({
                        "Semester": sem['semester'],
                        "Total Subjects": sem['total_subjects'],
                        "Passed": sem['passed_subjects'],
                        "Failed": sem['failed_subjects'],
                        "Passed Credits": round(sem['credits'], 2),
                        "Credit Points": round(sem['points'], 2),
                        "SGPA": sem['sgpa']
                    })
                
                sem_df = pd.DataFrame(sem_data)
                st.dataframe(sem_df, use_container_width=True)
            
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Overall CGPA", f"{grades['cgpa']:.2f}")
            with col2:
                st.metric("Total Passed Credits", f"{grades['total_passed_credits']:.2f}")
            with col3:
                st.metric("Total Credit Points", f"{grades['total_credit_points']:.2f}")