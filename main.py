from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_community.chat_models import ChatOllama
from langchain.agents import AgentType
from langchain.prompts.chat import ChatPromptTemplate
from langchain_experimental.sql import SQLDatabaseChain
from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy import create_engine, MetaData
import time

# Initialize FastAPI app
app = FastAPI()

# Initialize LLM and database connection
ollama_llm = "mistral"
llm = ChatOllama(model=ollama_llm)

connection_string = f"postgresql+psycopg2://postgres:root@localhost:5432/postgres"
engine = create_engine(connection_string)
metadata = MetaData()
metadata.reflect(bind=engine)

db = SQLDatabase(engine=engine)

# Define the request model
class QuestionRequest(BaseModel):
    question: str

# Function to get the prompt
def get_prompt():
    QUERY = ChatPromptTemplate.from_messages(
        [
            ("system",
             """
             You are an helpful AI assistant expert in querying SQL databases to find answers to user's question.
             Do not mention Answer: while generating sql query.
             Create and execute a syntactically correct SQL Server query on 'public' schema.
             You must have to use lower case for all letters of user names while creating query on users table.
             If user mention create account in question, then you must perform query on users table.
             If user want to cancle only its appointment then you must perform DELETE operation.
             if user has only one record in appointments table then perform query on name only, dont check for other details, While performing UPDATE and DELETE operations on appointments.
             Perform any Data Manipulation Language (DML) operations such as INSERT, UPDATE, DELETE, or DROP.
             Double-check my queries before execution and provide a response based on the query results.
             Analyze full database tables and columns properly and generate SQL queries based on that.
             User will ask question about users, you have to provide detailed information of users.
             There might be possible of duplicate users name but their information may differ. So ask user which user information they want.
             Make answer in proper human readable sentance of asked question.
             Provide answers and respone in straight-forword way.
             Don't provide and mention any irrelevant sentances and word like 'in the database, table,  source, and more' in answers.
             If a question doesn't relate to the database, you'll respond with "I don't know".
             Do not include '\' in query.
             Do not make user name's first letter in Upper case.
             Do not change status of appointments while performing UPDATE query on apppintment.
             Note : Do not mention 'Answer:' in 'SQLQuery:'.
            """
             ),
            ("user", "{question}"),
        ])
    return QUERY

# Initialize the SQLDatabaseChain
db_chain = SQLDatabaseChain(llm=llm, database=db, top_k=100, verbose=True)


@app.get("/")
async def home():
    response = {
                "message": "welcome to fast api"
            }
    return response

# Define the endpoint
@app.post("/ask-question")
async def ask_question(request: QuestionRequest):
    user_question = request.question
    if user_question:
        start_time = time.time()
        prompt = get_prompt().format(question=user_question)
        try:
            result = db_chain.invoke(prompt)
            end_time = time.time()
            response = {
                "answer": result["result"],
                "response_time": end_time - start_time
            }
            print(response)
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail="Question cannot be empty")