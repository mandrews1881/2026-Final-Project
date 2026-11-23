import os
import glob
import subprocess
import requests

API_URL = "https://ollama.com/api/chat"
HEADERS = {"Authorization": "Bearer " + os.environ["OLLAMA_API_KEY"]}

read_file_tool_schema = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Use this when the user wants to read a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "the path of the file to read"},
            },
            "required": ["path"]
        }    
    }
}

list_files_schema = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "Use this when the user wants to list files in a specified directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "the path of the directory on which to list the files."}
            },
            "required": []

        }
    }
}

run_python_schema = {
    "type": "function",
    "function": {
        "name": "run_python_file",
        "description": "Use this when the user wants to run a python file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "the path of the python file to run."}
            },
            "required": []
                }
    }
}

write_file_schema = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Use this when the user wants to write a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "the path to write the new file."},
                "content": {"type": "string", "description": "the content to be written."}
            }
        }
    }
}

def agent(messages):
    #Start by telling the agent what tools it will be using
    tools = [
        read_file_tool_schema, list_files_schema, write_file_schema, run_python_schema,
    ]

    #Define the model and how it will communicate with the user
    payload = {
        "model": "gpt-oss:20b",
        "messages": messages,
        "stream": False,
        "tools": tools
    }

    #Establish the response format and timeout so it doesn't buffer endlessly
    response = requests.post(
        API_URL,
        headers=HEADERS,
        json=payload,
        timeout=300,
    )

    response.raise_for_status()
    data = response.json()
    message = data ["message"]
    return message

#Where to input the instructions for the agent (after messages = content)
tool_called = True
messages = [
   {"role": "user",
    "content": "INSERT INSTRUCTIONS HERE"}
]

while tool_called:
    message = agent(messages)
    print(message)
    tool_called = "tool_calls" in message

    #Need to distinguish what the tool_calls[0] does
    if tool_called:
        print("tool called!")
        tool_calls = message["tool_calls"]
        tool_call = tool_calls[0]

        function_name = tool_call["function"]["name"]
        function_arguments = tool_call["function"]["arguments"]

        if function_name == "list_files":
            path = "."
            if "path" in function_arguments:
                path = function_arguments["path"]
            print(f"arguments for list_files: {path}")
            # Preserve the below in case you need it to list out file names
            # files = "\n" .join(os.listdir(path))
            files = glob.glob(f"{path}/*")
            output = files

        elif function_name == "read_file":
            path = function_arguments["path"]
            with open(path, "r") as file:
                file_content = file.read()
            output = file_content

        elif function_name == "write_file":
            path = function_arguments["path"]
            content = function_arguments["content"]
            with open(path, "w") as file:
                file.write(content)
            output = f"File written to {path} with content: {content}"

        elif function_name == "run_python_file":
            path = function_arguments["path"]
            result = subprocess.run(["python", path], capture_output = True, text=True)
            output = f"The output of python {path} is: {result.stdout}"

        else:
            output = f"The requested tool {function_name} does not exist."
        
        tool_message = {
            "role": "tool",
            "content": f"The output of tool {function_name} is: {output}"
        }
        messages.append(tool_message)
    
    else:    
        ai_message = {
            "role": message["role"],
            "content": message["content"]
        }
        messages.append(ai_message)
    
    last_message = messages[-1]
    import pprint
    printer = pprint.pprint
    #printer(last_message)

    printer(messages)
        

