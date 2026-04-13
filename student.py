import streamlit as st
import pandas as pd
import plotly.express as px
from database import Database
import re

st.set_page_config(page_title="Student Performance Analysis", layout="wide")

# Initialize database
@st.cache_resource
def init_db():
    return Database()

db = init_db()

# ------------------ Initialize session_state ------------------
if "page" not in st.session_state:
    st.session_state["page"] = "login"
if "student_submissions" not in st.session_state:
    st.session_state["student_submissions"] = {}
if "student_details" not in st.session_state:
    st.session_state["student_details"] = {}
if "logged_in_gr" not in st.session_state:
    st.session_state["logged_in_gr"] = None
if "kt_subjects" not in st.session_state:
    st.session_state["kt_subjects"] = []

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

def extract_batch_from_email(email):
    match = re.search(r'(\d{2})@', email)
    if match:
        year_suffix = match.group(1)
        start_year = 2000 + int(year_suffix) - 1
        end_year = start_year + 1
        return f"{start_year}-{str(end_year)[-2:]}"
    return None

def load_student_data(gr_number):
    student_details = db.get_student_details(gr_number)
    if student_details:
        st.session_state["student_details"] = {
            "name": student_details["name"],
            "gr": student_details["gr_number"],
            "email": student_details["email"],
            "department": student_details["department"],
            "current_sem": student_details["current_semester"],
            "batch": student_details["batch"]
        }
        
        all_marks = db.get_all_student_marks(gr_number)
        st.session_state["student_submissions"] = all_marks
        
        # Load KT subjects
        kt_data = db.get_kt_subjects(gr_number)
        st.session_state["kt_subjects"] = kt_data
        return True
    return False

def logout():
    for key in list(st.session_state.keys()):
        if key != "db":
            del st.session_state[key]
    st.session_state["page"] = "login"
    st.rerun()

# Page Navigation
if st.session_state.get("page") != "login" and st.session_state.get("page") is not None:
    col1, col2 = st.columns([6,1])
    with col2:
        if st.button("Logout"):
            logout()

# ------------------ PAGE 1: LOGIN ------------------
if st.session_state["page"] == "login":
    st.title("Student Grade Analysis System")
    st.subheader("Student Login")
    
    with st.form("login_form"):
        email = st.text_input("Enter College Email")
        password = st.text_input("Enter Password", type="password")
        department = st.selectbox("Select Department", ["Computer Engineering", "Data Science", "IT", "AIML", "Civil", "Mechanical", "Automobile"])
        
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if not email.endswith(".sce.edu.in"):
                st.error("Email must end with .sce.edu.in")
            elif password != "SCOE":
                st.error("Incorrect password")
            else:
                st.session_state["student_details"]["email"] = email
                st.session_state["student_details"]["department"] = department
                st.session_state["page"] = "student_details"
                st.success(f"Login successful!")
                st.rerun()

# ------------------ PAGE 2: STUDENT DETAILS ------------------
elif st.session_state["page"] == "student_details":
    st.title("Student Details")
    
    department = st.session_state["student_details"].get("department", "")
    email = st.session_state["student_details"]["email"]
    
    with st.form("student_details_form"):
        name = st.text_input("Student Name", value=st.session_state["student_details"].get("name", ""))
        gr = st.text_input("GR Number", value=st.session_state["student_details"].get("gr", ""))
        
        default_sem = st.session_state["student_details"].get("current_sem", 1)
        current_sem = st.selectbox("Current Semester", [1,2,3,4,5,6,7,8], index=default_sem-1)
        
        batch = extract_batch_from_email(email)
        if batch:
            st.info(f"Detected Batch: {batch}")
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Submit")
        with col2:
            back = st.form_submit_button("Back to Login")
        
        if submitted:
            if not name or not gr:
                st.warning("Please fill all student details!")
            else:
                db.save_student_details(gr, name, email, department, current_sem, batch)
                
                st.session_state["student_details"]["name"] = name
                st.session_state["student_details"]["gr"] = gr
                st.session_state["student_details"]["current_sem"] = current_sem
                st.session_state["student_details"]["batch"] = batch
                st.session_state["logged_in_gr"] = gr
                
                load_student_data(gr)
                st.session_state["page"] = "semester_entry"
                st.success("Student details saved!")
                st.rerun()
        
        if back:
            st.session_state["page"] = "login"
            st.rerun()

# ------------------ PAGE 3: SEMESTER MARKS ENTRY (CLEAN VERSION - NO EMOJIS, NO GRADE PREVIEW) ------------------
elif st.session_state["page"] == "semester_entry":
    name = st.session_state["student_details"]["name"]
    gr = st.session_state["student_details"]["gr"]
    current_sem = st.session_state["student_details"]["current_sem"]
    batch = st.session_state["student_details"].get("batch")
    department = st.session_state["student_details"].get("department")
    
    st.title(f"Enter Marks for {name}")
    st.caption(f"GR: {gr} | Batch: {batch} | Department: {department} | Current Semester: {current_sem}")
    
    with st.expander("Grade Structure Reference"):
        grade_data = {
            "Percentage": ["90% and above", "80% - 89.99%", "70% - 79.99%", "60% - 69.99%", 
                          "50% - 59.99%", "45% - 49.99%", "40% - 44.99%", "Less than 40%"],
            "Grade": ["O", "A+", "A", "B+", "C", "D", "P", "F"],
            "Grade Points": [10, 9, 8, 7, 5, 4, 4, 0]
        }
        grade_df = pd.DataFrame(grade_data)
        st.dataframe(grade_df, use_container_width=True, hide_index=True)
    
    # Show saved and pending semesters
    saved_sems = []
    pending_sems = []
    
    for sem in range(1, current_sem + 1):
        if sem in st.session_state["student_submissions"] and st.session_state["student_submissions"][sem]:
            saved_sems.append(sem)
        else:
            pending_sems.append(sem)
    
    st.subheader("Semester Progress")
    col1, col2 = st.columns(2)
    with col1:
        if saved_sems:
            st.success(f"Completed Semesters: {', '.join(map(str, saved_sems))}")
        else:
            st.info("No semesters completed yet")
    with col2:
        if pending_sems:
            st.warning(f"Pending Semesters: {', '.join(map(str, pending_sems))}")
        else:
            st.success("All semesters completed")
    
    st.markdown("---")
    
    # Select semester to enter/edit
    all_sems = list(range(1, current_sem + 1))
    
    # Default to first pending semester if any, otherwise show latest saved
    default_sem = pending_sems[0] if pending_sems else (saved_sems[-1] if saved_sems else 1)
    sem = st.selectbox("Select Semester to Enter/Edit Marks", all_sems, 
                       index=all_sems.index(default_sem))
    
    # Get existing data for this semester
    existing_data = st.session_state["student_submissions"].get(sem, [])
    
    # Get subjects configured by teacher for this batch and semester
    if batch and department:
        batch_subjects = db.get_batch_subjects(batch, department, sem)
        if not batch_subjects:
            st.warning(f"No subjects configured for Semester {sem}. Please contact your teacher.")
            batch_subjects = []
        else:
            st.success(f"Found {len(batch_subjects)} subjects for Semester {sem}")
    else:
        st.error("Batch or Department not detected. Please go back and update student details.")
        batch_subjects = []
    
    with st.form(f"sem_{sem}_marks_form"):
        subjects_data = []
        kt_updates = []
        
        if batch_subjects:
            st.subheader(f"Enter Marks for Semester {sem} Subjects")
            
            for idx, subject in enumerate(batch_subjects):
                with st.container():
                    st.markdown(f"**{idx+1}. {subject['subject_name']}**")
                    st.caption(f"Code: {subject['subject_code']} | Credits: {subject['credits']} | Type: {subject['subject_type']}")
                    
                    # Find existing marks for this subject
                    prev_marks = {}
                    if existing_data:
                        for s in existing_data:
                            if s.get("Subject Code") == subject['subject_code']:
                                prev_marks = s
                                break
                    
                    # ALWAYS PASS SUBJECT
                    if subject['subject_type'] == "Always Pass":
                        st.success("Always Pass Subject - Automatically gets O grade")
                        
                        subjects_data.append({
                            "Semester": sem,
                            "Subject": subject['subject_name'],
                            "Subject Code": subject['subject_code'],
                            "Subject Type": "Always Pass",
                            "Credits": subject['credits'],
                            "IA": 0,
                            "FA": 0,
                            "ESE": 0,
                            "Oral": 0,
                            "Practical": 0,
                            "Termwork": 0,
                            "Total": 0,
                            "Max_Marks": 0,
                            "Percentage": 100,
                            "Grade": "O",
                            "Grade Point": 10,
                            "Final Result": "Pass"
                        })
                    
                    # THEORY SUBJECT
                    elif subject['subject_type'] == "Theory":
                        if subject['paper_format'] == "40+60":
                            col1, col2 = st.columns(2)
                            with col1:
                                ia = st.number_input(
                                    f"IA Marks (0-40)", 
                                    min_value=0, 
                                    max_value=40, 
                                    value=prev_marks.get("IA", 0) if prev_marks else 0,
                                    step=1,
                                    key=f"theory_ia_{sem}_{idx}"
                                )
                            with col2:
                                ese = st.number_input(
                                    f"ESE Marks (0-60)", 
                                    min_value=0, 
                                    max_value=60, 
                                    value=prev_marks.get("ESE", 0) if prev_marks else 0,
                                    step=1,
                                    key=f"theory_ese_{sem}_{idx}"
                                )
                            
                            internal_result = "Pass" if ia >= 16 else "Fail"
                            external_result = "Pass" if ese >= 24 else "Fail"
                            subject_total = ia + ese
                            max_marks = 100
                            fa = 0
                            
                        elif subject['paper_format'] == "30+45":
                            col1, col2 = st.columns(2)
                            with col1:
                                ia = st.number_input(
                                    f"IA Marks (0-30)", 
                                    min_value=0, 
                                    max_value=30, 
                                    value=prev_marks.get("IA", 0) if prev_marks else 0,
                                    step=1,
                                    key=f"theory_ia_{sem}_{idx}"
                                )
                            with col2:
                                ese = st.number_input(
                                    f"ESE Marks (0-45)", 
                                    min_value=0, 
                                    max_value=45, 
                                    value=prev_marks.get("ESE", 0) if prev_marks else 0,
                                    step=1,
                                    key=f"theory_ese_{sem}_{idx}"
                                )
                            
                            internal_result = "Pass" if ia >= 12 else "Fail"
                            external_result = "Pass" if ese >= 18 else "Fail"
                            subject_total = ia + ese
                            max_marks = 75
                            fa = 0
                        
                        else:  # 20+20+60 format
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                ia = st.number_input(
                                    f"IA Marks (0-20)", 
                                    min_value=0, 
                                    max_value=20, 
                                    value=prev_marks.get("IA", 0) if prev_marks else 0,
                                    step=1,
                                    key=f"theory_ia_{sem}_{idx}"
                                )
                            with col2:
                                fa = st.number_input(
                                    f"FA Marks (0-20)", 
                                    min_value=0, 
                                    max_value=20, 
                                    value=prev_marks.get("FA", 0) if prev_marks else 0,
                                    step=1,
                                    key=f"theory_fa_{sem}_{idx}"
                                )
                            with col3:
                                ese = st.number_input(
                                    f"ESE Marks (0-60)", 
                                    min_value=0, 
                                    max_value=60, 
                                    value=prev_marks.get("ESE", 0) if prev_marks else 0,
                                    step=1,
                                    key=f"theory_ese_{sem}_{idx}"
                                )
                            
                            internal_total = ia + fa
                            internal_result = "Pass" if internal_total >= 8 else "Fail"
                            external_result = "Pass" if ese >= 24 else "Fail"
                            subject_total = ia + fa + ese
                            max_marks = 100
                        
                        final_result = "Pass" if internal_result == "Pass" and external_result == "Pass" else "Fail"
                        
                        if final_result == "Pass":
                            percentage = (subject_total / max_marks) * 100
                            grade = get_grade(percentage)
                            grade_point = GRADE_POINTS[grade]
                        else:
                            percentage = 0
                            grade = "F"
                            grade_point = 0
                        
                        subjects_data.append({
                            "Semester": sem,
                            "Subject": subject['subject_name'],
                            "Subject Code": subject['subject_code'],
                            "Subject Type": "Theory",
                            "Paper Format": subject['paper_format'],
                            "Credits": subject['credits'],
                            "IA": ia,
                            "FA": fa,
                            "ESE": ese,
                            "Oral": 0,
                            "Practical": 0,
                            "Termwork": 0,
                            "Total": subject_total,
                            "Max_Marks": max_marks,
                            "Percentage": round(percentage, 2),
                            "Grade": grade,
                            "Grade Point": grade_point,
                            "Final Result": final_result
                        })
                        
                        if final_result == "Fail":
                            kt_updates.append({
                                "subject_code": subject['subject_code'],
                                "subject_name": subject['subject_name'],
                                "original_semester": sem,
                                "credits": subject['credits'],
                                "attempts": 1,
                                "cleared": False,
                                "status": "Pending"
                            })
                    
                    # LAB SUBJECT
                    elif subject['subject_type'] == "Lab":
                        if subject['lab_type'] == "Only_TW":
                            termwork = st.number_input(
                                f"Termwork Marks (0-25)", 
                                min_value=0, 
                                max_value=25, 
                                value=prev_marks.get("Termwork", 0) if prev_marks else 0,
                                step=1,
                                key=f"lab_tw_{sem}_{idx}"
                            )
                            teamwork_result = "Pass" if termwork >= 10 else "Fail"
                            subject_total = termwork
                            max_marks = 25
                            oral = 0
                            practical = 0
                            
                        elif subject['lab_type'] == "C_Prog":
                            col1, col2 = st.columns(2)
                            with col1:
                                termwork = st.number_input(
                                    f"Termwork Marks (0-25)", 
                                    min_value=0, 
                                    max_value=25, 
                                    value=prev_marks.get("Termwork", 0) if prev_marks else 0,
                                    step=1,
                                    key=f"lab_tw_{sem}_{idx}"
                                )
                            with col2:
                                practical = st.number_input(
                                    f"Practical Marks (0-25)", 
                                    min_value=0, 
                                    max_value=25, 
                                    value=prev_marks.get("Practical", 0) if prev_marks else 0,
                                    step=1,
                                    key=f"lab_prac_{sem}_{idx}"
                                )
                            
                            teamwork_total = termwork + practical
                            teamwork_result = "Pass" if teamwork_total >= 20 else "Fail"
                            subject_total = teamwork_total
                            max_marks = 50
                            oral = 0
                            
                        else:  # TW_OR
                            col1, col2 = st.columns(2)
                            with col1:
                                termwork = st.number_input(
                                    f"Termwork Marks (0-25)", 
                                    min_value=0, 
                                    max_value=25, 
                                    value=prev_marks.get("Termwork", 0) if prev_marks else 0,
                                    step=1,
                                    key=f"lab_tw_{sem}_{idx}"
                                )
                            with col2:
                                oral = st.number_input(
                                    f"Oral Marks (0-25)", 
                                    min_value=0, 
                                    max_value=25, 
                                    value=prev_marks.get("Oral", 0) if prev_marks else 0,
                                    step=1,
                                    key=f"lab_oral_{sem}_{idx}"
                                )
                            
                            teamwork_total = termwork + oral
                            teamwork_result = "Pass" if teamwork_total >= 20 else "Fail"
                            subject_total = teamwork_total
                            max_marks = 50
                            practical = 0
                        
                        final_result = teamwork_result
                        
                        if final_result == "Pass":
                            percentage = (subject_total / max_marks) * 100
                            grade = get_grade(percentage)
                            grade_point = GRADE_POINTS[grade]
                        else:
                            percentage = 0
                            grade = "F"
                            grade_point = 0
                        
                        subjects_data.append({
                            "Semester": sem,
                            "Subject": subject['subject_name'],
                            "Subject Code": subject['subject_code'],
                            "Subject Type": "Lab",
                            "Lab Type": subject['lab_type'],
                            "Credits": subject['credits'],
                            "IA": 0,
                            "FA": 0,
                            "ESE": 0,
                            "Oral": oral,
                            "Practical": practical,
                            "Termwork": termwork,
                            "Total": subject_total,
                            "Max_Marks": max_marks,
                            "Percentage": round(percentage, 2),
                            "Grade": grade,
                            "Grade Point": grade_point,
                            "Final Result": final_result
                        })
                        
                        if final_result == "Fail":
                            kt_updates.append({
                                "subject_code": subject['subject_code'],
                                "subject_name": subject['subject_name'],
                                "original_semester": sem,
                                "credits": subject['credits'],
                                "attempts": 1,
                                "cleared": False,
                                "status": "Pending"
                            })
                    
                    # ADDITIONAL SUBJECT
                    elif subject['subject_type'] == "Additional":
                        termwork_max = subject.get('termwork_max', 50)
                        pass_marks = int(termwork_max * 0.4)
                        
                        termwork = st.number_input(
                            f"Termwork Marks (0-{termwork_max})", 
                            min_value=0, 
                            max_value=termwork_max, 
                            value=prev_marks.get("Termwork", 0) if prev_marks else 0,
                            step=1,
                            key=f"add_tw_{sem}_{idx}"
                        )
                        
                        final_result = "Pass" if termwork >= pass_marks else "Fail"
                        
                        if final_result == "Pass":
                            percentage = (termwork / termwork_max) * 100
                            grade = get_grade(percentage)
                            grade_point = GRADE_POINTS[grade]
                        else:
                            percentage = 0
                            grade = "F"
                            grade_point = 0
                        
                        subjects_data.append({
                            "Semester": sem,
                            "Subject": subject['subject_name'],
                            "Subject Code": subject['subject_code'],
                            "Subject Type": "Additional",
                            "Credits": subject['credits'],
                            "IA": 0,
                            "FA": 0,
                            "ESE": 0,
                            "Oral": 0,
                            "Practical": 0,
                            "Termwork": termwork,
                            "Termwork_Max": termwork_max,
                            "Total": termwork,
                            "Max_Marks": termwork_max,
                            "Percentage": round(percentage, 2),
                            "Grade": grade,
                            "Grade Point": grade_point,
                            "Final Result": final_result
                        })
                        
                        if final_result == "Fail":
                            kt_updates.append({
                                "subject_code": subject['subject_code'],
                                "subject_name": subject['subject_name'],
                                "original_semester": sem,
                                "credits": subject['credits'],
                                "attempts": 1,
                                "cleared": False,
                                "status": "Pending"
                            })
                    
                    st.markdown("---")
        
        else:
            st.error("No subjects configured for this semester. Please contact your teacher to configure subjects first.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            save_button = st.form_submit_button(f"Save Semester {sem} Marks", type="primary", use_container_width=True)
        with col2:
            back_button = st.form_submit_button("Back to Details", use_container_width=True)
        with col3:
            view_analysis = st.form_submit_button("View Analysis", use_container_width=True)
        
        if save_button:
            if not subjects_data:
                st.error("No subjects data to save!")
            else:
                # Save marks to database
                db.save_semester_marks(gr, sem, subjects_data)
                st.session_state["student_submissions"][sem] = subjects_data
                
                # Update KT subjects
                if kt_updates:
                    existing_kt = st.session_state.get("kt_subjects", [])
                    for kt in kt_updates:
                        found = False
                        for e in existing_kt:
                            if e["subject_code"] == kt["subject_code"] and not e.get("cleared", False):
                                e["attempts"] += 1
                                found = True
                                break
                        if not found:
                            existing_kt.append(kt)
                    st.session_state["kt_subjects"] = existing_kt
                    db.save_all_kt_subjects(gr, existing_kt)
                
                st.success(f"Semester {sem} marks saved successfully!")
                st.balloons()
                st.rerun()
        
        if back_button:
            st.session_state["page"] = "student_details"
            st.rerun()
        
        if view_analysis:
            has_data = any(st.session_state["student_submissions"].get(s, []) for s in range(1, current_sem + 1))
            if has_data:
                st.session_state["page"] = "analysis"
                st.rerun()
            else:
                st.error("Please save at least one semester's marks before viewing analysis!")
    
    # Navigation buttons at bottom
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col2:
        if st.button("View Complete Analysis", use_container_width=True):
            has_data = any(st.session_state["student_submissions"].get(s, []) for s in range(1, current_sem + 1))
            if has_data:
                st.session_state["page"] = "analysis"
                st.rerun()
            else:
                st.error("Please save at least one semester's marks first!")

# ------------------ PAGE 4: ANALYSIS (FIXED - KT PENDING SGPA=0, KT CLEARED INCLUDED IN SGPA) ------------------
elif st.session_state["page"] == "analysis":
    st.title("Student Performance Analysis")
    
    # Force refresh data from database to get latest marks
    gr = st.session_state["logged_in_gr"]
    
    # Refresh student submissions from database
    all_marks = db.get_all_student_marks(gr)
    st.session_state["student_submissions"] = all_marks
    
    # Refresh KT subjects from database
    kt_data = db.get_kt_subjects(gr)
    st.session_state["kt_subjects"] = kt_data
    
    # Now collect all records from updated session_state
    all_records = []
    for sem, subjects in st.session_state["student_submissions"].items():
        if subjects:
            all_records.extend(subjects)
    
    if not all_records:
        st.warning("No data available.")
        if st.button("Go to Semester Entry"):
            st.session_state["page"] = "semester_entry"
            st.rerun()
    else:
        df = pd.DataFrame(all_records)
        
        # Add Max_Marks if not present
        if "Max_Marks" not in df.columns:
            df["Max_Marks"] = df.apply(lambda row: get_max_marks(row), axis=1)
        
        st.subheader(f"Student: {st.session_state['student_details']['name']} (GR: {st.session_state['student_details']['gr']})")
        st.subheader(f"Department: {st.session_state['student_details']['department']}")
        st.subheader(f"Batch: {st.session_state['student_details'].get('batch', 'N/A')}")
        
        # Grade point mapping
        df["Grade Point"] = df["Grade"].map(GRADE_POINTS)
        
        # Credit points calculation - only for passed subjects
        df["Credit Points"] = df.apply(
            lambda row: row["Credits"] * row["Grade Point"] if row["Final Result"] == "Pass" else 0, 
            axis=1
        )
        
        # Get KT subjects from session_state
        all_kt_subjects = st.session_state.get("kt_subjects", [])
        
        # Separate active KT (not cleared) and cleared KT
        active_kt_subjects = [kt for kt in all_kt_subjects if not kt.get("cleared", False)]
        cleared_kt_subjects = [kt for kt in all_kt_subjects if kt.get("cleared", False)]
        
        # Identify semesters with active KT (not cleared)
        semesters_with_active_kt = set()
        for kt in active_kt_subjects:
            semesters_with_active_kt.add(kt["original_semester"])
        
        # Create formatted Total column
        df["Marks"] = df.apply(
            lambda row: f"{row['Total']}/{row['Max_Marks']}" if row['Max_Marks'] > 0 else "Always Pass",
            axis=1
        )
        
        # Subject-wise report
        st.subheader("Subject-wise Detailed Report")
        display_cols = ["Semester", "Subject Type", "Subject", "Marks", "Percentage", "Grade", "Credits", "Grade Point", "Credit Points", "Final Result"]
        available_display_cols = [col for col in display_cols if col in df.columns]
        st.dataframe(df[available_display_cols], use_container_width=True)

              # Semester-wise summary
        st.subheader("Semester-wise Summary")
        sem_summary = []
        
        # Track totals for CGPA (include ONLY semesters with NO failed subjects)
        total_cgpa_credits = 0
        total_cgpa_credit_points = 0
        
        for sem in range(1, st.session_state["student_details"]["current_sem"]+1):
            sem_df = df[df["Semester"] == sem]
            if sem_df.empty:
                continue
            
            # Check if this semester has any failed subject
            failed_subjects_count = len(sem_df[sem_df["Final Result"] == "Fail"])
            has_failed = failed_subjects_count > 0
            
            # Calculate marks (excluding Always Pass)
            sem_df_no_always = sem_df[sem_df["Subject Type"] != "Always Pass"]
            sem_max = sem_df_no_always["Max_Marks"].sum() if not sem_df_no_always.empty else 0
            sem_total = sem_df_no_always["Total"].sum() if not sem_df_no_always.empty else 0
            sem_percent = (sem_total / sem_max) * 100 if sem_max > 0 else 0
            
            # Subject counts
            total_subjects = len(sem_df)
            passed_subjects = len(sem_df[sem_df["Final Result"] == "Pass"])
            failed_subjects = failed_subjects_count
            
            # Calculate total credits and credit points for this semester
            total_credits = sem_df["Credits"].sum()
            total_credit_points = sem_df["Credit Points"].sum()
            
            # SGPA calculation based on whether there's any failed subject
            if has_failed:
                # Semester with any failed subject = SGPA = 0, NOT included in CGPA
                sgpa = 0.00
                sgpa_display = "0.00"
                status_msg = "Not Cleared"
                passed_credits = sem_df[sem_df["Final Result"] == "Pass"]["Credits"].sum()
                credit_points = 0
                # DO NOT add to CGPA
            else:
                # Semester with no failed subjects = normal SGPA calculation
                if total_credits > 0:
                    sgpa = round(total_credit_points / total_credits, 2)
                else:
                    sgpa = 0.00
                sgpa_display = f"{sgpa:.2f}"
                passed_credits = sem_df["Credits"].sum()
                credit_points = total_credit_points
                status_msg = "Cleared"
                
                # Add to CGPA calculation (only for semesters with no failed subjects)
                total_cgpa_credits += total_credits
                total_cgpa_credit_points += total_credit_points
            
            sem_summary.append({
                "Semester": sem,
                "Total Marks": sem_total,
                "Max Marks": sem_max,
                "Percentage": round(sem_percent, 2),
                "Total Subjects": total_subjects,
                "Passed": passed_subjects,
                "Failed": failed_subjects,
                "Passed Credits": round(passed_credits, 2),
                "Credit Points": round(credit_points, 2),
                "SGPA": sgpa_display,
                "Status": status_msg
            })

        summary_df = pd.DataFrame(sem_summary)
        st.dataframe(summary_df, use_container_width=True)

        if not summary_df.empty:
            # Overall Statistics
            any_failed = len(summary_df[summary_df["Failed"] > 0]) > 0
            
            # CGPA Calculation - from ALL semesters with NO failed subjects
            if total_cgpa_credits > 0:
                overall_cgpa = round(total_cgpa_credit_points / total_cgpa_credits, 2)
            else:
                overall_cgpa = 0.00
            
            # Overall Percentage (excluding Always Pass subjects)
            df_no_always = df[df["Subject Type"] != "Always Pass"]
            total_marks = df_no_always["Total"].sum() if not df_no_always.empty else 0
            total_max = df_no_always["Max_Marks"].sum() if not df_no_always.empty else 0
            overall_percentage = (total_marks / total_max) * 100 if total_max > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if any_failed:
                    st.metric("Overall CGPA", f"{overall_cgpa:.2f}")
                    st.caption(f"Failed subjects exist - CGPA from cleared semesters only")
                else:
                    st.metric("Overall CGPA", f"{overall_cgpa:.2f}")
                    st.caption("All semesters cleared")
            with col2:
                st.metric("Overall Percentage", f"{overall_percentage:.2f}%")
            with col3:
                total_subjects_count = len(df)
                pass_count = len(df[df["Final Result"] == "Pass"])
                fail_count = len(df[df["Final Result"] == "Fail"])
                pass_rate = (pass_count/total_subjects_count)*100 if total_subjects_count > 0 else 0
                st.metric("Pass Rate", f"{pass_rate:.1f}%")
                st.caption(f"Failed: {fail_count}")
            with col4:
                # Find best SGPA from semesters with no failed subjects
                valid_sems = summary_df[summary_df["Status"] != "Not Cleared"]
                if not valid_sems.empty:
                    sgpa_values = []
                    for idx, row in valid_sems.iterrows():
                        try:
                            val = float(row["SGPA"])
                            sgpa_values.append((row["Semester"], val))
                        except:
                            pass
                    
                    if sgpa_values:
                        best_sem, best_sgpa = max(sgpa_values, key=lambda x: x[1])
                        st.metric("Best Semester", f"Sem {best_sem}", f"SGPA: {best_sgpa:.2f}")
                    else:
                        st.metric("Best Semester", "N/A", "")
                else:
                    st.metric("Best Semester", "N/A", "No cleared semesters")

            st.markdown("---")
            st.subheader("Performance Analysis")
            
            if any_failed:
                # Get all failed subjects
                failed_subjects_df = df[df["Final Result"] == "Fail"]
                st.error(f"FAILED SUBJECTS - {len(failed_subjects_df)} Subject(s) to Clear")
                st.warning("**Subjects to Clear:**")
                for idx, row in failed_subjects_df.iterrows():
                    st.write(f"• {row['Subject']} (Semester {row['Semester']})")
                st.info("**Note:** Semesters with failed subjects have SGPA = 0 and are NOT included in CGPA calculation.")
            else:
                if overall_cgpa >= 8.5:
                    statement = "EXCELLENT - Outstanding Performance"
                elif overall_cgpa >= 8.0:
                    statement = "EXCELLENT - Excellent Performance"
                elif overall_cgpa >= 7.0:
                    statement = "GOOD - Very Good Performance"
                elif overall_cgpa >= 6.0:
                    statement = "GOOD - Good Performance"
                elif overall_cgpa >= 5.0:
                    statement = "AVERAGE - Average Performance"
                elif overall_cgpa >= 4.0:
                    statement = "PASS - Pass Performance"
                else:
                    statement = "NEEDS IMPROVEMENT"
                st.info(f"**{statement}**")

        # Semester-wise SGPA Comparison
        st.subheader("Semester-wise SGPA Comparison")
        if not summary_df.empty:
            # Prepare data for chart
            chart_data = summary_df.copy()
            
            # Convert SGPA to numeric values (Not Cleared = 0)
            sgpa_values = []
            for idx, row in chart_data.iterrows():
                try:
                    if row["Status"] == "Not Cleared":
                        sgpa_values.append(0.0)
                    else:
                        val = float(row["SGPA"])
                        sgpa_values.append(val)
                except:
                    sgpa_values.append(0.0)
            
            chart_data["SGPA_Value"] = sgpa_values
            
            # Create bar chart
            fig_sgpa = px.bar(
                chart_data,
                x="Semester",
                y="SGPA_Value",
                text="SGPA_Value",
                title="Semester-wise SGPA",
                color="Status",
                color_discrete_map={"Not Cleared": "red", "Cleared": "blue"},
                range_y=[0, 10]
            )
            fig_sgpa.update_traces(
                texttemplate='%{text:.2f}', 
                textposition='outside'
            )
            fig_sgpa.update_layout(
                xaxis_title="Semester",
                yaxis_title="SGPA",
                showlegend=True,
                height=500
            )
            st.plotly_chart(fig_sgpa, use_container_width=True)
        else:
            st.info("No semester data available for chart.")
        
        # ------------------ KT MANAGEMENT SECTION ------------------
        st.markdown("---")
        st.subheader("KT (Failed Subjects) Management")
        
        # Get all failed subjects from marks
        failed_from_marks = df[df["Final Result"] == "Fail"]
        
        # Update KT list with failed subjects
        if not failed_from_marks.empty:
            existing_kt = st.session_state.get("kt_subjects", [])
            for idx, row in failed_from_marks.iterrows():
                found = False
                for e in existing_kt:
                    if e.get("subject_code") == row.get("Subject Code") and not e.get("cleared", False):
                        found = True
                        break
                if not found:
                    existing_kt.append({
                        "subject_code": row.get("Subject Code", ""),
                        "subject_name": row.get("Subject", ""),
                        "original_semester": row.get("Semester", 0),
                        "credits": row.get("Credits", 0),
                        "subject_type": row.get("Subject Type", "Theory"),
                        "max_marks": row.get("Max_Marks", 100),
                        "attempts": 1,
                        "cleared": False,
                        "status": "Pending"
                    })
            st.session_state["kt_subjects"] = existing_kt
            db.save_all_kt_subjects(gr, existing_kt)
            active_kt_subjects = [kt for kt in existing_kt if not kt.get("cleared", False)]
        
        if active_kt_subjects:
            for idx, kt in enumerate(active_kt_subjects):
                max_marks = kt.get("max_marks", 100)
                passing_marks = int(max_marks * 0.4)
                
                with st.expander(f"{kt['subject_name']} (Semester {kt['original_semester']})", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Subject Code:** {kt['subject_code']}")
                        st.write(f"**Subject Type:** {kt.get('subject_type', 'Theory')}")
                        st.write(f"**Credits:** {kt['credits']}")
                        st.write(f"**Max Marks:** {max_marks}")
                        st.write(f"**Passing Marks Required:** {passing_marks} (40%)")
                        st.write(f"**Attempts:** {kt.get('attempts', 1)}")
                    
                    with col2:
                        status_options = ["Pending", "Yet to Give", "Attempted"]
                        current_status = kt.get("status", "Pending")
                        status_idx = status_options.index(current_status) if current_status in status_options else 0
                        
                        status = st.selectbox(
                            "Preparation Status",
                            status_options,
                            index=status_idx,
                            key=f"kt_status_{idx}"
                        )
                        kt["status"] = status
                    
                    st.markdown("---")
                    st.subheader("Re-exam Marks Entry")
                    
                    reexam_col1, reexam_col2 = st.columns(2)
                    
                    with reexam_col1:
                        reexam_marks = st.number_input(
                            f"Marks Obtained in Re-exam (0-{max_marks})",
                            min_value=0,
                            max_value=max_marks,
                            value=kt.get("reexam_marks", 0),
                            key=f"kt_reexam_marks_{idx}"
                        )
                        kt["reexam_marks"] = reexam_marks
                    
                    with reexam_col2:
                        attempts = st.number_input(
                            "Total Attempts",
                            min_value=1,
                            max_value=5,
                            value=kt.get("attempts", 1),
                            key=f"kt_attempts_{idx}"
                        )
                        kt["attempts"] = attempts
                    
                    # Calculate grade based on subject's max marks
                    percentage = (reexam_marks / max_marks) * 100 if max_marks > 0 else 0
                    reexam_grade = get_grade(percentage)
                    reexam_grade_point = GRADE_POINTS.get(reexam_grade, 0)
                    
                    # Show if marks are sufficient to pass
                    if reexam_marks >= passing_marks:
                        st.success(f"**Passing Criteria Met!** {reexam_marks}/{max_marks} marks ({percentage:.1f}%) - Required {passing_marks} marks")
                    else:
                        st.warning(f"**Need {passing_marks - reexam_marks} more marks to pass** (Current: {reexam_marks}/{max_marks})")
                    
                    st.info(f"**Calculated Grade:** {reexam_grade} ({reexam_grade_point} points)")
                    
                    kt["reexam_grade"] = reexam_grade
                    kt["reexam_grade_point"] = reexam_grade_point
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Save Status", key=f"save_kt_{idx}"):
                            for i, main_kt in enumerate(st.session_state["kt_subjects"]):
                                if main_kt["subject_code"] == kt["subject_code"]:
                                    st.session_state["kt_subjects"][i] = kt
                                    break
                            db.save_all_kt_subjects(gr, st.session_state["kt_subjects"])
                            st.success(f"KT status for {kt['subject_name']} saved!")
                            st.rerun()
                    
                    with col2:
                        if st.button("Clear KT", key=f"clear_kt_{idx}"):
                            if reexam_marks >= passing_marks:
                                # Mark KT as cleared
                                kt["cleared"] = True
                                kt["status"] = "Cleared"
                                
                                # Create new entry for the subject with passed marks
                                kt_subject = {
                                    "Semester": kt["original_semester"],
                                    "Subject": kt['subject_name'],
                                    "Subject Code": kt['subject_code'],
                                    "Subject Type": f"{kt.get('subject_type', 'Theory')} (KT Cleared)",
                                    "Credits": kt['credits'],
                                    "IA": 0,
                                    "FA": 0,
                                    "ESE": 0,
                                    "Oral": 0,
                                    "Practical": 0,
                                    "Termwork": 0,
                                    "Total": reexam_marks,
                                    "Max_Marks": max_marks,
                                    "Percentage": round(percentage, 2),
                                    "Grade": reexam_grade,
                                    "Grade Point": reexam_grade_point,
                                    "Final Result": "Pass"
                                }
                                
                                # Update the semester marks
                                if kt["original_semester"] not in st.session_state["student_submissions"]:
                                    st.session_state["student_submissions"][kt["original_semester"]] = []
                                
                                # Remove the old failed entry and add the new passed entry
                                st.session_state["student_submissions"][kt["original_semester"]] = [
                                    s for s in st.session_state["student_submissions"][kt["original_semester"]] 
                                    if s.get("Subject Code") != kt['subject_code']
                                ]
                                st.session_state["student_submissions"][kt["original_semester"]].append(kt_subject)
                                
                                # Save to database
                                db.save_semester_marks(gr, kt["original_semester"], st.session_state["student_submissions"][kt["original_semester"]])
                                db.save_all_kt_subjects(gr, st.session_state["kt_subjects"])
                                
                                st.success(f"{kt['subject_name']} cleared successfully! This semester's SGPA will now be recalculated and included in CGPA.")
                                st.rerun()
                            else:
                                st.error(f"Cannot clear: {reexam_marks}/{max_marks} marks (Need {passing_marks} marks to pass)")
        else:
            st.success("No active KT subjects! All subjects cleared.")
        
        # ------------------ DOWNLOAD DATA ------------------
        st.markdown("---")
        st.subheader("Download Data")
        
        download_df = df.copy()
        download_df["Marks Obtained"] = download_df["Marks"]
        
        csv_columns = ["Semester", "Subject", "Subject Code", "Marks Obtained", "Percentage", 
                      "Grade", "Credits", "Grade Point", "Final Result"]
        available_csv_cols = [col for col in csv_columns if col in download_df.columns]
        
        csv_data = download_df[available_csv_cols].sort_values("Semester").to_csv(index=False)
        st.download_button(
            label="Download All Marks as CSV",
            data=csv_data,
            file_name=f"{st.session_state['student_details']['name']}_marks.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Navigation
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to Semester Entry", use_container_width=True):
                st.session_state["page"] = "semester_entry"
                st.rerun()
        with col2:
            if st.button("Home", use_container_width=True):
                st.session_state["page"] = "login"
                st.rerun()
