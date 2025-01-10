import streamlit as st
from google import genai
from google.genai import types
import gemini20functiongeneral
import helpercode
import logging
#Hitesh Comments Added
#Hitesh Comments Added in GitHub

PROJECT_ID = helpercode.get_project_id()
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.0-flash-exp"


def handle_api_response(message_placeholder, api_requests_and_responses, backend_details):
    backend_details += "- Function call:\n"
    backend_details += (
                        "   - Function name: ```"
                        + str(api_requests_and_responses[-1][0])
                        + "```"
                    )
    backend_details += "\n\n"
    backend_details += (
                        "   - Function parameters: ```"
                        + str(api_requests_and_responses[-1][1])
                        + "```"
                    )
    backend_details += "\n\n"
    backend_details += (
                        "   - API response: ```"
                        + str(api_requests_and_responses[-1][2])
                        + "```"
                    )
    backend_details += "\n\n"
    with message_placeholder.container():
        st.markdown(backend_details)
    return backend_details

market_query20_tool = types.Tool(
    function_declarations=[
        # geminifunctionsbq.sql_query_func,
        # geminifunctionsbq.list_datasets_func,
        # geminifunctionsbq.list_tables_func,
        # geminifunctionsbq.get_table_func,
        # geminifunctionsbq.sql_query_func,
        gemini20functiongeneral.current_date,
        # gemini20functionalphavantage.monthly_stock_price,
        # gemini20functionalphavantage.market_sentiment,
    ],
)

SYSTEM_INSTRUCTION = """
You are a helpful assistant that can answer questions and help with tasks.
Any date information should be retrieved from the current_date function.
"""

generate_config_20 = types.GenerateContentConfig(
    temperature = 1,
    top_p = 0.95,
    max_output_tokens = 8192,
    response_modalities = ["TEXT"],
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
    system_instruction=[types.Part.from_text(SYSTEM_INSTRUCTION)],
    tools= [market_query20_tool],
)

st.title("Hello World")
st.write("This is a simple Streamlit app.")

#initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "aicontent" not in st.session_state:
    st.session_state.aicontent = []

if "gemini_client" not in st.session_state:
    st.session_state.gemini_client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=LOCATION
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        st.session_state.aicontent.append(types.Content(role='user', parts=[types.Part(text=prompt)]))
        response =st.session_state.gemini_client.models.generate_content(model=MODEL_NAME, 
                                                    contents=st.session_state.aicontent, 
                                                    config=generate_config_20)
        response = response.candidates[0].content.parts[0]
        api_requests_and_responses = []
        backend_details = ""
        function_calling_in_process = True
        while function_calling_in_process:
            try:
                params = {}
                for key, value in response.function_call.args.items():
                    params[key] = value

                function_name = response.function_call.name
                function_call_result = helpercode.function_handler[function_name]()
                api_requests_and_responses.append([function_name, params, function_call_result])
                st.session_state.aicontent.append(response)
                st.session_state.aicontent.append(types.Part.from_function_response(
                            name=function_name,
                            response={
                                "result": function_call_result,
                            },))
                response = st.session_state.gemini_client.models.generate_content(model=MODEL_NAME, contents=st.session_state.aicontent, config=generate_config_20)
                logging.warning(response)
                backend_details = handle_api_response(message_placeholder, api_requests_and_responses, backend_details)
                st.session_state.aicontent.append(response.candidates[0].content)
                response = response.candidates[0].content.parts[0]
            except AttributeError as e:
                logging.warning(e)
                function_calling_in_process = False
        
        full_response = response.text
        with message_placeholder.container():
            st.markdown(full_response.replace("$", r"\$"))  # noqa: W605
            with st.expander("Function calls, parameters, and responses:"):
                st.markdown(backend_details)

        st.session_state.messages.append({"role": "assistant", "content": full_response})

