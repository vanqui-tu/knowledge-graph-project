import os
import google.generativeai as genai
from google.generativeai.types import generation_types
from string import Template
import json
from neo4j import GraphDatabase
import glob
from timeit import default_timer as timer
from dotenv import load_dotenv
from time import sleep
import re
from youtube_transcript_api import YouTubeTranscriptApi 
from urllib.parse import urlparse,parse_qs
from langchain_community.document_loaders import WikipediaLoader, WebBaseLoader
from prompts import RELATION_EXTRACTION_TEMPLATE

load_dotenv()

# Gemini API configuration
safety_settings = [
    {
        "category": "HARM_CATEGORY_DANGEROUS",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
    },
]
generation_config = generation_types.GenerationConfig(temperature=0, max_output_tokens=10000)
system_instruction = "You are a helpful IT-project and account management expert who extracts information from documents."
genai.configure(api_key=os.getenv('GEMINI_KEY'))
GEMINI = genai.GenerativeModel('gemini-1.5-flash', safety_settings = safety_settings, generation_config = generation_config, system_instruction = system_instruction)

# Neo4j configuration & constraints
neo4j_url = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")
gds = GraphDatabase.driver(neo4j_url, auth=(neo4j_user, neo4j_password))
gds.verify_connectivity()

# Function to call the Gemini API
def process_gemini(file_prompt):
    response = GEMINI.generate_content(file_prompt)
    nlp_results = response.text
    sleep(3)
    return remove_outer_braces(nlp_results)

def remove_outer_braces(input_string):
    if (input_string[0] == '{' and input_string[-1] == '}'):
        return input_string
    start_index = input_string.find('{')
    end_index = input_string.rfind('}')    
    if start_index == -1 or end_index == -1:
        return input_string    
    return input_string[start_index:end_index+1]

# Function to take a file and a prompt template, and return a json-object of all the entities and relationships
def extract_entities_relationships(file, prompt_template):
    start = timer()
    print(f"Extracting entities and relationships for {file}")
    try:
        with open(file, "r") as f:
            text = f.read().rstrip()
            prompt = Template(prompt_template).substitute(ctext=text)
            result = process_gemini(prompt)
    except Exception as e:
        print(f"Error processing {file}: {e}")
    end = timer()
    print(f"Extract pipeline completed in {end-start} seconds.")
    return result


# Function to take a json-object of entitites and relationships and generate cypher query for creating those entities
def generate_cypher(string_json):
    e_statements = []
    r_statements = []
    e_label_map = {}
    # loop through our json object 
    # for entity in json_obj["entities"]:
    json_obj = json.loads(string_json)
    for key, value in json_obj.items():
        if key == "entities":
            for entity in value:
                label = entity["label"]
                id = entity["id"]
                id = id.replace("-", "").replace("_", "")
                properties = {k: v for k, v in entity.items() if k not in ["label", "id"]}
                # cypher to add new entities
                cypher = f'MERGE (n:{label} {{id: "{id}"}})'
                if properties:
                    props_str = ", ".join(
                        [f'n.{key} = "{val}"' for key, val in properties.items()]
                    )
                    cypher += f" ON CREATE SET {props_str}"
                e_statements.append(cypher)
                e_label_map[id] = label
        elif key == "relationships":
            for rs in value:
                src_id, rs_type, tgt_id = rs.split("|")
                src_id = src_id.replace("-", "").replace("_", "")
                tgt_id = tgt_id.replace("-", "").replace("_", "")
                src_label = e_label_map[src_id]
                tgt_label = e_label_map[tgt_id]
                # cypher to add new relations 
                cypher = f'MERGE (a:{src_label} {{id: "{src_id}"}}) MERGE (b:{tgt_label} {{id: "{tgt_id}"}}) MERGE (a)-[:{rs_type}]->(b)'
                r_statements.append(cypher)

    with open("latest_update_cypher.txt", "w") as outfile:
        outfile.write("\n".join(e_statements + r_statements))

    return e_statements + r_statements

# Full pipeline extract-cypher-execute
def construct_graph(filepath):
    entities_relationships = extract_entities_relationships(filepath, RELATION_EXTRACTION_TEMPLATE)
    cypher_statements = generate_cypher(entities_relationships)
    for i, stmt in enumerate(cypher_statements):
        print(f"Executing cypher statement {i+1} of {len(cypher_statements)}")
        try:
            gds.execute_query(stmt)
        except Exception as e:
            with open("failed_statements.txt", "w") as f:
                f.write(f"{stmt} - Exception: {e}\n")
            break


# Helper functions to process uploaded URL
def get_youtube_transcript(youtube_id):
  try:
    transcript = YouTubeTranscriptApi.get_transcript(youtube_id)
    return transcript
  except Exception as e:
    message = f"Youtube transcript is not available for youtube Id: {youtube_id}"
    raise Exception(message)
  
def get_documents_from_Wikipedia(wiki_query:str, language:str):
  try:
    pages = WikipediaLoader(query=wiki_query.strip(), lang=language, load_max_docs=1, load_all_available_meta=False).load()
    file_name = wiki_query.strip()
    return file_name, pages
  except Exception as e:
    message = f"Cannot load Wikipedia page."
    raise Exception(message)

def process_url(url:str=None):
    def create_youtube_url(url):
        you_tu_url = "https://www.youtube.com/watch?v="
        u_pars = urlparse(url)
        quer_v = parse_qs(u_pars.query).get('v')
        if quer_v:
            return  you_tu_url + quer_v[0].strip()
        pth = u_pars.path.split('/')
        if pth:
            return you_tu_url + pth[-1].strip()
        
    try:
        # For Youtube URL
        # if re.match('(?:https?:\/\/)?(?:www\.)?youtu\.?be(?:\.com)?\/?.*(?:watch|embed)?(?:.*v=|v\/|\/)([\w\-_]+)\&?', url.strip()):
        if re.match(r'(?:https?://)?(?:www\.)?youtu\.?be(?:\.com)?/?.*(?:watch|embed)?(?:.*v=|v/|/)([\w\-_]+)\&?', url.strip()):
          youtube_url = create_youtube_url(url.strip())
          youtube_id = re.search(r'(?:v=)([0-9A-Za-z_-]{11})\s*',youtube_url)
          transcript = get_youtube_transcript(youtube_id)
          return transcript[:1000], f"youtube_{youtube_id}"
        
        # For Wiki URL
        wiki_query_id=''
        wikipedia_url_regex = r'https?:\/\/(www\.)?([a-zA-Z]{2,3})\.wikipedia\.org\/wiki\/(.*)'        
        match = re.search(wikipedia_url_regex, url.strip())
        if match:
            language = match.group(2)
            wiki_query_id = match.group(3)
            pages = WikipediaLoader(query=wiki_query_id.strip(), lang=language, load_max_docs=1, load_all_available_meta=True).load()
            return pages[0].page_content[:1000], f"wiki_{wiki_query_id.strip()}"
    except Exception as e:
      raise Exception(e)

# Function to query the number of nodes and relations
def get_info():
    with gds.session() as session:
        result = session.run("MATCH (n) RETURN count(n)")
        node_count = result.single()[0]
    with gds.session() as session:
        result = session.run("MATCH ()-[r]->() RETURN count(r)")
        relation_count = result.single()[0]
    return node_count, relation_count
