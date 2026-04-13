import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import json

# Supabase credentials
SUPABASE_URL = "https://pnuyenxpnzzmvgvlpnmn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBudXllbnhwbnp6bXZndmxwbm1uIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYwODc1MDAsImV4cCI6MjA5MTY2MzUwMH0.HNDKgM-TiQmkLGawCKHNS0j4lGBR46RSKTMP9bjXGAg"

class Database:
    def __init__(self):
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.create_tables()
    
    def create_tables(self):
        """Create tables in Supabase"""
        try:
            # Create student_details table
            self.supabase.table('student_details').insert({}).execute()
        except:
            # Table creation SQL - Run once in Supabase SQL editor
            print("Please run the SQL script in Supabase SQL editor")
            pass
    
    # ==================== STUDENT METHODS ====================
    
    def save_student_details(self, gr_number, name, email, department, current_semester, batch=None):
        try:
            data = {
                "gr_number": gr_number,
                "name": name,
                "email": email,
                "department": department,
                "current_semester": current_semester,
                "batch": batch
            }
            result = self.supabase.table('student_details').upsert(data).execute()
            return True
        except Exception as e:
            print(f"Error saving student: {e}")
            return False
    
    def get_student_details(self, gr_number):
        try:
            result = self.supabase.table('student_details').select("*").eq("gr_number", gr_number).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error getting student: {e}")
            return None
    
    def save_semester_marks(self, gr_number, semester, subjects_data):
        try:
            subjects_json = json.dumps(subjects_data)
            data = {
                "gr_number": gr_number,
                "semester": semester,
                "subject_data": subjects_json,
                "saved_at": datetime.now().isoformat()
            }
            
            # Check if exists
            existing = self.supabase.table('student_marks').select("*").eq("gr_number", gr_number).eq("semester", semester).execute()
            
            if existing.data:
                self.supabase.table('student_marks').update(data).eq("gr_number", gr_number).eq("semester", semester).execute()
            else:
                self.supabase.table('student_marks').insert(data).execute()
            return True
        except Exception as e:
            print(f"Error saving marks: {e}")
            return False
    
    def get_all_student_marks(self, gr_number):
        try:
            result = self.supabase.table('student_marks').select("*").eq("gr_number", gr_number).execute()
            
            all_marks = {}
            for row in result.data:
                semester = row['semester']
                subject_data = json.loads(row['subject_data'])
                all_marks[semester] = subject_data
            
            return all_marks
        except Exception as e:
            print(f"Error getting marks: {e}")
            return {}
    
    # ==================== KT METHODS ====================
    
    def save_all_kt_subjects(self, gr_number, kt_list):
        try:
            # Delete existing
            self.supabase.table('kt_subjects').delete().eq("gr_number", gr_number).execute()
            
            # Insert new
            for kt in kt_list:
                data = {
                    "gr_number": gr_number,
                    "subject_code": kt["subject_code"],
                    "subject_name": kt["subject_name"],
                    "original_semester": kt["original_semester"],
                    "credits": kt["credits"],
                    "attempts": kt.get("attempts", 1),
                    "cleared": 1 if kt.get("cleared", False) else 0,
                    "cleared_semester": kt.get("cleared_semester"),
                    "reexam_marks": kt.get("reexam_marks", 0),
                    "reexam_grade": kt.get("reexam_grade", ""),
                    "reexam_grade_point": kt.get("reexam_grade_point", 0),
                    "status": kt.get("status", "Pending")
                }
                self.supabase.table('kt_subjects').insert(data).execute()
            return True
        except Exception as e:
            print(f"Error saving KT: {e}")
            return False
    
    def get_kt_subjects(self, gr_number):
        try:
            result = self.supabase.table('kt_subjects').select("*").eq("gr_number", gr_number).execute()
            
            kt_list = []
            for row in result.data:
                kt_list.append({
                    "subject_code": row['subject_code'],
                    "subject_name": row['subject_name'],
                    "original_semester": row['original_semester'],
                    "credits": row['credits'],
                    "attempts": row['attempts'],
                    "cleared": bool(row['cleared']),
                    "cleared_semester": row.get('cleared_semester'),
                    "reexam_marks": row.get('reexam_marks', 0),
                    "reexam_grade": row.get('reexam_grade', ""),
                    "reexam_grade_point": row.get('reexam_grade_point', 0),
                    "status": row.get('status', "Pending")
                })
            return kt_list
        except Exception as e:
            print(f"Error getting KT: {e}")
            return []
    
    # ==================== TEACHER METHODS ====================
    
    def save_teacher(self, name, email, password, department):
        try:
            data = {
                "name": name,
                "email": email,
                "password": password,
                "department": department
            }
            result = self.supabase.table('teachers').upsert(data).execute()
            return {"name": name, "email": email, "department": department}
        except Exception as e:
            print(f"Error saving teacher: {e}")
            return None
    
    def verify_teacher(self, email, password):
        try:
            result = self.supabase.table('teachers').select("*").eq("email", email).eq("password", password).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error verifying teacher: {e}")
            return None
    
    # ==================== BATCH SUBJECT METHODS ====================
    
    def add_batch_subject(self, batch, department, semester, subject_code, subject_name, 
                          subject_type, paper_format=None, lab_type=None, 
                          termwork_max=None, credits=None):
        try:
            data = {
                "batch": batch,
                "department": department,
                "semester": semester,
                "subject_code": subject_code,
                "subject_name": subject_name,
                "subject_type": subject_type,
                "paper_format": paper_format,
                "lab_type": lab_type,
                "termwork_max": termwork_max,
                "credits": credits
            }
            result = self.supabase.table('batch_subjects').upsert(data).execute()
            return True
        except Exception as e:
            print(f"Error adding subject: {e}")
            return False
    
    def get_batch_subjects(self, batch, department, semester):
        try:
            result = self.supabase.table('batch_subjects').select("*").eq("batch", batch).eq("department", department).eq("semester", semester).execute()
            return result.data
        except Exception as e:
            print(f"Error getting subjects: {e}")
            return []
    
    def delete_batch_subject(self, batch, department, semester, subject_code):
        try:
            self.supabase.table('batch_subjects').delete().eq("batch", batch).eq("department", department).eq("semester", semester).eq("subject_code", subject_code).execute()
            return True
        except Exception as e:
            print(f"Error deleting subject: {e}")
            return False
    
    # ==================== STUDENT FILTERING METHODS ====================
    
    def get_students_by_batch_and_dept(self, batch, department):
        try:
            result = self.supabase.table('student_details').select("*").eq("batch", batch).eq("department", department).execute()
            return result.data
        except Exception as e:
            print(f"Error getting students: {e}")
            return []
    
    def get_all_students(self):
        try:
            result = self.supabase.table('student_details').select("*").execute()
            return result.data
        except Exception as e:
            print(f"Error getting students: {e}")
            return []
    
    def close(self):
        pass