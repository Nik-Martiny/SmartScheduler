import streamlit as st

class Course:
    def __init__(self, course_name):
        self.course_name = course_name


s = st.chat_input("Enter the course name")


courses = [Course(s)]

for course in courses:
    st.write(course.course_name)
