import os
import sys
import glob
import subprocess
import requests
from pypdf import PdfReader
from docx import Document
import pprint

API_URL = "https://ollama.com/api/chat"
HEADERS = {"Authorization": "Bearer " + os.environ["OLLAMA_API_KEY"]}
#Provide tool schemas which describe the existance of each tool to the model and tell it when it would be used
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

#Informs tool how to read specified file types
def read_document(file_path):
    lowercase_path = file_path.lower()
    
    if lowercase_path.endswith(".txt"):
        with open(file_path, "r") as file:
            file_content = file.read()
        return file_content
    
    elif lowercase_path.endswith(".pdf"):
        reader = PdfReader(file_path)
        page_text = []
        for page in reader.pages:
            page_text.append(page.extract_text())
        text = "\n".join(page_text)
        stripped_text = text.strip()
        if stripped_text == "":
            return f"{file_path} has undetectable text and requires human review."     
        else:
            return text
      
    elif lowercase_path.endswith(".docx"):
        doc = Document(file_path)
        paragraph_text = []
        for paragraph in doc.paragraphs:
            paragraph_text.append(paragraph.text)
        text = "\n".join(paragraph_text)
        stripped_text = text.strip()
        if stripped_text == "":
            return f"{file_path} has undetectable text and requires human review."     
        else:
            return text

    else:
        return f"Unknown file type for {file_path} so it could not be read."


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
    ) #This sends info to Ollama's server for it to then send back a response

    response.raise_for_status()
    data = response.json() #This converts Ollama's response into Python dictionary
    message = data ["message"] #This specifically creates a reference to the message FROM Ollama
    return message

#Ask the user for input
folder_name = input("What is the case's folder name? Please ensure the folder contains a 'specs.docx' file and a folder named 'docs' which contains the case files before starting. ")
if not os.path.isdir(folder_name):
    sys.exit(f"Error: the folder '{folder_name}' was not found. Please try again.")
print("Folder name " + folder_name + " found. Continuing.")

specs_docx_path = f"{folder_name}/specs.docx"
if not os.path.isfile(specs_docx_path):
    sys.exit(f"Error: The named case folder does not include a specs.docx file. This is needed to check Responsiveness. If there is a specs file please make sure it is named this exactly: 'specs.docx'.")
print("File name " + specs_docx_path + " found. Continuing.")

docs_path = f"{folder_name}/docs"
if not os.path.isdir(docs_path):
    sys.exit(f"Error: The named case folder does not include a docs folder. This is needed to store the case files. If there is a folder containing the case files please make sure it is named this exactly: 'docs'.")
print("Folder name " + docs_path + " found. Correct case folder structure confirmed.")

#Where the model is instructed what to do
tool_called = True
messages = [
   {"role": "user",
    "content": f"The user has provided {folder_name} which contains {specs_docx_path} and {docs_path}. Start by reading {specs_docx_path} to determine what makes a file Responsive or Not Responsive. Next, review each file in {docs_path} and assign it a Responsive or Not Responsive label based on the contents of {specs_docx_path} and a Confidential or Not Confidential label based on the contents of the file. Each file in {docs_path} must be reviewed exactly once."}
] #Instructions that tell the Model what to do once the user provides a case folder name

MAX_COUNT = 10
current_count = 0

files_already_reviewed = []

while tool_called:
    message = agent(messages) #previous message is overwritten with current message FROM Ollama
    messages.append(message) #current Ollama message (model) is filed in the messages cabinet (added to transcript)
    print(message) #prints current message for user's viewing
    tool_called = "tool_calls" in message

    #If a tool is called the program must loop through each tool called. Creates a for loop for each tool_call in the tool_calls.
    if tool_called:
        print("tool called!")
        tool_calls = message["tool_calls"]
        #tool_call = tool_calls[0]

        for tool_call in tool_calls:

            function_name = tool_call["function"]["name"]
            function_arguments = tool_call["function"]["arguments"]

            #Tell python what to do when the model calls each tool
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
                #with open(path, "r") as file:
                #   file_content = file.read()
                #output = file_content
                #Adding a guard in case the model calls a file to read that it has already read
                normalized_path = os.path.abspath(path)
                if normalized_path in files_already_reviewed:
                    print(f"Skip duplicate call for {normalized_path}, it was already read.")
                    output = f"{path} was already read; do not request to read it again."
                else:
                    print(f"Reading {normalized_path}")
                    files_already_reviewed.append(normalized_path)
                    output = read_document(path)
                
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
            messages.append(tool_message) #code files the tool result
    
    # else:    
    #     ai_message = {
    #         "role": message["role"],
    #         "content": message["content"]
    #     }
    #     messages.append(ai_message)
    current_count = current_count + 1
    if current_count == MAX_COUNT:
        print("Turn limit reached, closing loop")
        break
#last_message = messages[-1]
#printer(last_message)
pprint.pprint(messages)
#printer(messages)
        

