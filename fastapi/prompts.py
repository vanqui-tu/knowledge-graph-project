from langchain.prompts.prompt import PromptTemplate


# Prompt templates for QA
CYPHER_GENERATION_TEMPLATE = """
You are an expert Neo4j Cypher translator who converts English to Cypher based on the Neo4j Schema provided, following the instructions below:
1. Generate Cypher query compatible ONLY for Neo4j Version 5
2. Do not use EXISTS, SIZE, HAVING keywords in the cypher. Use alias when using the WITH keyword
3. Use only Nodes and relationships mentioned in the schema
4. Always do a case-insensitive and fuzzy search for any properties related search. Eg: to search for a Client, use `toLower(client.id) contains 'neo4j'`. To search for Slack Messages, use 'toLower(SlackMessage.text) contains 'neo4j'`. To search for a project, use `toLower(project.summary) contains 'logistics platform' OR toLower(project.name) contains 'logistics platform'`.)
5. Never use relationships that are not mentioned in the given schema
6. When asked about projects, Match the properties using case-insensitive matching and the OR-operator, E.g, to find a logistics platform -project, use `toLower(project.summary) contains 'logistics platform' OR toLower(project.name) contains 'logistics platform'`.

schema: {schema}

Examples:
Question: Which client's projects use most of our people?
Answer: ```MATCH (c:CLIENT)<-[:HAS_CLIENT]-(p:Project)-[:HAS_PEOPLE]->(person:Person)
RETURN c.name AS Client, COUNT(DISTINCT person) AS NumberOfPeople
ORDER BY NumberOfPeople DESC```
Question: Which person uses the largest number of different technologies?
Answer: ```MATCH (person:Person)-[:USES_TECH]->(tech:Technology)
RETURN person.name AS PersonName, COUNT(DISTINCT tech) AS NumberOfTechnologies
ORDER BY NumberOfTechnologies DESC```

Question: {question}
"""

CYPHER_QA_TEMPLATE = """You are an assistant that helps to form nice and human understandable answers.
The information part contains the provided information that you must use to construct an answer.
The provided information is authoritative, you must never doubt it or try to use your internal knowledge to correct it.
Make the answer sound as a response to the question. Do not mention that you based the result on the given information.
If the provided information is empty, say that you don't know the answer.
Final answer should be easily readable and structured.
Information:
{context}

Question: {question}
Helpful Answer:"""


# Construct prompts for QA
cypher_prompt = PromptTemplate(
    template = CYPHER_GENERATION_TEMPLATE,
    input_variables = ["schema", "question"]
)
qa_prompt = PromptTemplate(
    template=CYPHER_QA_TEMPLATE,
    input_variables=["context", "question"]
)


# Prompt template for KG construction (Now we use a pre-defined graph schema)
RELATION_EXTRACTION_TEMPLATE = """
From the text below, extract the following Entities & relationships described in the mentioned format 
0. ALWAYS FINISH THE OUTPUT. Never send partial responses
1. First, look for these Entity types in the text and generate as comma-separated format similar to entity type.
   `id` property of each entity must be alphanumeric and must be unique among the entities. You will be referring this property to define the relationship between entities. Do not create new entity types that aren't mentioned below. You will have to generate as many entities as needed as per the types below:
    Entity Types:
    label:'Person',id:string,name:string,dob:string //`id` property is the name of the person, in lower-case; `name` is the person's name, as spelled in the text; `dob` is his or her date of birth
    label:'Technology',id:string,name:string,releaseTime:string //`id` property is the name of the technology, in lower-case; `releaseTime` is the date or year it was released
    label:'Organization',id:string,name:string,description:string //`id` property is the name of the organization, in lower-case; `description` is a brief description about the organization (e.g: what it is and in which industry it operates)
    label:'University',id:string,name:string //`id` property is the name of the university, in lower-case
    label:'Concept',id:string,name:string,description:string //`id` property is the name of the technology, in lower-case; `description` is a brief description about the concept

2. Next generate each relationships as triples of head, relationship and tail. To refer the head and tail entity, use their respective `id` property. Relationship property should be mentioned within brackets as comma-separated. They should follow these relationship types below. You will have to generate as many relationships as needed as defined below:
    Relationship types:
    person|WORK_AT|organization 
    person|DEVELOPE|technology
    person|STUDY_AT|university
    person|PROPOSE|concept
    organization|RELEASE|technology
    concept|IS_RELATED_TO|concept

3. The output should look like :
{
    "entities": [{"label":"Person","id":string,"name":string,"dob":string}],
    "relationships": ["personid|WORK_AT|organizationid"]
}

Case Sheet:
$ctext
"""