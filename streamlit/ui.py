import io
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import streamlit as st
from streamlit_chat import message
import json


BACKEND_UPLOAD_TEXT_URL = "http://localhost:8000/upload-text"
BACKEND_UPLOAD_FILE_URL = "http://localhost:8000/upload-file"
BACKEND_QUERY_URL = "http://localhost:8000/query"
BACKEND_INFO_URL = "http://localhost:8000/info"

num_entity = 0
num_relation = 0
entity_change = 0
relation_change = 0
info = requests.get(BACKEND_INFO_URL).json()
entity_change = int(info.get('num_entity')) - num_entity
num_entity += entity_change
relation_change = int(info.get('num_relation')) - num_relation
num_relation += relation_change


### Helper functions ###

if "temp" not in st.session_state:
    st.session_state.temp = ""

def submit_and_clear_input(key:str):
    if key in st.session_state:
        st.session_state.temp = st.session_state[key]
        st.session_state[key] = ""
    print(key + " : " + st.session_state.temp)

def send_file(file, file_name, content_type,  server_url: str):
    m = MultipartEncoder(fields={"file": (file_name, file, content_type)})
    r = requests.post(
        server_url, data=m, headers={"Content-Type": m.content_type}, timeout=8000
    )
    return r
 
def on_upload_click(text_input, url_input, file_input):
    response = None
    headers = {"Content-Type": "application/json"}
    if file_input:
        if file_input.name.endswith(".txt"):
            response = send_file(file_input, file_input.name, 'text/plain', BACKEND_UPLOAD_FILE_URL).json()
        elif file_input.name.endswith(".wav"):
            response = send_file(file_input, file_input.name, 'audio/wav', BACKEND_UPLOAD_FILE_URL).json()
        else:
            raise ValueError("Unsupported file type. Use 'txt' or 'wav'.")
    elif text_input:
        data = {'text': text_input}
        response = requests.post(BACKEND_UPLOAD_TEXT_URL, json=data, headers=headers, timeout=8000).json()
        st.rerun()
    elif url_input:
        data = {'url': url_input}
        response = requests.post(BACKEND_UPLOAD_TEXT_URL, json=data, headers=headers, timeout=8000).json()
        st.rerun()
    else:
        return
    print(type(response))
    print(response)  
    st.success(response.get("message"))
    # st.rerun()


### Construct UI ###
st.set_page_config(layout="wide", page_title="Knowledge Graph RAG")
st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """, unsafe_allow_html=True)

# Left sidebar
with st.sidebar:   
    st.write('''### Upload your data by:''')
    with st.form("input_data"):
        st.text_area("Input text directly", key="text_input", on_change=submit_and_clear_input("text_input"))
        text_input = st.session_state.temp
        st.text_input("Or paste a link to Youtube or Wikipedia", key="url_input", on_change=submit_and_clear_input("url_input"))
        url_input = st.session_state.temp 
        file_input = st.file_uploader("Or drop a text file or an audio file", key="file_input") 
        upload_clicked = st.form_submit_button("Upload", on_click=on_upload_click(text_input, url_input, file_input)) 
    st.divider()
    # st.write('''### Delete the knowledge graph:''')
    # delete_clicked = st.button("Clear database", type="primary", on_click=on_delete_click) 

# Main space
st.title("Knowledge Graph RAG :bookmark_tabs:")
if "user_msgs" not in st.session_state:
    st.session_state.user_msgs = []
if "system_msgs" not in st.session_state:
    st.session_state.system_msgs = []

col1, col2 = st.columns([2, 1])

# Display the chat history
col1.write("""Construct a knowledge graph from anything you upload and have a chat.""")
chatbox = col1.container(height=460, border=True)
with chatbox:
    if st.session_state["system_msgs"]:
        for i in range(0, len(st.session_state["system_msgs"])):
            message(st.session_state["user_msgs"][i], is_user=True, key=str(i) + "_user")
            message(st.session_state["system_msgs"][i], key = str(i) + "_assistant")
col1.text_input("Enter your question", key="user_input", on_change=submit_and_clear_input("user_input"))
user_input = st.session_state.temp


cypher_query = ""
# Handle chat
if user_input:
    with st.spinner("Processing your question..."):
        st.session_state.user_msgs.append(user_input)
        try:
            result = requests.post(BACKEND_QUERY_URL, json={'text': user_input}, headers={"Content-Type": "application/json"}, timeout=8000).json()      #handle_query(user_input)      
            print(result)
            intermediate_steps = result["intermediate_steps"]
            cypher_query = intermediate_steps[0]["query"]
            database_results = intermediate_steps[1]["context"]
            answer = result["result"]
            print("answer: " + answer)
            st.session_state.system_msgs.append(answer)
        except Exception as e:
            st.error("Failed to process question. Please try again.")
            print(e)
    # Re-run the script to update the chat display
    st.rerun()



entity_types = ["Person", "Organization", "Technology", "University", "Concept"]
relationship_types = ["WORK_AT", "DEVELOPE", "STUDY_AT", "PROPOSE", "RELEASE", "IS_RELATED_TO"]
with col2:
    col21, col22, col23, col24= st.columns([1,1,1,1])
    en_metric = col21.metric("Entities", value=num_entity, delta=entity_change)
    re_metric = col22.metric("Relations", value=num_relation, delta=relation_change)
    col23.metric("Ent. Types", value=len(entity_types))
    col24.metric("Rel. Types", value=len(relationship_types))
    selected_entity_types = st.multiselect("Entity Types", entity_types, entity_types, disabled=True)
    selected_relationship_types = st.multiselect("Relationship Types", relationship_types, relationship_types, disabled=True)

    st.text_area("Last Cypher Query", cypher_query, key="_cypher", height=200)
    # st.text_area("Last Database Results", database_results, key="_database", height=200)


### Handle interactions ###








# if st.button("Get segmentation map"):

#     col1, col2 = st.columns(2)

#     if file_input:
#         segments = process(input_image, backend)
#         original_image = Image.open(input_image).convert("RGB")
#         segmented_image = Image.open(io.BytesIO(segments.content)).convert("RGB")
#         col1.header("Original")
#         col1.image(original_image, use_column_width=True)
#         col2.header("Segmented")
#         col2.image(segmented_image, use_column_width=True)

#     else:
#         # handle case with no image
#         st.write("Insert an image!")

# st.success('This is a success message!', icon="✅")
# st.error('This is an error', icon="🚨")
