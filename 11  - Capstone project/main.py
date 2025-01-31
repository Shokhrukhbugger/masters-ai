import os
import streamlit as st
from openai import OpenAI
import sqlite3
from tools.movie_search_utils import ImdbMovieLinkFetcher
from tools.database_interaction import DatabaseInteraction
import logging
from conversation import Conversation
import sys

MODEL = "gpt-4o-mini"
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
imdb_link_fetcher = ImdbMovieLinkFetcher()

st.set_page_config(layout="wide", page_title="EPAM reference", page_icon="🤩")

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s - %(asctime)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("public")


def chat_completion_request(messages, functions=None, model=MODEL):
    response = client.chat.completions.create(
        messages=messages,
        model=model,
        tools=functions,
    )
    return response


if __name__ == '__main__':
    conversation = Conversation()
    connection = sqlite3.connect("./movies_2.sqlite")
    database_commands = DatabaseInteraction(logger, connection)
    db_schema = database_commands.get_db_schema()
    logger.info(f"database schema: \n{db_schema}")

tools = [
    {
        "type": "function",
        "function": {
            "name": "ask_database",
            "description": "Use this function to answer user questions about data. Output should be a fully formed SQL query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": f"""
                            SQL query extracting info to answer the user's question.
                            SQL should be written using this database schema:
                            {db_schema}
                            The query should be returned in plain text, not in JSON.
                            """,
                    }
                },
                "required": ["query"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_movie_link",
            "description": "Use this function to find the link to a movie by its title, if requested by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title of the movie for which the link is requested."
                    }
                },
                "required": [
                    "title"
                ],
            }
        }
    }
]


def chat_completion_with_tools_execution(messages):
    """This function makes a ChatCompletion API call and if a function call is requested, executes the function"""
    try:

        response = chat_completion_request(messages, tools)
        full_message = response.choices[0]
        if full_message.finish_reason == "tool_calls":
            logger.info("Function generation requested, calling function")
            result = call_function(messages, full_message)
            return result.choices[0].message.content
        else:
            logger.info("Function not required, responding to user")
        return response.choices[0].message.content
    except Exception as e:
        logger.error("Unable to generate ChatCompletion response")
        logger.info(f"Exception: {e}")
        return e


def try_ask_database(full_message, messages):
    query = eval(full_message.message.tool_calls[0].function.arguments)
    logger.info(f"Prepped query is {query}")

    try:
        results = database_commands.fetch_from_db(query["query"])
    except Exception as e:
        logger.error(e)

        # This following block tries to fix any issues in query generation with a subsequent call
        messages.append(
            {
                "role": "system",
                "content": f"""Query: {query['query']}
                    The previous query received the error {e}. 
                    Please return a fixed SQL query in plain text.
                    Your response should consist of ONLY the SQL query with the separator sql_start at the beginning and sql_end at the end""",
            }
        )
        response = chat_completion_request(messages, model=MODEL)

        # Retrying with the fixed SQL query. If it fails a second time we exit.
        try:
            cleaned_query = response.choices[0].message.content.split("sql_start")[1]
            cleaned_query = cleaned_query.split("sql_end")[0]
            logger.info(f"cleaned query: {cleaned_query}")
            results = database_commands.fetch_from_db(cleaned_query)
            logger.info("Got on second try")

        except Exception as e:
            logger.info("Second failure, exiting")

            logger.error("Function execution failed")
            logger.error(f"Error message: {e}")
            logger.error(f"{cleaned_query}")
            logger.error(f"{database_commands.get_db_schema()}")

    messages.append(
        {"role": "function", "name": "ask_database", "content": str(results)}
    )

    try:
        response = chat_completion_request(messages)
        return response
    except Exception as e:
        print(type(e))
        print(e)
        raise Exception("Function chat request failed")


def get_imdb_link(full_message, messages):
    movie_title = eval(full_message.message.tool_calls[0].function.arguments)
    result = imdb_link_fetcher.get_imdb_link(movie_title=movie_title)
    messages.append(
        {"role": "function", "name": "get_movie_link", "content": str(result)}
    )
    try:
        response = chat_completion_request(messages)
        return response
    except Exception as e:
        print(type(e))
        print(e)
        raise Exception("Function chat request failed")


def call_function(messages, full_message):
    """Executes function calls using model generated function arguments."""
    function_call_name = full_message.message.tool_calls[0].function.name
    match function_call_name:
        case "ask_database":
            return try_ask_database(full_message, messages)
        case "get_movie_link":
            return get_imdb_link(full_message, messages)

        case _:
            raise Exception("Function does not exist and cannot be called")


# Streamlit - User interface
st.title("MovieGPT: ChatGPT-powered Movie Assistant")
st.write("Ask questions about movies, and MovieGPT will find answers using both a database and external tools!")

# SESSION STATE INITIALIZATION
if "messages" not in st.session_state:
    st.session_state.messages = []

# DISPLAY CONVERSATION HISTORY
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about movies (e.g., 'Hi, find the movie Doom?')"):
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

        agent_system_message = """
            You are MovieGPT, a helpful assistant who gets answers to user questions about movies from the Database.
            Provide as many details as possible to your users. Begin!"""
        sql_conversation = Conversation()
        sql_conversation.add_message("system", agent_system_message)
        sql_conversation.add_message("user", prompt)

    with st.chat_message("assistant"):
        try:
            chat_response = chat_completion_with_tools_execution(sql_conversation.conversation_history)
            st.markdown(chat_response)
            st.session_state.messages.append({"role": "assistant", "content": chat_response})
        except Exception as e:
            st.error(f"An error occurred while processing your request: {e}")

    sql_conversation.add_message("assistant", chat_response)