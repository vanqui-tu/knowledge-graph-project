import io
from starlette.responses import Response
from fastapi import FastAPI, File , UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from graph_qa import *
from graph_construct import *
from prompts import RELATION_EXTRACTION_TEMPLATE
import speech_recognition as sr

class TextInput(BaseModel):
    text: Optional[str] = None
    url: Optional[str] = None

app = FastAPI(
    title="Knowledge Graph RAG - Backend",
    description="""Construct a knowledge graph from anything you upload and have a chat.
    This back-end uses Neo4j database to manage and store knowledge graph, LangChain with Gemini API to construct and chat with the knowledge graph. 
    Visit this URL at port 8501 for the streamlit interface.""",
    version="0.1.0",
)

count_direct_text_upload = 0
count_url_upload = 0
count_file_upload = 0

@app.post("/upload-text")
def handle_text(input: TextInput):
    print(input)
    """Extract relations in text content, then add to knowledge graph."""
    global count_direct_text_upload, count_url_upload
    filepath = ""
    if input.text:
        filepath = f"./uploaded-content/direct_text_{count_direct_text_upload}.txt"
        count_direct_text_upload += 1
        with open(filepath, "w") as file:
            file.write(input.text)        
    elif input.url:
        content, filename = process_url(input.url)
        filepath = f"./uploaded-content/{filename}.txt"
        count_url_upload += 1
        with open(filepath, "w") as file:
            file.write(content.encode("ascii", "ignore").decode("ascii"))    
    else:
        # raise HTTPException(status_code=400, detail="Empty input.")
        return JSONResponse(status_code=400, content={"message": "Empty input."})
    construct_graph(filepath)  
    node_count, relation_count = get_info()  
    return JSONResponse(content={"message": "Text/URL processed.", "num_entity": node_count, "num_relation": relation_count}) 

@app.post("/upload-file")
async def handle_file(file : UploadFile  = File(...)):
    """Extract relations in text/audio file, then add to knowledge graph."""
    global count_file_upload
    filepath = ""
    if file.content_type == "text/plain":
        filepath = f"./uploaded-content/{file.filename}"
        count_file_upload += 1
        # Read the file contents asynchronously
        contents = await file.read()
        with open(filepath, "w") as saved_file:
            saved_file.write(str(contents.decode("utf-8")))
    elif file.content_type == "audio/wav":
        contents = await file.read()
        recognizer = sr.Recognizer()
        audio_file = io.BytesIO(contents)
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source, duration=60)
            try:
                transcript = recognizer.recognize_google(audio_data, language='en')
            except sr.UnknownValueError:
                return JSONResponse(content={"error": "Speech was unintelligible"}, status_code=400)
            except sr.RequestError as e:
                return JSONResponse(content={"error": f"Could not request results; {e}"}, status_code=500)
        filepath = f"./uploaded-content/{os.path.splitext(file.filename)[0].txt}"
        count_file_upload += 1
        with open(filepath, "w") as saved_file:
            saved_file.write(transcript)
    else:
        # raise HTTPException(status_code=400, detail="Unsupported file type.")
        return JSONResponse(status_code=400, content={"message": "Unsupported file type."})
    construct_graph(filepath) 
    node_count, relation_count = get_info() 
    return JSONResponse(content={"message": "File processed.", "num_entity": node_count, "num_relation": relation_count})

@app.post("/query")
def handle_query(input: TextInput):
    """Query to knowledge graph, then provide an answer. Therefore, only ask RELEVANT things."""
    if input.text:
        return JSONResponse(content=qa_on_graph(input.text))
    else:
        # raise HTTPException(status_code=400, detail="Empty input.")
        return JSONResponse(status_code=400, content={"message": "Empty input."})
    
@app.get("/info")
def handle_get_info():
    node_count, relation_count = get_info() 
    return JSONResponse(content={"num_entity": node_count, "num_relation": relation_count})
    
