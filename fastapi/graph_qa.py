from langchain_community.graphs import Neo4jGraph
from langchain.chains import GraphCypherQAChain
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)
from prompts import cypher_prompt, qa_prompt
import dotenv
import os
dotenv.load_dotenv()

# Google Gemini configuration
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    safety_settings = {
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE, 
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE, 
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE, 
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    },
    google_api_key=os.getenv("GEMINI_KEY"),
    max_output_tokens=5000,
    temperature=0
)

# Neo4j configuration
neo4j_url = os.getenv("NEO4J_URI")
neo4j_user = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")
graph = Neo4jGraph(url=neo4j_url, username=neo4j_user, password=neo4j_password)

# LangChain QA on knowledge graph
def qa_on_graph(user_input):
    # graph = Neo4jGraph(url=neo4j_url, username=neo4j_user, password=neo4j_password)
    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        verbose=True,
        return_intermediate_steps=True,
        cypher_prompt=cypher_prompt,
        qa_prompt=qa_prompt,
        validate_cypher=True
        )
    result = chain.invoke(user_input)
    print(result)
    return result